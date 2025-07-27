from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium_stealth import stealth
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
import random
import os
import re
import json
from urllib.parse import urljoin, urlparse
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

def wait_and_retry_on_block(driver, url, max_retries=1):
    """Minimal placeholder: just loads the URL and returns True."""
    try:
        driver.get(url)
        return True
    except Exception as e:
        print(f"[wait_and_retry_on_block] Error: {e}")
        return False

def setup_undetected_driver():
    """Setup undetected Chrome driver with maximum stealth"""
    try:
        print("[*] Setting up undetected Chrome driver...")
        options = uc.ChromeOptions()
        realistic_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        user_agent = random.choice(realistic_agents)
        print(f"[*] Using User-Agent: {user_agent}")
        options.add_argument(f"--user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions-file-access-check")
        options.add_argument("--disable-extensions-http-throttling")
        options.add_argument("--disable-extensions-except")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-translate")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--headless")
        
        common_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900), (1280, 720)
        ]
        width, height = random.choice(common_resolutions)
        options.add_argument(f"--window-size={width},{height}")
        pos_x, pos_y = random.randint(0, 100), random.randint(0, 100)
        options.add_argument(f"--window-position={pos_x},{pos_y}")
        languages = ["en-US,en", "en-GB,en", "en-CA,en"]
        lang = random.choice(languages)
        options.add_argument(f"--accept-lang={lang}")
        timezones = ["Asia/Dubai", "Asia/Kuwait", "Asia/Qatar", "Asia/Riyadh"]
        timezone = random.choice(timezones)
        options.add_argument(f"--timezone={timezone}")
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
                "geolocation": 2,
                "mouse_cursor": 1,
            },
            "profile.managed_default_content_settings.images": 1,
            "profile.managed_default_content_settings.javascript": 1,
            "profile.password_manager_enabled": False,
            "profile.default_content_settings.popups": 0,
            "credentials_enable_service": False,
            "profile.managed_default_content_settings.cookies": 1,
            "profile.cookie_controls_mode": 0,
        }
        options.add_experimental_option("prefs", prefs)
        # Removed excludeSwitches and useAutomationExtension for undetected-chromedriver
        driver = uc.Chrome(options=options, version_main=None)
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined,});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5],});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en'],});
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        if (window.chrome) {
            Object.defineProperty(window.chrome, 'runtime', {get: () => undefined,});
        }
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_js})
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'width': width,
            'height': height,
            'deviceScaleFactor': round(random.uniform(1.0, 2.0), 1),
            'mobile': False
        })
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            'userAgent': user_agent,
            'acceptLanguage': lang,
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64'])
        })
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)
        print("[✅] Undetected driver setup complete")
        return driver
    except Exception as e:
        print(f"[Error] Failed to setup undetected driver: {e}")
        return None

def simulate_human_behavior(driver):
    try:
        width = driver.execute_script("return window.innerWidth")
        height = driver.execute_script("return window.innerHeight")
        body = driver.find_element(By.TAG_NAME, "body")
        actions = ActionChains(driver)
        for _ in range(random.randint(2, 5)):
            x = random.randint(10, max(10, width - 10))
            y = random.randint(10, max(10, height - 10))
            actions.move_to_element_with_offset(body, x, y).pause(random.uniform(0.5, 1.5))
        if random.random() < 0.3:
            actions.click(body)
        actions.perform()
        if random.random() < 0.2:
            actions = ActionChains(driver)
            actions.send_keys(Keys.TAB).pause(random.uniform(0.5, 1.0)).perform()
    except Exception as e:
        print(f"[Debug] Human simulation failed: {e}")

def intelligent_scroll(driver, max_scroll=8):
    try:
        page_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        current_position = 0
        num_scrolls = random.randint(5, max(max_scroll, 5))
        for i in range(num_scrolls):
            progress = current_position / page_height if page_height > 0 else 0
            if progress < 0.3:
                min_pause, max_pause = 2.0, 4.0
            elif progress < 0.7:
                min_pause, max_pause = 1.0, 2.5
            else:
                min_pause, max_pause = 1.5, 3.0
            base_scroll = viewport_height * random.uniform(0.3, 0.8)
            scroll_distance = int(base_scroll + random.randint(-100, 100))
            if random.random() < 0.15 and current_position > 200:
                scroll_distance = -random.randint(50, 150)
            current_position += scroll_distance
            driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
            if random.random() < 0.3:
                pause_time = random.uniform(max_pause, max_pause * 2)
            else:
                pause_time = random.uniform(min_pause, max_pause)
            time.sleep(pause_time)
            if current_position >= page_height * 0.9:
                break
        if random.random() < 0.25:
            scroll_back_to = random.randint(0, int(current_position * 0.5)) if current_position > 0 else 0
            driver.execute_script(f"window.scrollTo({{top: {scroll_back_to}, behavior: 'smooth'}});")
            time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"[Warning] Intelligent scroll failed: {e}")

def wait_with_human_simulation(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        human_delay = random.uniform(1.5, 4.0)
        print(f"[*] Simulating human reading delay: {human_delay:.1f}s")
        time.sleep(human_delay)
        if random.random() < 0.4:
            simulate_human_behavior(driver)
        return True
    except Exception as e:
        print(f"[Warning] Page load wait with simulation failed: {e}")
        return False

def visit_decoy_pages(driver):
    decoy_sites = [
        "https://www.ounass.ae",
        "https://www.ounass.ae/women",
        "https://www.ounass.ae/men",
    ]
    print("[*] Building realistic browsing history...")
    for i, site in enumerate(decoy_sites):
        try:
            print(f"[*] Visiting decoy page {i+1}: {site}")
            driver.get(site)
            wait_with_human_simulation(driver, 20)
            intelligent_scroll(driver, max_scroll=3)
            delay = random.uniform(3, 8)
            print(f"[*] Browsing delay: {delay:.1f}s")
            time.sleep(delay)
        except Exception as e:
            print(f"[Warning] Decoy page visit failed: {e}")
            continue

def enhanced_collect_product_links(driver, category_url, max_products=5):
    print(f"\n[*] Collecting product links from: {category_url}")
    product_links = []
    try:
        if random.random() < 0.3:
            visit_decoy_pages(driver)
        driver.get(category_url)
        # Save the page source for debugging
        try:
            with open('debug_category_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("[*] Saved debug_category_page.html for inspection.")
        except Exception as e:
            print(f"[Warning] Could not save debug_category_page.html: {e}")
        wait_with_human_simulation(driver, 45)
        # Wait for the product grid to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.PLPDesktop-grid"))
            )
            print("[✅] Product grid found with selector: ul.PLPDesktop-grid")
        except Exception as e:
            print("[Warning] Product grid not found with selector ul.PLPDesktop-grid")
            print("[DEBUG] Page source snippet:", driver.page_source[:500])
        intelligent_scroll(driver, max_scroll=10)
        time.sleep(random.uniform(2, 4))
        # Find all product containers (cards)
        product_containers = driver.find_elements(By.CSS_SELECTOR, "li.StyleColorListItem")
        if not product_containers:
            print("[Error] No product containers found with selector li.StyleColorListItem")
            divs = driver.find_elements(By.TAG_NAME, "div")
            class_names = set()
            for div in divs:
                class_attr = div.get_attribute("class")
                if class_attr:
                    class_names.update(class_attr.split())
            print("[DEBUG] All div class names on page:", list(class_names)[:30])
            return []
        print(f"[✅] Found {len(product_containers)} products with selector: li.StyleColorListItem")
        indices = list(range(len(product_containers)))
        random.shuffle(indices)
        for i in indices:
            if len(product_links) >= max_products:
                break
            container = product_containers[i]
            try:
                # Find the product link inside the card
                a_tag = container.find_element(By.CSS_SELECTOR, "a[href^='/shop-']")
                href = a_tag.get_attribute("href")
                if href and href not in product_links:
                    product_links.append(href)
                    print(f"[+] Product link {len(product_links)}: {href}")
                    time.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                print(f"[Debug] Error extracting from container {i}: {e}")
                continue
        print(f"[✅] Successfully collected {len(product_links)} product links")
        return product_links
    except Exception as e:
        print(f"[Error] Failed to collect links: {e}")
        return []

def extract_breadcrumb_category(driver, soup):
    """Extract breadcrumb category path for Ounass"""
    try:
        # Look for breadcrumb elements specific to Ounass
        breadcrumb_selectors = [
            '.breadcrumb a',
            '[class*="breadcrumb"] a',
            'nav[aria-label*="breadcrumb"] a',
            '.breadcrumbs a',
            '[data-testid="breadcrumb"] a'
        ]
        
        breadcrumbs = []
        for selector in breadcrumb_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and text.lower() not in ['home', 'ounass']:
                        breadcrumbs.append(text)
            except:
                continue
        
        if breadcrumbs:
            return ' > '.join(breadcrumbs)
        
        # Fallback: try to extract from URL
        current_url = driver.current_url
        if '/women/' in current_url:
            return 'Women'
        elif '/men/' in current_url:
            return 'Men'
        elif '/kids/' in current_url:
            return 'Kids'
        else:
            return 'Unknown'
            
    except Exception as e:
        print(f"[Warning] Error extracting breadcrumb: {e}")
        return 'Unknown'

def extract_aed_price(soup):
    """Extract price in AED for Ounass"""
    try:
        # Look for price elements specific to Ounass
        price_selectors = [
            '[data-testid="price"]',
            '.price',
            '.current-price',
            '[class*="price"]',
            '.product-price',
            '.price-current',
            '.price-value'
        ]
        
        for selector in price_selectors:
            try:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Extract numeric value
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        return float(price_match.group())
            except:
                continue
        
        return None

    except Exception as e:
        print(f"[Warning] Error extracting AED price: {e}")
        return None

def calculate_currency_prices(aed_price):
    """Calculate prices in different currencies based on AED"""
    if not aed_price:
        return {
            'price_aed': '',
            'price_usd': '',
            'price_gbp': '',
            'price_eur': ''
        }
    
    return {
        'price_aed': f"AED {aed_price:,.2f}",
        'price_usd': f"USD {aed_price * 0.27:.2f}",
        'price_gbp': f"GBP {aed_price * 0.21:.2f}",
        'price_eur': f"EUR {aed_price * 0.25:.2f}"
    }

def extract_sale_info(soup):
    """Extract sale price, original price, and discount percentage for Ounass"""
    sale_info = {
        'original_price': '',
        'sale_price': '',
        'discount': ''
    }
    
    try:
        # Look for original price (strikethrough) - Ounass specific
        original_selectors = [
            's',
            'del',
            '.strikethrough',
            '[class*="PriceContainer-slashedPrice"][class*="original"][class*="price"]',
            '.original-price',
            '.price-original',
            '.was-price'
        ]
        
        original_price = None
        for selector in original_selectors:
            try:
                orig_elem = soup.select_one(selector)
                if orig_elem:
                    orig_text = orig_elem.get_text(strip=True)
                    price_match = re.search(r'[\d,]+\.?\d*', orig_text.replace(',', ''))
                    if price_match:
                        original_price = float(price_match.group())
                        sale_info['original_price'] = f"AED {original_price:,.2f}"
                        break
            except:
                continue
        
        # Look for sale price - Ounass specific
        sale_selectors = [
            '[class*="PriceContainer-price"][class*="sale"][class*="price"]',
            '.sale-price',
            '.price-sale',
            '[data-testid="price"]',
            '.price-current',
            '.now-price'
        ]
        
        sale_price = None
        for selector in sale_selectors:
            try:
                sale_elem = soup.select_one(selector)
                if sale_elem:
                    sale_text = sale_elem.get_text(strip=True)
                    price_match = re.search(r'[\d,]+\.?\d*', sale_text.replace(',', ''))
                    if price_match:
                        sale_price = float(price_match.group())
                        sale_info['sale_price'] = f"AED {sale_price:,.2f}"
                        break
            except:
                continue
        
        # Calculate discount percentage if both prices are available
        if original_price and sale_price and original_price > sale_price:
            discount = ((original_price - sale_price) / original_price) * 100
            sale_info['discount'] = f"{discount:.0f}%"
                
    except Exception as e:
        print(f"[Warning] Error extracting sale info: {e}")
    
    return sale_info

def extract_size_and_fit(soup):
    """Extract size and fit information for Ounass"""
    try:
        size_fit_info = []
        
        # Look for size elements - Ounass specific
        size_selectors = [
            '[data-testid*="size"]',
            '[class*="size"]',
            '.size-option',
            'button[class*="size"]',
            '.size-selector',
            '.product-size',
            '.size-button'
        ]
        
        sizes = []
        for selector in size_selectors:
            try:
                size_elements = soup.select(selector)
                for elem in size_elements:
                    size_text = elem.get_text(strip=True)
                    if size_text and len(size_text) <= 10:
                        sizes.append(size_text)
            except:
                continue
        
        if sizes:
            size_fit_info.append(f"Available Sizes: {', '.join(set(sizes))}")
        
        # Look for fit information - Ounass specific
        fit_selectors = [
            '[class*="fit"]',
            '[class*="measurement"]',
            '.fit-guide',
