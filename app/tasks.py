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
from selenium.common.exceptions import WebDriverException, InvalidSessionIdException
from contextlib import contextmanager
from selenium.webdriver.remote.webdriver import WebDriver

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

# Driver management (keeping your existing logic)
drivers: dict = {}
_drivers_lock = Lock()
DRIVER_TTL = timedelta(minutes=10)

def _init_driver_for_site(website: str):
    """Create and return a fresh driver object for a given website."""
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
    return drv

def _safe_quit_close(driver, site_name=None):
    """Try to quit then close; swallow exceptions but log."""
    try:
        if hasattr(driver, "quit"):
            try:
                driver.quit()
                return
            except Exception as e:
                print(f"[WARN] quit() failed for {site_name or ''}: {e}")
        if hasattr(driver, "close"):
            try:
                driver.close()
                return
            except Exception as e:
                print(f"[WARN] close() failed for {site_name or ''}: {e}")
    except Exception as e:
        print(f"[WARN] error shutting down driver {site_name or ''}: {e}")

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
    global drivers
    print("[ℹ] Shutting down all drivers and database connections...")

    # Clean up drivers
    with _drivers_lock:
        for site, entry in list(drivers.items()):
            if not entry:
                continue
            try:
                _safe_quit_close(entry["driver"], site_name=site)
                drivers[site] = None
                print(f"✓ Closed {site} driver")
            except Exception as e:
                print(f"⚠ Failed closing {site} driver: {e}")

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


@shared_task(name="scrap_product_url", bind=True)
def scrape_product_and_notify(self, url, medusa_product_data, website):
    """
    Scrape product data from the given URL and website.
    
    Uses proper database session management to prevent connection pool exhaustion.
    """
    print(f"[☑️] Starting scrape task for website {website} and URL {url}")

    driver = None
    try:
        # Use context manager for database session
        with get_db_session() as session:
            # Check if already processed
            existing = check_existing_product(website, url, session)
            if existing:
                print(f"[⏩] Skipping {url} (already scraped)")
                return

            # Get driver
            driver = get_driver(website)

            # Scrape data based on website
            data = {}
            if website == "farfetch":
                data["farfetch"] = farfetch_retrieve_products(driver, url)
            elif website == "lyst":
                data["lyst"] = driver.scrape_product(url)
            elif website == "modesens":
                data["modesens"] = driver.scrape_product(url)
            elif website == "reversible":
                data["reversible"] = driver.scrape_product(url)
            elif website == "italist":
                data["italist"] = driver.scrape_product(url)
            elif website == "selfridge":
                data["selfridge"] = driver.scrape_product(url)
            elif website == "leam":
                data["leam"] = driver.scrape_product(url)
            else:
                raise ValueError(f"Website {website} is not supported")

            # Check if scraping was successful
            if data[website] is None:
                print(f"[❌] No data scraped from {website} for URL {url}")
                return

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
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60  # 1min, 2min, 4min...
            print(
                f"[🔄] Retrying task in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=e)
        else:
            print(
                f"[❌] Task failed permanently after {self.max_retries} retries")
            raise

    finally:
        # Always clean up driver
        if driver:
            try:
                if type(driver) == WebDriver:
                    driver.quit()
                else:
                    driver.close()
            except Exception as e:
                print(f"[WARN] Error closing driver: {e}")
