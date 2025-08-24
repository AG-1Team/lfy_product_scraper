import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import random
import zipfile
import re


def switch_website(url):
    if "farfetch" in url:
        return "farfetch"

    # Extract website name from URL
    return url.split("//")[1].split("/")[0]


def create_proxy_extension(
    proxy_host="pr.oxylabs.io",
    proxy_port="7777",
    proxy_user="umar_lfy_Boeun",
    proxy_pass="umar_LFY1234",
    ext_path="oxylabs_proxy_auth.zip"
):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "Oxylabs Proxy",
        "permissions": [
            "proxy",
            "storage",
            "webRequest",
            "webRequestAuthProvider",
            "webRequestBlocking"
        ],
        "background": {
            "service_worker": "background.js"
        },
        "host_permissions": [
            "<all_urls>"
        ]
    }
    """

    background_js = f"""
    chrome.runtime.onInstalled.addListener(() => {{
        var config = {{
            mode: "fixed_servers",
            rules: {{
                singleProxy: {{
                    scheme: "http",
                    host: "{proxy_host}",
                    port: parseInt({proxy_port})
                }},
                bypassList: ["localhost"]
            }}
        }};
        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
    }});

    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    with zipfile.ZipFile(ext_path, "w") as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return ext_path


def setup_scraping_driver(headless=True):
    options = uc.ChromeOptions()

    # User agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36 Edg/124.0.2478.51",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0"
    ]

    options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # options = Options()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-web-security")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--allow-running-insecure-content")

    # options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-web-security")
    options.add_argument(
        "--proxy-server=https://customer-umar_lfy_Boeun:umar_LFY1234@us-pr.oxylabs.io:10000")

    options.binary_location = "/usr/local/bin/google-chrome"
    # ext_path = create_proxy_extension()
    # options.add_extension(ext_path)

    driver = uc.Chrome(
        headless=headless, options=options, use_subprocess=False, version_main=130)

    # # Execute script to remove webdriver property
    # driver.execute_script(
    #     "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def save_scraped_data(website, data, db_model, sql_alchemy_session, medusa_id):
    retrieved_data = data.get(website)
    allowed_fields = set(db_model.__table__.columns.keys())
    cleaned_data = {k: v for k, v in retrieved_data.items()
                    if k in allowed_fields}

    if "image_urls" in cleaned_data and isinstance(cleaned_data["image_urls"], str):
        # Regex to match full image URLs ending in jpg|jpeg|png|webp|svg
        urls = re.findall(
            r'https?://[^\s,"]+?\.(?:jpg|jpeg|png|webp|svg)', cleaned_data["image_urls"], re.IGNORECASE)

        if urls:
            # first valid image
            cleaned_data["thumbnail"] = urls[0]
        sql_alchemy_session.add(db_model(medusa_id=medusa_id, **cleaned_data))
