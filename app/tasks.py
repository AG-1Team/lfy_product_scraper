import os
from celery import Celery, shared_task, signals
from .driver.index import setup_farfetch_driver
from .farfetch.index import farfetch_retrieve_products
from .scrapers.lyst import LystScraper
from .scrapers.modesens import ModeSensScraper
from .scrapers.reversible import ReversibleScraper
from .scrapers.leam import LeamScraper
from .scrapers.selfridge import SelfridgesScraper
from .scrapers.italist import ItalistScraper
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from .db.index import Base, MedusaProduct, FarfetchProduct, LystProduct, ItalistProduct, LeamProduct, ModesensProduct, ReversibleProduct, SelfridgeProduct
from .utils.index import save_scraped_data, extract_text
from datetime import datetime, timezone, timedelta
from threading import Lock, local
from selenium.common.exceptions import WebDriverException, InvalidSessionIdException, TimeoutException
from contextlib import contextmanager
from selenium.webdriver.remote.webdriver import WebDriver
import time
import random

process_local = local()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/mydb")

# Create default engine for the main process
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Reduced from 10
    max_overflow=10,  # Reduced from 20
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=30,
    echo=False
)
Base.metadata.create_all(engine)

# Use scoped_session for thread-safety
default_Session = scoped_session(
    sessionmaker(bind=engine, expire_on_commit=False))


def create_engine_for_worker():
    """Create a new SQLAlchemy engine specifically for a worker process."""
    print("Creating a new SQLAlchemy engine for worker process")
    worker_engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,  # Smaller pool per worker
        max_overflow=5,
        pool_recycle=3600,
        pool_timeout=30,
        echo=False
    )

    # Use scoped_session for thread-safety in workers
    process_local.engine = worker_engine
    process_local.Session = scoped_session(
        sessionmaker(bind=worker_engine, expire_on_commit=False))
    return worker_engine


def dispose_engine():
    """Dispose of the process-local engine if it exists."""
    if hasattr(process_local, 'Session'):
        print("Disposing SQLAlchemy session and engine for worker process")
        process_local.Session.remove()  # Important: remove scoped session
        del process_local.Session

    if hasattr(process_local, 'engine'):
        process_local.engine.dispose()
        del process_local.engine


def get_engine():
    """Get the appropriate SQLAlchemy engine for the current process."""
    if hasattr(process_local, 'engine'):
        return process_local.engine
    return engine


@contextmanager
def get_db_session():
    """
    Context manager for database sessions with proper cleanup.

    This ensures sessions are always closed and connections returned to the pool.
    """
    if hasattr(process_local, 'Session'):
        session = process_local.Session()
    else:
        session = default_Session()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        session.close()


def get_session():
    """
    Get a new SQLAlchemy session from the appropriate Session factory.

    WARNING: When using this method directly, you MUST call session.close() 
    when done to return the connection to the pool.

    Prefer using get_db_session() context manager instead.
    """
    if hasattr(process_local, 'Session'):
        return process_local.Session()
    return default_Session()


celery = Celery("tasks")

celery.conf.update(
    worker_pool='threads',
    worker_concurrency=4,  # Reduced from 8 to limit concurrent DB connections
    worker_prefetch_multiplier=1,  # Reduced to prevent task hoarding
    task_acks_late=True,
    worker_max_tasks_per_child=10,  # Increased to reduce worker restarts
    task_default_retry_delay=60,
    task_max_retries=3,
    task_time_limit=300,  # 5 minute timeout per task
    task_soft_time_limit=240,  # 4 minute soft limit
)

WEBHOOK_URL = "https://hook.eu2.make.com/8set6v5sh27som4jqyactxvkyb7idyko"
PRODUCTION_ENV = os.getenv("PYTHON_ENV")


def is_driver_alive(driver):
    """Check if the WebDriver session is still alive and responsive."""
    try:
        # Try to get current URL - this will fail if session is dead
        _ = driver.current_url
        return True
    except (WebDriverException, InvalidSessionIdException, ConnectionError) as e:
        print(f"[WARN] Driver health check failed: {e}")
        return False
    except Exception as e:
        print(f"[WARN] Unexpected error in driver health check: {e}")
        return False


def _init_driver_for_site(website: str, max_retries=3):
    """Create and return a fresh driver object for a given website with retries."""
    for attempt in range(max_retries):
        try:
            print(
                f"[ℹ] Creating driver for {website} (attempt {attempt + 1}/{max_retries})")

            # Add small random delay to prevent resource conflicts
            time.sleep(random.uniform(0.5, 2.0))

            if website == "farfetch":
                drv = setup_farfetch_driver()
            elif website == "lyst":
                drv = LystScraper(headless=True, wait_time=15)
            elif website == "modesens":
                drv = ModeSensScraper(headless=True, wait_time=15)
            elif website == "reversible":
                drv = ReversibleScraper(headless=True, wait_time=15)
            elif website == "leam":
                drv = LeamScraper(headless=True, wait_time=15)
            elif website == "selfridge":
                drv = SelfridgesScraper(headless=True, wait_time=15)
            elif website == "italist":
                drv = ItalistScraper(headless=True, wait_time=15)
            else:
                raise ValueError(f"No driver setup defined for {website}")

            # Verify the driver is working
            if not is_driver_alive(drv):
                raise WebDriverException(
                    "Driver failed health check immediately after creation")

            print(f"[✓] Successfully created driver for {website}")
            return drv

        except Exception as e:
            print(
                f"[⚠] Failed to create driver for {website} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                # Wait before retry with exponential backoff
                wait_time = (2 ** attempt) * random.uniform(1, 3)
                print(f"[ℹ] Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            else:
                print(
                    f"[❌] Failed to create driver for {website} after {max_retries} attempts")
                raise


def _safe_quit_close(driver, site_name=None):
    """Try to quit then close; swallow exceptions but log."""
    if driver is None:
        return

    try:
        # First check if driver is still responsive
        if not is_driver_alive(driver):
            print(
                f"[WARN] Driver for {site_name or ''} already dead, skipping cleanup")
            return

        if hasattr(driver, "quit"):
            try:
                driver.quit()
                print(f"[✓] Successfully quit driver for {site_name or ''}")
                return
            except Exception as e:
                print(f"[WARN] quit() failed for {site_name or ''}: {e}")

        if hasattr(driver, "close"):
            try:
                driver.close()
                print(f"[✓] Successfully closed driver for {site_name or ''}")
                return
            except Exception as e:
                print(f"[WARN] close() failed for {site_name or ''}: {e}")

    except Exception as e:
        print(f"[WARN] Error during driver cleanup for {site_name or ''}: {e}")


@contextmanager
def get_driver_context(website: str):
    """Context manager for WebDriver that ensures proper cleanup."""
    driver = None
    try:
        driver = _init_driver_for_site(website)
        yield driver
    except Exception as e:
        print(f"[⚠] Error in driver context for {website}: {e}")
        raise
    finally:
        if driver:
            _safe_quit_close(driver, website)


def get_driver(website: str):
    """Always create a fresh driver for this worker task"""
    print(f"[ℹ] Initializing driver for {website} in worker process...")
    return _init_driver_for_site(website)


@signals.worker_process_init.connect
def init_worker_process(*args, **kwargs):
    """Initialize resources for a worker process."""
    print("Initializing worker process...")
    create_engine_for_worker()


@signals.worker_process_shutdown.connect
def shutdown_all_drivers(**kwargs):
    """Clean shutdown of all resources."""
    print("[ℹ] Shutting down all database connections...")
    # Clean up database connections
    dispose_engine()


def check_existing_product(website: str, url: str, session):
    """Check if product already exists in database."""
    model_map = {
        "farfetch": FarfetchProduct,
        "lyst": LystProduct,
        "italist": ItalistProduct,
        "leam": LeamProduct,
        "modesens": ModesensProduct,
        "reversible": ReversibleProduct,
        "selfridge": SelfridgeProduct,
    }

    if website not in model_map:
        return None

    model = model_map[website]
    return session.query(model).filter_by(product_url=url).first()


def safe_scrape_with_retry(driver, website, url, max_retries=2):
    """Safely scrape with driver health checks and retries."""
    for attempt in range(max_retries):
        try:
            # Health check before scraping
            if not is_driver_alive(driver):
                raise WebDriverException(
                    f"Driver is not alive before scraping attempt {attempt + 1}")

            print(
                f"[ℹ] Scraping {website} (attempt {attempt + 1}/{max_retries})")

            # Perform scraping based on website
            if website == "farfetch":
                return farfetch_retrieve_products(driver, url)
            elif website == "lyst":
                return driver.scrape_product(url)
            elif website == "modesens":
                return driver.scrape_product(url)
            elif website == "reversible":
                return driver.scrape_product(url)
            elif website == "italist":
                return driver.scrape_product(url)
            elif website == "selfridge":
                return driver.scrape_product(url)
            elif website == "leam":
                return driver.scrape_product(url)
            else:
                raise ValueError(f"Website {website} is not supported")

        except (WebDriverException, InvalidSessionIdException, ConnectionError, TimeoutException) as e:
            print(f"[⚠] Scraping failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"[ℹ] Retrying scraping in 2 seconds...")
                time.sleep(2)
                # Health check - if driver is dead, we can't retry with same driver
                if not is_driver_alive(driver):
                    raise WebDriverException(
                        "Driver died during scraping, cannot retry with same driver")
            else:
                print(f"[❌] Scraping failed after {max_retries} attempts")
                raise


@shared_task(name="scrap_product_url", bind=True)
def scrape_product_and_notify(self, url, medusa_product_data, website):
    """
    Scrape product data from the given URL and website.

    Uses proper database session management and WebDriver context management.
    """
    print(f"[☑️] Starting scrape task for website {website} and URL {url}")

    try:
        # Use context manager for database session
        with get_db_session() as session:
            # Check if already processed
            existing = check_existing_product(website, url, session)
            if existing:
                print(f"[⏩] Skipping {url} (already scraped)")
                return

            # Use context manager for WebDriver
            with get_driver_context(website) as driver:
                # Scrape data with retry logic
                scraped_data = safe_scrape_with_retry(driver, website, url)

                # Check if scraping was successful
                if scraped_data is None:
                    print(f"[❌] No data scraped from {website} for URL {url}")
                    return

                data = {website: scraped_data}

                # Process medusa product data
                medusa_product_data["description"] = extract_text(
                    medusa_product_data["description"])
                data["medusa"] = medusa_product_data
                print("Scraped data:", data)

                # Handle medusa product
                medusa = session.get(MedusaProduct, medusa_product_data["id"])

                if not medusa:
                    medusa = MedusaProduct(
                        id=medusa_product_data["id"],
                        title=medusa_product_data["title"],
                        brand=medusa_product_data["brand"],
                        description=medusa_product_data["description"],
                        images=medusa_product_data["image_urls"],
                        thumbnail=medusa_product_data["thumbnail"]
                    )
                    session.add(medusa)
                else:
                    # Update existing medusa product
                    medusa.title = medusa_product_data["title"]
                    medusa.brand = medusa_product_data["brand"]
                    medusa.description = medusa_product_data["description"]
                    medusa.images = medusa_product_data["image_urls"]
                    medusa.thumbnail = medusa_product_data["thumbnail"]

                # Save scraped data based on website
                model_map = {
                    "farfetch": FarfetchProduct,
                    "lyst": LystProduct,
                    "italist": ItalistProduct,
                    "leam": LeamProduct,
                    "modesens": ModesensProduct,
                    "reversible": ReversibleProduct,
                    "selfridge": SelfridgeProduct,
                }

                if website in model_map:
                    save_scraped_data(
                        website, data, model_map[website], session, medusa.id)

                session.add(medusa)
                # session.commit() is handled by the context manager
                print(f"[✔] Data stored for {medusa.id} ({website})")

    except Exception as e:
        print(f"[⚠] Task failed for {url} on {website}: {e}")

        # Don't retry on certain unrecoverable errors
        if isinstance(e, ValueError):  # Unsupported website
            print(f"[❌] Non-retryable error, failing permanently: {e}")
            raise

        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = (2 ** self.request.retries) * 60  # 1min, 2min, 4min...
            print(
                f"[🔄] Retrying task in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=e)
        else:
            print(
                f"[❌] Task failed permanently after {self.max_retries} retries")
            raise
