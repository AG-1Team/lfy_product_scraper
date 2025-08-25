import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import random
import zipfile
import re
import time
import json


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
        "manifest_version": 2,
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


def setup_scraping_driver(headless=True, proxy_enabled=True):
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

    # Headless mode
    if headless:
        options.add_argument("--headless=new")

    # Basic Chrome options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--allow-running-insecure-content")

    # if proxy_enabled:
    # options.add_argument('--proxy-server=pr.oxylabs.io:7777')

    # Set Chrome binary location if needed
    # options.binary_location = "/usr/local/bin/google-chrome"

    try:
        driver = uc.Chrome(
            headless=headless,
            options=options,
            use_subprocess=False,
            version_main=130
        )

        # Additional stealth measures
        # driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": random.choice(user_agents)
        })

        proxy_ip = check_proxy_working(driver)

        if proxy_ip:
            print(f"\n✅ Proxy is working! Current IP: {proxy_ip}")

        else:
            print("\n❌ Proxy might not be working correctly")

        return driver

    except Exception as e:
        print(f"Error initializing driver: {e}")
        return None


def check_proxy_working(driver):
    """
    Simple proxy check
    """
    print("Checking if proxy is working...")

    try:
        # Try multiple services
        services = [
            "https://httpbin.org/ip",
            "https://icanhazip.com/",
            "https://ipinfo.io/ip"
        ]

        for service in services:
            try:
                print(f"Trying {service}...")
                driver.get(service)

                # Wait for page load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                body_text = driver.find_element(
                    By.TAG_NAME, "body").text.strip()
                print(f"Response: {body_text[:200]}...")

                # Check if it looks like an error
                if "can't be reached" in body_text.lower() or "err_" in body_text.lower():
                    print(f"❌ Error response from {service}")
                    continue

                # Try to extract IP
                if service == "https://httpbin.org/ip":
                    try:
                        data = json.loads(body_text)
                        ip = data.get("origin", "Unknown")
                        print(f"✅ Proxy working! IP: {ip}")
                        return ip
                    except json.JSONDecodeError:
                        print("❌ Invalid JSON response")
                        continue
                else:
                    # For other services, the body should be just the IP
                    if body_text and "." in body_text and len(body_text.split(".")) == 4:
                        print(f"✅ Proxy working! IP: {body_text}")
                        return body_text

            except Exception as e:
                print(f"❌ Error with {service}: {e}")
                continue

        print("❌ All services failed")
        return None

    except Exception as e:
        print(f"❌ General error: {e}")
        return None


def verify_proxy_location(driver):
    """
    Verify proxy location and other details
    """
    try:
        print("\nChecking proxy location and details...")
        driver.get('https://ipinfo.io/json')
        time.sleep(3)

        info = driver.find_element(By.TAG_NAME, "pre").text
        print(f"Proxy location info:\n{info}")

        return info

    except Exception as e:
        print(f"Error getting location info: {e}")
        return None


def test_proxy_rotation(driver, num_requests=3):
    """
    Test if the proxy is rotating IPs (for sticky session residential proxies)
    """
    print(f"\nTesting proxy rotation with {num_requests} requests...")
    ips = []

    for i in range(num_requests):
        try:
            driver.get('https://icanhazip.com/')
            time.sleep(random.uniform(2, 4))  # Random delay

            ip = driver.find_element(By.TAG_NAME, "body").text.strip()
            ips.append(ip)
            print(f"Request {i+1}: {ip}")

        except Exception as e:
            print(f"Error on request {i+1}: {e}")

    unique_ips = set(ips)
    print(f"\nTotal requests: {len(ips)}")
    print(f"Unique IPs: {len(unique_ips)}")
    print(f"IPs: {list(unique_ips)}")

    return ips


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


def extract_text(content: str) -> str:
    """
    Extracts readable text from either:
    - HTML with tags (<p>, <div>, <span>, etc.)
    - Plain string without HTML
    Preserves line breaks for <br> tags.
    """
    if "<" in content and ">" in content:
        soup = BeautifulSoup(content, "html.parser")
        # Replace <br> with newline explicitly
        for br in soup.find_all("br"):
            br.replace_with("\n")
        return soup.get_text(separator=" ", strip=True)

    return content.strip()
