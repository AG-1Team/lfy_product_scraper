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
from sqlalchemy.orm import sessionmaker
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

engine = create_engine(DATABASE_URL, pool_size=10,
                       max_overflow=20, pool_pre_ping=True)
Base.metadata.create_all(engine)
default_Session = sessionmaker(bind=engine, expire_on_commit=False)
# Session = sessionmaker(bind=engine)
# session = Session()


def create_engine_for_worker():
    """Create a new SQLAlchemy engine specifically for a worker process."""
    print("Creating a new SQLAlchemy engine for worker process")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    process_local.engine = engine
    process_local.Session = sessionmaker(bind=engine, expire_on_commit=False)
    return engine


def dispose_engine():
    """Dispose of the process-local engine if it exists."""
    if hasattr(process_local, 'engine'):
        print("Disposing SQLAlchemy engine for worker process")
        process_local.engine.dispose()
        del process_local.engine
        del process_local.Session


def get_engine():
    """Get the appropriate SQLAlchemy engine for the current process."""
    # Check if we have a process-local engine
    if hasattr(process_local, 'engine'):
        return process_local.engine
    # Otherwise, return the default engine
    return engine


def get_session():
    """
    Get a new SQLAlchemy session from the appropriate Session factory.
    
    This works with both the main application (using the default engine)
    and Celery workers (using their process-local engines).
    """
    # Check if we have a process-local Session factory
    if hasattr(process_local, 'Session'):
        return process_local.Session()
    # Otherwise, use the default Session factory
    return default_Session()

celery = Celery("tasks")

celery.conf.update(
    worker_pool='threads',   # use threads instead of prefork (multiprocessing)
    worker_concurrency=8,   # number of threads
    worker_prefetch_multiplier=2,
    task_acks_late=True,
    worker_max_tasks_per_child=5,  # optional, not as useful with threads
    task_default_retry_delay=60,
    task_max_retries=3,
)

WEBHOOK_URL = "https://hook.eu2.make.com/8set6v5sh27som4jqyactxvkyb7idyko"
PRODUCTION_ENV = os.getenv("PYTHON_ENV")

drivers: dict = {}
_drivers_lock = Lock()

# configure TTL
DRIVER_TTL = timedelta(minutes=10)

# def get_driver(website: str):
#     """Return existing driver for website or initialize/rotate if stale/unhealthy."""
#     global drivers
#     with _drivers_lock:
#         entry = drivers.get(website)

#         if entry is None:
#             print(f"[ℹ] Initializing driver for {website} (first time)...")
#             drivers[website] = _init_driver_for_site(website)
#             return drivers[website]["driver"]

#         # Check if rotation is needed
#         is_stale = _is_stale(entry)
#         is_healthy = _is_healthy(entry["driver"])

#         if is_stale or not is_healthy:
#             age = datetime.now(timezone.utc) - entry['created_at']
#             reason = "stale" if is_stale else "unhealthy"
#             print(
#                 f"[ℹ] Driver for {website} is {reason} (age: {age}) -> rotating now...")
#             _safe_quit_close(entry["driver"], site_name=website)
#             drivers[website] = _init_driver_for_site(website)
#         else:
#             age = datetime.now(timezone.utc) - entry['created_at']
#             print(
#                 f"[DEBUG] Using existing healthy driver for {website} (age: {age})")

#         return drivers[website]["driver"]


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

    # return {"driver": drv, "created_at": datetime.now(timezone.utc)}
    return drv


def _safe_quit_close(driver, site_name=None):
    """Try to quit then close; swallow exceptions but log."""
    try:
        # prefer quit if available
        if hasattr(driver, "quit"):
            try:
                driver.quit()
                return
            except Exception as e:
                print(f"[WARN] quit() failed for {site_name or ''}: {e}")
        # fallback to close
        if hasattr(driver, "close"):
            try:
                driver.close()
                return
            except Exception as e:
                print(f"[WARN] close() failed for {site_name or ''}: {e}")
    except Exception as e:
        print(f"[WARN] error shutting down driver {site_name or ''}: {e}")


def _is_stale(entry: dict) -> bool:
    """Check if driver entry is older than TTL"""
    age = datetime.now(timezone.utc) - entry["created_at"]
    is_stale = age > DRIVER_TTL
    if is_stale:
        print(f"[DEBUG] Driver is stale. Age: {age}, TTL: {DRIVER_TTL}")
    return is_stale


def _is_healthy(driver) -> bool:
    """Simple health check. Returns False on common session errors."""
    try:
        # Handle different driver types
        actual_driver = None

        # For custom scrapers that wrap WebDriver
        if hasattr(driver, 'driver'):
            actual_driver = driver.driver
        # For custom scrapers that might use 'webdriver' attribute
        elif hasattr(driver, 'webdriver'):
            actual_driver = driver.webdriver
        # For raw WebDriver objects
        elif hasattr(driver, 'execute_script'):
            actual_driver = driver
        else:
            # If we can't find the underlying driver, assume it's healthy
            # This prevents unnecessary rotations for custom scrapers
            print(
                f"[DEBUG] Cannot determine driver type for health check, assuming healthy")
            return True

        if actual_driver and hasattr(actual_driver, 'execute_script'):
            # cheap call to webdriver — execute_script is usually safe
            actual_driver.execute_script("return 1")
            return True
        else:
            print(f"[DEBUG] No execute_script method found, assuming healthy")
            return True

    except (InvalidSessionIdException, WebDriverException) as e:
        print(f"[DEBUG] driver health check failed: {e}")
        return False
    except Exception as e:
        # any other error treat as unhealthy but log
        print(f"[DEBUG] driver health check unexpected error: {e}")
        return False


def rotate_drivers(force: bool = False):
    """Rotate (recreate) any drivers older than DRIVER_TTL, or rotate all if force=True."""
    global drivers
    with _drivers_lock:
        for site, entry in list(drivers.items()):
            if entry is None:
                continue
            try:
                should_rotate = force or _is_stale(
                    entry) or not _is_healthy(entry["driver"])
                if should_rotate:
                    age = datetime.now(timezone.utc) - entry['created_at']
                    reason = "forced" if force else (
                        "stale" if _is_stale(entry) else "unhealthy")
                    print(
                        f"[ℹ] Rotating driver for {site} - Reason: {reason}, Age: {age}")
                    _safe_quit_close(entry["driver"], site_name=site)
                    # create new driver and replace entry
                    drivers[site] = _init_driver_for_site(site)
                    print(f"[✓] Recreated driver for {site}")
                else:
                    age = datetime.now(timezone.utc) - entry['created_at']
                    print(
                        f"[DEBUG] Driver for {site} is healthy and fresh - Age: {age}")
            except Exception as e:
                print(f"[ERROR] rotating driver for {site}: {e}")


def get_driver(website: str):
    """Always create a fresh driver for this worker task"""
    print(f"[ℹ] Initializing driver for {website} in worker process...")
    return _init_driver_for_site(website)


@signals.worker_process_init.connect
def init_worker_process(*args, **kwargs):
    """
    Initialize resources for a worker process.
    
    This signal handler runs in each forked child process,
    creating a separate SQLAlchemy engine for each worker.
    """
    create_engine_for_worker()

# wire shutdown to Celery signal as you already do
@signals.worker_process_shutdown.connect
def shutdown_all_drivers(**kwargs):
    global drivers
    print("[ℹ] Shutting down all drivers...")
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
    dispose_engine()


@shared_task(name="scrap_product_url")
def scrape_product_and_notify(url, medusa_product_data, website):
    print(f"[☑️] Starting scrape task for website {website} and URL {url}")
    session = get_session()
    # 🚨 Check if already processed
    if website == "farfetch":
        existing = session.query(FarfetchProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "lyst":
        existing = session.query(LystProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "italist":
        existing = session.query(ItalistProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "leam":
        existing = session.query(LeamProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "modesens":
        existing = session.query(ModesensProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "reversible":
        existing = session.query(ReversibleProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return
    elif website == "selfridge":
        existing = session.query(SelfridgeProduct).filter_by(
            product_url=url).first()
        if existing:
            print(f"[⏩] Skipping {url} (already scraped)")
            return

    # 🔄 REMOVED: rotate_drivers() call that was causing premature rotation
    # Now get_driver() will handle rotation only when needed (TTL exceeded or unhealthy)

    data = {}

    # with driver_for(website) as driver:
    driver = get_driver(website)
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

    # ❌ If scraper failed → don't insert anything
    if data[website] is None:
        print(f"[❌] No data scraped from {website} for URL {url}")
        return

    medusa_product_data["description"] = extract_text(
        medusa_product_data["description"])
    data["medusa"] = medusa_product_data
    print("Scraped data:", data)

    medusa = session.get(MedusaProduct, medusa_product_data["id"])

    try:
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
            medusa.title = medusa_product_data["title"]
            medusa.brand = medusa_product_data["brand"]
            medusa.description = medusa_product_data["description"]
            medusa.images = medusa_product_data["image_urls"]
            medusa.thumbnail = medusa_product_data["thumbnail"]

        if website == "farfetch":
            save_scraped_data(
                website, data, FarfetchProduct, session, medusa.id)
        elif website == "lyst":
            save_scraped_data(website, data, LystProduct,
                              session, medusa.id)
        elif website == "italist":
            save_scraped_data(
                website, data, ItalistProduct, session, medusa.id)
        elif website == "leam":
            save_scraped_data(website, data, LeamProduct,
                              session, medusa.id)
        elif website == "modesens":
            save_scraped_data(
                website, data, ModesensProduct, session, medusa.id)
        elif website == "reversible":
            save_scraped_data(
                website, data, ReversibleProduct, session, medusa.id)
        elif website == "selfridge":
            save_scraped_data(
                website, data, SelfridgeProduct, session, medusa.id)

        session.add(medusa)
        session.commit()
        print(f"[✔] Data stored for {medusa.id} ({website})")

    except Exception as e:
        print(f"[⚠] Failed to add medusa product: {e}")

    if type(driver) == WebDriver:
        driver.quit()
    else:
        driver.close()
