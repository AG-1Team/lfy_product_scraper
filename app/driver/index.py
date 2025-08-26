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
        # Rotate user agent
        ua = UserAgent()
        user_agent = ua.random
        print(f"[*] Using User-Agent: {user_agent}")

        # Chrome options with server-specific configurations
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
        options.add_argument("--disable-web-security")

        # Window size (important even in headless mode)
        options.add_argument("--window-size=1920,1080")

        # ext_path = create_proxy_extension()
        # options.add_extension(ext_path)

        # CHROME SPECIFIC: Set binary location
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/opt/chrome/chrome',          # custom install path
            '/usr/local/bin/google-chrome'  # symlink from Dockerfile
        ]

        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                print(f"[*] Found Chrome binary at: {path}")
                break

        if chrome_binary:
            options.binary_location = chrome_binary
        else:
            print("[Warning] No Chrome binary found, trying default...")

        # Additional prefs for better performance
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Block images to load faster (optional)
            }
        }
        options.add_experimental_option("prefs", prefs)

        # Find ChromeDriver (system package only)
        chrome_driver_paths = [
            '/usr/bin/chromedriver',           # System chromedriver
            '/opt/chromedriver',               # Custom install
            '/usr/local/bin/chromedriver'      # Manual install
        ]

        driver_path = None
        for path in chrome_driver_paths:
            if os.path.exists(path):
                # Check if it's executable
                if os.access(path, os.X_OK):
                    driver_path = path
                    print(f"[*] Found ChromeDriver at: {path}")
                    break
                else:
                    print(
                        f"[Warning] Found ChromeDriver at {path} but it's not executable")

        if not driver_path:
            print("[Error] No ChromeDriver found at standard locations")
            print("[*] Trying to find chromedriver in PATH...")
            try:
                result = subprocess.run(['which', 'chromedriver'],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    driver_path = result.stdout.strip()
                    print(f"[*] Found ChromeDriver in PATH: {driver_path}")
            except Exception as e:
                print(f"[Warning] PATH search failed: {e}")

        if not driver_path:
            print("[Error] ChromeDriver not found anywhere")
            print("[*] Installation commands:")
            print("    sudo apt-get update")
            print("    sudo apt-get install chrome chrome-driver")
            print("    # or")
            print("    sudo apt-get install google-chrome-stable")
            return None

        # Test if ChromeDriver is working
        try:
            result = subprocess.run([driver_path, '--version'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[*] ChromeDriver version: {result.stdout.strip()}")
            else:
                print(f"[Warning] ChromeDriver test failed: {result.stderr}")
        except Exception as e:
            print(f"[Warning] Could not test ChromeDriver: {e}")

        # Initialize the driver with enhanced error handling
        try:
            service = Service(driver_path)
            # Add service arguments for better Docker compatibility
            service.service_args.extend([
                '--verbose',
                '--log-path=/tmp/chromedriver.log',
                '--whitelisted-ips=',
                '--allowed-origins=*'
            ])

            driver = webdriver.Chrome(service=service, options=options)
            print("[*] Using system chromedriver")
        except Exception as e:
            print(f"[Error] Failed to initialize driver: {e}")
            print("[*] Troubleshooting:")
            print(f"    - ChromeDriver path: {driver_path}")
            print(f"    - Chrome binary: {chrome_binary}")
            print("    - Check permissions: ls -la", driver_path)
            print("    - Check chromedriver log: cat /tmp/chromedriver.log")
            return None

        # ENHANCED: More aggressive timeout settings for server environments
        driver.set_page_load_timeout(60)  # Increased timeout for slow servers
        driver.implicitly_wait(15)  # Increased implicit wait

        # Additional anti-detection measures
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

        # Use selenium-stealth for additional protection
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Linux x86_64",  # Server-appropriate platform
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        # Test if driver works with retry mechanism
        max_test_retries = 3
        for attempt in range(max_test_retries):
            try:
                driver.get("https://httpbin.org/user-agent")
                print(
                    f"[✓] Driver initialized successfully (attempt {attempt + 1})")
                break
            except Exception as e:
                print(f"[Warning] Test failed on attempt {attempt + 1}: {e}")
                if attempt < max_test_retries - 1:
                    time.sleep(5)
                else:
                    print("[Error] Driver test failed after all attempts")
                    driver.quit()
                    return None

        return driver

    except Exception as e:
        print(f"[Error] Failed to setup driver: {e}")
        print("[*] Chrome setup checklist:")
        print("    1. Install: sudo apt-get install chrome chrome-driver")
        print("    2. Test browser: chrome --version")
        print("    3. Test driver: chromedriver --version")
        print("    4. Check permissions: ls -la /usr/bin/chromedriver")
        print("    5. Check shared memory: df -h /dev/shm")
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
