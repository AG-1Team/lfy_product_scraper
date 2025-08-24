# app.py
from flask import Flask, request, jsonify
from .tasks import scrape_product_and_notify
# from .utils.index import extract_website

app = Flask(__name__)


@app.before_request
def check_api_key():
    if request.endpoint == "scrape_products":  # only protect this route
        client_key = request.headers.get("X-API-Key")
        if client_key != "75db64f3-4822-4904-a1a1-dc2f3404d61d":
            return jsonify({"error": "Unauthorized"}), 401


@app.route("/scrape", methods=["POST"])
def scrape_products():
    req_data = request.json

    if not req_data:
        return jsonify({"error": "request data is required"}), 400

    url = req_data.get("url")
    # website = extract_website(url)
    medusa_product_data = req_data.get("medusa_product_data")

    # print("Website extracted:", website)

    if not url:
        return jsonify({"error": "url is required"}), 400

    if not medusa_product_data:
        return jsonify({"error": "medusa_product_data is required"}), 400

    task = None

    if "farfetch" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "farfetch")
    elif "lyst" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "lyst")
    elif "modesens" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "modesens")
    elif "reversible" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "reversible")
    elif "italist" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "italist")
    elif "leam" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "leam")
    elif "selfridge" in url:
        task = scrape_product_and_notify.delay(
            url, medusa_product_data, "selfridge")
    else:
        return jsonify({"error": f'Website with url %{url} is not supported'}), 400

    if task:
        return jsonify({"message": "Task scheduled", "task_id": task.id})

    if not task:
        return jsonify({"error": "website was not found OR data could not be scraped"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
