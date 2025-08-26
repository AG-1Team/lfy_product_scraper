import os
import time
import subprocess

from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth


def setup_farfetch_driver():
    """Setup stealth-enabled Chrome driver optimized for server environments"""
    try:
        # Rotate UA
        ua = UserAgent()
        user_agent = ua.random
        print(f"[*] Using User-Agent: {user_agent}")

        options = Options()
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--window-size=1920,1080")

        # Locate Chrome binary
        chrome_paths = [
            '/opt/chrome/chrome',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/local/bin/google-chrome'
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                options.binary_location = path
                print(f"[*] Found Chrome binary at: {path}")
                break

        # ✅ Force system chromedriver (no UC downloader!)
        driver_path = "/usr/local/bin/chromedriver"
        if not os.path.exists(driver_path):
            raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")

        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        print("[*] Using system chromedriver")

        # Basic timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(15)

        # Anti-detection tweaks
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux x86_64",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        # Test driver
        for attempt in range(3):
            try:
                driver.get("https://httpbin.org/user-agent")
                print(
                    f"[✓] Driver initialized successfully (attempt {attempt+1})")
                break
            except Exception as e:
                print(f"[Warning] Test failed on attempt {attempt+1}: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    driver.quit()
                    raise RuntimeError("Farfetch driver init failed")

        return driver

    except Exception as e:
        print(f"[Error] Failed to setup Farfetch driver: {e}")
        return None
def detect_browser():
    """Detect which browser is available on the system"""
    browsers = {
        'chrome': ['/usr/bin/chrome', '/usr/bin/chrome-browser'],
        'chrome': ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable']
    }

    for browser_name, paths in browsers.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, '--version'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(
                            f"[*] Found {browser_name}: {result.stdout.strip()}")
                        return browser_name, path
                except:
                    continue

    return None, None


def test_system_setup():
    """Test if the system is properly configured for Selenium"""
    print("[*] Testing system setup...")

    # Test browser
    browser_name, browser_path = detect_browser()
    if browser_name:
        print(f"[✓] Browser found: {browser_name} at {browser_path}")
    else:
        print("[✗] No browser found")
        return False

    # Test driver
    try:
        result = subprocess.run(['chromedriver', '--version'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[✓] ChromeDriver: {result.stdout.strip()}")
        else:
            print("[✗] ChromeDriver test failed")
            return False
    except FileNotFoundError:
        print("[✗] ChromeDriver not found in PATH")
        return False
    except Exception as e:
        print(f"[✗] ChromeDriver error: {e}")
        return False

    print("[✓] System setup looks good!")
    return True
