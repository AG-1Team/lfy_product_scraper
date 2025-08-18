# tasks.py
from celery import Celery, shared_task, signals
import requests
from .driver.index import setup_farfetch_driver
from .farfetch.index import farfetch_retrieve_products
from .scrapers.lyst import LystScraper

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


def get_driver(website: str):
    """Return existing driver for website or initialize if not exists"""
    global drivers

    if website not in drivers or drivers[website] is None:
        print(f"[ℹ] Initializing driver for {website}...")
        if website == "farfetch":
            # farfetch specific setup
            drivers[website] = setup_farfetch_driver()
        elif website == "lyst":
            drivers[website] = LystScraper(headless=False, wait_time=15)
        # elif website == "other":
        #     drivers[website] = setup_driver(profile="other")
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
            elif site == "lyst":
                drv.close()
                print(f"✓ Closed {site} driver")
        except Exception as e:
            print(f"⚠ Failed closing {site} driver: {e}")


@shared_task(name="scrap_product_url")
def scrape_product_and_notify(url, medusa_product_data, website):
    driver = get_driver(website)

    data = {}
    if website == "farfetch":
        data["farfetch"] = farfetch_retrieve_products(driver, url)
    elif website == "lyst":
        data["lyst"] = driver.scrape_multiple_products([url])

    data["medusa"] = medusa_product_data

    print("DATA retrieved:", data)
    # Send results to Node.js webhook
    try:
        print("[ℹ] Sending data to webhook...")
        # requests.post(WEBHOOK_URL, json={"url": url, "data": data})
    except Exception as e:
        print(f"[⚠] Failed to send webhook: {e}")
