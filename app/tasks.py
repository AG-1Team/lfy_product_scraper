# tasks.py
import os
import requests
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
from .utils.index import save_scraped_data

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/mydb")

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

celery = Celery("tasks")

celery.conf.update(
    worker_pool='solo',  # This prevents multiprocessing issues with Chrome
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Restart worker after each task to prevent memory leaks
    worker_max_tasks_per_child=1,
)

WEBHOOK_URL = "https://hook.eu2.make.com/8set6v5sh27som4jqyactxvkyb7idyko"

# keep a dict of drivers
drivers = {}

PRODUCTION_ENV = os.getenv("PYTHON_ENV")


def get_driver(website: str):
    """Return existing driver for website or initialize if not exists"""
    global drivers

    if website not in drivers or drivers[website] is None:
        print(f"[ℹ] Initializing driver for {website}...")
        if website == "farfetch":
            # farfetch specific setup
            drivers[website] = setup_farfetch_driver()
        elif website == "lyst":
            drivers[website] = LystScraper(headless=True, wait_time=15)
        elif website == "modesens":
            drivers[website] = ModeSensScraper(headless=True, wait_time=15)
        elif website == "reversible":
            drivers[website] = ReversibleScraper(headless=True, wait_time=15)
        elif website == "leam":
            drivers[website] = LeamScraper(headless=True, wait_time=15)
        elif website == "selfridge":
            drivers[website] = SelfridgesScraper(headless=True, wait_time=15)
        elif website == "italist":
            drivers[website] = ItalistScraper(headless=True, wait_time=15)
        else:
            raise ValueError(f"No driver setup defined for {website}")

    return drivers[website]


@signals.worker_process_shutdown.connect
def shutdown_all_drivers(**kwargs):
    global drivers
    print("[ℹ] Shutting down all drivers...")
    for site, drv in drivers.items():
        try:
            if site == "farfetch":
                drv.quit()
                print(f"✓ Closed {site} driver")
            else:
                drv.close()
                print(f"✓ Closed {site} driver")
        except Exception as e:
            print(f"⚠ Failed closing {site} driver: {e}")


@shared_task(name="scrap_product_url")
def scrape_product_and_notify(url, medusa_product_data, website):
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


    driver = get_driver(website)

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

    # ❌ If scraper failed → don’t insert anything
    if data[website] is None:
        print(f"[❌] No data scraped from {website} for URL {url}")
        return

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
