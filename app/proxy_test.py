import undetected_chromedriver as uc
import random
import time
import tempfile
import os
import zipfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def create_working_proxy_extension(
    proxy_host="pr.oxylabs.io",
    proxy_port="7777",
    proxy_user="umar_lfy_Boeun",
    proxy_pass="umar_LFY1234"
):
    """
    Create a working proxy extension using a different approach
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    ext_path = os.path.join(temp_dir, "proxy_auth.zip")

    # Use Manifest V2 with simplified approach
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Auth",
        "permissions": [
            "proxy",
            "tabs", 
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"],
            "persistent": true
        }
    }
    """

    # Simplified background script that should work
    background_js = f"""
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

    // Set proxy immediately when extension loads
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{
        console.log("Proxy set to {proxy_host}:{proxy_port}");
    }});

    // Handle authentication requests
    function handleAuth(details) {{
        console.log("Auth requested for:", details.url);
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        handleAuth,
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    # Create the zip file
    with zipfile.ZipFile(ext_path, "w") as zf:
        zf.writestr("manifest.json", manifest_json)
        zf.writestr("background.js", background_js)

    return ext_path


def setup_driver_with_working_extension(headless=True):
    """
    Setup driver with the working extension approach
    """
    options = uc.ChromeOptions()

    # Basic options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")

    # Extension-related options
    options.add_argument("--enable-extensions")
    options.add_argument("--load-extension")  # This might help

    # User agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")

    if headless:
        options.add_argument("--headless=new")

    # Create and add extension
    ext_path = create_working_proxy_extension()
    options.add_extension(ext_path)

    print(f"Created extension: {ext_path}")

    try:
        # Try different Chrome versions
        for version in [139]:
            try:
                driver = uc.Chrome(
                    headless=headless,
                    options=options,
                    use_subprocess=False,
                    version_main=version
                )
                print(f"Successfully created driver with Chrome {version}")
                break
            except Exception as e:
                print(f"Failed with Chrome {version}: {e}")
                continue
        else:
            print("Failed to create driver with any Chrome version")
            return None

        # Give extension time to load
        print("Waiting for extension to initialize...")
        time.sleep(8)  # Increased wait time

        return driver

    except Exception as e:
        print(f"Error creating driver: {e}")
        return None


def setup_driver_alternative_method(headless=True):
    """
    Alternative method: Use subprocess approach with specific flags
    """
    options = uc.ChromeOptions()

    # More aggressive options to handle proxy
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--disable-extensions-except")
    options.add_argument("--disable-default-apps")

    # Set proxy using the format that works with requests
    proxy_host = "pr.oxylabs.io"
    proxy_port = "7777"

    # Try just setting the server without auth in the URL
    options.add_argument(f"--proxy-server=http://{proxy_host}:{proxy_port}")

    # Alternative: Try with authentication bypass flags
    options.add_argument("--proxy-bypass-list=<-loopback>")
    options.add_argument("--disable-features=VizDisplayCompositor")

    if headless:
        options.add_argument("--headless=new")

    try:
        # Try with use_subprocess=True this time
        driver = uc.Chrome(
            headless=headless,
            options=options,
            use_subprocess=True,  # Different from before
            # version_main=130
        )

        return driver

    except Exception as e:
        print(f"Alternative method failed: {e}")
        return None


def setup_driver_with_env_auth(headless=True):
    """
    Try setting proxy auth via environment variables
    """
    import os

    # Set proxy authentication via environment
    os.environ['HTTP_PROXY'] = 'http://umar_lfy_Boeun:umar_LFY1234@pr.oxylabs.io:7777'
    os.environ['HTTPS_PROXY'] = 'http://umar_lfy_Boeun:umar_LFY1234@pr.oxylabs.io:7777'

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    if headless:
        options.add_argument("--headless=new")

    try:
        driver = uc.Chrome(
            headless=headless,
            options=options,
            use_subprocess=False,
            # version_main=130
        )

        return driver

    except Exception as e:
        print(f"Environment auth method failed: {e}")
        return None


def test_proxy_with_driver(driver, method_name):
    """
    Test if proxy is working with the given driver
    """
    if not driver:
        print(f"❌ {method_name}: No driver provided")
        return False

    try:
        print(f"🧪 Testing {method_name}...")

        # Test with multiple services
        test_urls = [
            "https://httpbin.org/ip",
            "https://icanhazip.com/",
            "https://ipinfo.io/ip"
        ]

        for url in test_urls:
            try:
                print(f"  Trying {url}...")
                driver.get(url)

                # Wait for page load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                body_text = driver.find_element(
                    By.TAG_NAME, "body").text.strip()

                # Check for errors
                if "can't be reached" in body_text.lower() or "err_no_supported_proxies" in body_text.lower():
                    print(f"    ❌ Connection error")
                    continue

                # Try to extract IP
                if url == "https://httpbin.org/ip":
                    import json
                    try:
                        data = json.loads(body_text)
                        ip = data.get("origin", "Unknown")
                    except:
                        continue
                else:
                    ip = body_text.strip()

                print(f"    📍 Got IP: {ip}")

                # Check if it's the proxy IP (not your local IP)
                if ip and ip != "119.73.117.47":
                    print(f"✅ {method_name} SUCCESS! Proxy IP: {ip}")
                    return True
                else:
                    print(f"    ⚠️ Still showing local IP")

            except Exception as e:
                print(f"    ❌ Error with {url}: {e}")
                continue

        print(f"❌ {method_name} FAILED - All tests failed")
        return False

    except Exception as e:
        print(f"❌ {method_name} FAILED: {e}")
        return False


def comprehensive_selenium_test():
    """
    Test all Selenium approaches
    """
    print("🚀 Testing all Selenium proxy methods...")

    methods = [
        ("Working Extension", setup_driver_with_working_extension),
        ("Alternative Method", setup_driver_alternative_method),
        ("Environment Auth", setup_driver_with_env_auth)
    ]

    working_methods = []

    for method_name, method_func in methods:
        print(f"\n{'='*50}")
        print(f"Testing: {method_name}")
        print('='*50)

        try:
            # Use non-headless for debugging
            driver = method_func(headless=False)

            if driver:
                success = test_proxy_with_driver(driver, method_name)
                if success:
                    working_methods.append(method_name)

                # Keep successful driver open for inspection
                if success:
                    input(
                        f"✅ {method_name} is working! Press Enter to continue...")

                driver.quit()
            else:
                print(f"❌ {method_name}: Failed to create driver")

        except Exception as e:
            print(f"❌ {method_name}: Exception - {e}")

    print(f"\n🏆 RESULTS:")
    if working_methods:
        print(f"✅ Working methods: {working_methods}")
    else:
        print("❌ No methods worked")
        print("\n🔧 Next steps:")
        print("1. Contact Oxylabs support - mention you can connect via requests but not Chrome")
        print("2. Ask about Chrome-specific proxy setup")
        print("3. Try their official Chrome extension if available")
        print("4. Consider using requests + BeautifulSoup instead of Selenium")


def quick_requests_vs_selenium():
    """
    Compare requests vs selenium for the same proxy
    """
    print("🔄 Comparing requests vs Selenium...")

    # Test with requests (we know this works)
    try:
        import requests
        proxies = {
            'http': 'http://umar_lfy_Boeun:umar_LFY1234@pr.oxylabs.io:7777',
            'https': 'http://umar_lfy_Boeun:umar_LFY1234@pr.oxylabs.io:7777'
        }

        response = requests.get('https://httpbin.org/ip',
                                proxies=proxies, timeout=10)
        requests_ip = response.json().get('origin', 'Unknown')
        print(f"✅ Requests IP: {requests_ip}")

    except Exception as e:
        print(f"❌ Requests failed: {e}")
        return

    # Test with basic Selenium (no undetected-chromedriver)
    print("\n🧪 Trying basic Selenium WebDriver...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--proxy-server=http://pr.oxylabs.io:7777")

        driver = webdriver.Chrome(options=options)
        driver.get("https://httpbin.org/ip")
        time.sleep(3)

        body = driver.find_element(By.TAG_NAME, "body").text
        print(f"Basic Selenium result: {body}")

        driver.quit()

    except Exception as e:
        print(f"Basic Selenium also failed: {e}")


if __name__ == "__main__":
    # First do the comparison
    quick_requests_vs_selenium()

    print("\n" + "="*60)

    # Then run comprehensive test
    comprehensive_selenium_test()
