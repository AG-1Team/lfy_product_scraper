# tasks.py
from celery import Celery, shared_task, signals
import requests
from .driver.index import setup_driver
from .farfetch.index import farfetch_retrieve_products

celery = Celery("tasks")

celery.conf.update(
    worker_pool='solo',  # This prevents multiprocessing issues with Chrome
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1,  # Restart worker after each task to prevent memory leaks
)

WEBHOOK_URL = "https://hook.eu2.make.com/8set6v5sh27som4jqyactxvkyb7idyko"

@signals.worker_process_init.connect
def init_worker_session(**kwargs):
    global driver
    print("Initializing Chromium session once per worker process...")
    driver = setup_driver()


@signals.worker_process_shutdown.connect
def shutdown_worker_session(**kwargs):
    global driver
    if driver is not None:
        driver.quit()


@shared_task(name="scrap_product_url")
def scrape_farfetch_and_notify(url, medusa_product_data):
    global driver
    if driver is None:
        print("[⚠] Driver not initialized — starting a new one...")
        driver = setup_driver()

    data = {}
    data["farfetch"] = farfetch_retrieve_products(driver, url)
    data["medusa"] = medusa_product_data

    print("DATA retrieved:", data)
    # Send results to Node.js webhook
    try:
        requests.post(WEBHOOK_URL, json={"url": url, "data": data})
    except Exception as e:
        print(f"[⚠] Failed to send webhook: {e}")
