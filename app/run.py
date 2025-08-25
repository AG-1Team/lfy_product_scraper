# app.py
import os
import requests
import json
import time
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .tasks import scrape_product_and_notify
from .db.index import Base, MedusaProduct, FarfetchProduct, LystProduct, ItalistProduct, LeamProduct, ModesensProduct, ReversibleProduct, SelfridgeProduct

app = Flask(__name__)

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/mydb")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Airtable configuration
# AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
# AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_API_KEY = "patFZ3qlfvQSzjZJF.02cc99a5b0bee622b47b99f584946ff805a735d82e5bf90ce8f52221f1a24e9b"
AIRTABLE_BASE_ID = "appRwNpNlOjXibJjF"
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

# Rate limiting configuration
# 200ms delay between requests (max 5 per second)
AIRTABLE_RATE_LIMIT_DELAY = 0.2
# Keep 5k buffer from 100k limit
API_CALL_COUNTER = {"count": 0, "limit": 95000}

# Airtable table names
AIRTABLE_TABLES = {
    'medusa': 'Products',
    'farfetch': 'Farfetch',
    'lyst': 'Lyst',
    'italist': 'Italist',
    'leam': 'Leam',
    'modesens': 'Modesens',
    'reversible': 'Reversible',
    'selfridge': 'Selfridge'
}


@app.before_request
def check_api_key():
    if request.endpoint in ["scrape_products", "sync_to_airtable", "get_api_usage"]:
        client_key = request.headers.get("X-API-Key")
        if client_key != "75db64f3-4822-4904-a1a1-dc2f3404d61d":
            return jsonify({"error": "Unauthorized"}), 401


def check_api_limit():
    """Check if we're approaching API limit"""
    if API_CALL_COUNTER["count"] >= API_CALL_COUNTER["limit"]:
        raise Exception(
            f"API limit reached ({API_CALL_COUNTER['count']}/{API_CALL_COUNTER['limit']}). Please wait for limit reset.")


def make_airtable_request(method, url, **kwargs):
    """Make rate-limited Airtable API request"""
    check_api_limit()

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    kwargs.setdefault('headers', {}).update(headers)

    # Rate limiting
    time.sleep(AIRTABLE_RATE_LIMIT_DELAY)

    response = requests.request(method, url, **kwargs)
    API_CALL_COUNTER["count"] += 1

    if response.status_code not in [200, 201]:
        print(f"Airtable API error: {response.status_code} - {response.text}")
        raise Exception(
            f"Airtable API error: {response.status_code} - {response.text}")

    return response


def get_existing_records(table_name, filter_formula=None):
    """Get existing records from Airtable with pagination"""
    url = f"{AIRTABLE_API_URL}/{table_name}"
    all_records = {}
    offset = None

    while True:
        params = {"pageSize": 100}  # Max page size
        if offset:
            params["offset"] = offset
        if filter_formula:
            params["filterByFormula"] = filter_formula

        response = make_airtable_request("GET", url, params=params)
        data = response.json()

        # Index records by a unique identifier
        for record in data.get("records", []):
            fields = record.get("fields", {})
            # For medusa products, use ID field
            if table_name == AIRTABLE_TABLES['medusa']:
                key = fields.get("ID")
            else:
                # For website products, use Product URL as unique identifier
                key = fields.get("Product URL")

            if key:
                all_records[key] = record["id"]  # Store Airtable record ID

        offset = data.get("offset")
        if not offset:
            break

    return all_records


def format_attachment_field(url):
    """Convert URL string to Airtable attachment format"""
    if not url:
        return None
    return [{"url": url}]


def convert_to_airtable_record(data, table_type, medusa_airtable_id=None, is_update=False):
    """Convert database record to Airtable format"""
    if table_type == 'medusa':
        fields = {
            "Title": data.title or "",
            "Brand": data.brand or "",
            "Description": data.description or "",
            "Thumbnail": format_attachment_field(data.thumbnail),
            "Images": data.images or "",
            "Created At": data.created_at.isoformat() if data.created_at else "",
            "Updated At": data.updated_at.isoformat() if data.updated_at else ""
        }
        # Only include ID for new records, not updates
        if not is_update:
            fields["Id"] = data.id

        return {"fields": fields}
    else:
        # For all other website tables
        fields = {
            "Product Name": data.product_name or "",
            "Thumbnail": format_attachment_field(data.thumbnail),
            "Product URL": data.product_url or "",
            "Brand": data.brand or "",
            "Product Details": data.product_details or "",
            "Category": data.category or "",
            "Image URLs": data.image_urls or "",
            "Original Price": data.original_price or "",
            "Discount": data.discount or "",
            "Sale Price": data.sale_price or "",
            "Size and Fit": data.size_and_fit or "",
            "Price AED": data.price_aed or "",
            "Price USD": data.price_usd or "",
            "Price GBP": data.price_gbp or "",
            "Price EUR": data.price_eur or "",
            "Created At": data.created_at.isoformat() if data.created_at else ""
        }

        # Link to main product if medusa_airtable_id is provided
        if medusa_airtable_id:
            fields["Medusa Product"] = [medusa_airtable_id]

        return {"fields": fields}


def batch_upsert_records(table_name, records_to_create, records_to_update):
    """Create and update records in batches"""
    results = {"created": 0, "updated": 0}

    # Create new records
    if records_to_create:
        batch_size = 10  # Airtable limit
        for i in range(0, len(records_to_create), batch_size):
            batch = records_to_create[i:i + batch_size]
            url = f"{AIRTABLE_API_URL}/{table_name}"
            payload = {"records": batch}

            response = make_airtable_request("POST", url, json=payload)
            created_count = len(response.json().get("records", []))
            results["created"] += created_count

    # Update existing records
    if records_to_update:
        batch_size = 10  # Airtable limit
        for i in range(0, len(records_to_update), batch_size):
            batch = records_to_update[i:i + batch_size]
            url = f"{AIRTABLE_API_URL}/{table_name}"
            payload = {"records": batch}

            response = make_airtable_request("PATCH", url, json=payload)
            updated_count = len(response.json().get("records", []))
            results["updated"] += updated_count

    return results


@app.route("/sync-to-airtable", methods=["POST"])
def sync_to_airtable():
    """Sync data from PostgreSQL to Airtable with deduplication and rate limiting"""
    try:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({"error": "Airtable API key and Base ID must be set"}), 400

        session = Session()

        req_data = request.json or {}
        medusa_id = req_data.get("medusa_id")
        sync_all = req_data.get("sync_all", False)
        # Force update even if exists
        force_update = req_data.get("force_update", False)

        if not medusa_id and not sync_all:
            return jsonify({"error": "Either 'medusa_id' or 'sync_all: true' is required"}), 400

        # Get products to sync
        if medusa_id:
            medusa_products = session.query(
                MedusaProduct).filter_by(id=medusa_id).all()
        else:
            medusa_products = session.query(MedusaProduct).all()

        if not medusa_products:
            return jsonify({"error": "No products found"}), 404

        results = {
            "synced_products": 0,
            "created_records": {},
            "updated_records": {},
            "skipped_records": {},
            "errors": [],
            "api_calls_used": 0
        }

        # Get existing records from Airtable to avoid duplicates
        print("Fetching existing records from Airtable...")
        existing_medusa_records = get_existing_records(
            AIRTABLE_TABLES['medusa'])

        website_models = {
            'farfetch': FarfetchProduct,
            'lyst': LystProduct,
            'italist': ItalistProduct,
            'leam': LeamProduct,
            'modesens': ModesensProduct,
            'reversible': ReversibleProduct,
            'selfridge': SelfridgeProduct
        }

        # Get existing website records
        existing_website_records = {}
        for website in website_models.keys():
            existing_website_records[website] = get_existing_records(
                AIRTABLE_TABLES[website])

        for medusa_product in medusa_products:
            try:
                # 1. Handle main product
                medusa_airtable_id = None
                if medusa_product.id in existing_medusa_records:
                    medusa_airtable_id = existing_medusa_records[medusa_product.id]

                    if force_update:
                        # Update existing record
                        record = convert_to_airtable_record(
                            medusa_product, 'medusa', is_update=True)
                        record["id"] = medusa_airtable_id
                        batch_upsert_records(
                            AIRTABLE_TABLES['medusa'], [], [record])
                        results["updated_records"]["medusa"] = results["updated_records"].get(
                            "medusa", 0) + 1
                    else:
                        results["skipped_records"]["medusa"] = results["skipped_records"].get(
                            "medusa", 0) + 1
                else:
                    # Create new record
                    record = convert_to_airtable_record(
                        medusa_product, 'medusa')
                    response = batch_upsert_records(
                        AIRTABLE_TABLES['medusa'], [record], [])

                    # Get the created record ID (you'd need to fetch it or modify batch_upsert_records to return IDs)
                    # For now, we'll fetch it again (this is one extra API call per new product)
                    updated_existing = get_existing_records(
                        AIRTABLE_TABLES['medusa'], f"{{ID}} = '{medusa_product.id}'")
                    medusa_airtable_id = updated_existing.get(
                        medusa_product.id)

                    results["created_records"]["medusa"] = results["created_records"].get(
                        "medusa", 0) + 1

                if not medusa_airtable_id:
                    results["errors"].append(
                        f"Failed to get Airtable ID for product {medusa_product.id}")
                    continue

                # 2. Handle website-specific data
                for website, model in website_models.items():
                    website_products = session.query(model).filter_by(
                        medusa_id=medusa_product.id).all()

                    if not website_products:
                        continue

                    records_to_create = []
                    records_to_update = []

                    for website_product in website_products:
                        product_url = website_product.product_url

                        if product_url in existing_website_records[website]:
                            if force_update:
                                # Update existing record
                                record = convert_to_airtable_record(
                                    website_product, website, medusa_airtable_id, is_update=True
                                )
                                record["id"] = existing_website_records[website][product_url]
                                records_to_update.append(record)
                            else:
                                results["skipped_records"][website] = results["skipped_records"].get(
                                    website, 0) + 1
                        else:
                            # Create new record
                            record = convert_to_airtable_record(
                                website_product, website, medusa_airtable_id
                            )
                            records_to_create.append(record)

                    # Batch process the records
                    if records_to_create or records_to_update:
                        batch_results = batch_upsert_records(
                            AIRTABLE_TABLES[website],
                            records_to_create,
                            records_to_update
                        )
                        results["created_records"][website] = results["created_records"].get(
                            website, 0) + batch_results["created"]
                        results["updated_records"][website] = results["updated_records"].get(
                            website, 0) + batch_results["updated"]

                results["synced_products"] += 1

                # Check API limit periodically
                if API_CALL_COUNTER["count"] >= API_CALL_COUNTER["limit"]:
                    results["errors"].append(
                        f"API limit reached after processing {results['synced_products']} products")
                    break

            except Exception as e:
                results["errors"].append(
                    f"Error syncing product {medusa_product.id}: {str(e)}")
                continue

        session.close()
        results["api_calls_used"] = API_CALL_COUNTER["count"]

        return jsonify({
            "message": "Sync completed",
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500


@app.route("/api-usage", methods=["GET"])
def get_api_usage():
    """Get current API usage stats"""
    return jsonify({
        "api_calls_used": API_CALL_COUNTER["count"],
        "api_limit": API_CALL_COUNTER["limit"],
        "remaining": API_CALL_COUNTER["limit"] - API_CALL_COUNTER["count"]
    })


@app.route("/reset-api-counter", methods=["POST"])
def reset_api_counter():
    """Reset API counter (call this when your monthly limit resets)"""
    API_CALL_COUNTER["count"] = 0
    return jsonify({"message": "API counter reset", "count": API_CALL_COUNTER["count"]})


@app.route("/scrape", methods=["POST"])
def scrape_products():
    req_data = request.json

    if not req_data:
        return jsonify({"error": "request data is required"}), 400

    url = req_data.get("url")
    medusa_product_data = req_data.get("medusa_product_data")

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
        return jsonify({"error": f'Website with url {url} is not supported'}), 400

    if task:
        return jsonify({"message": "Task scheduled", "task_id": task.id})

    return jsonify({"error": "website was not found OR data could not be scraped"}), 400


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Service is running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
