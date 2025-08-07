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
            if max_products is not None and len(product_links) >= max_products:
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
            '.size-guide',
            '.measurement-info',
            '.product-fit',
            '.size-chart'
        ]
        
        fit_info = []
        for selector in fit_selectors:
            try:
                fit_elements = soup.select(selector)
                for elem in fit_elements:
                    fit_text = elem.get_text(strip=True)
                    if fit_text and len(fit_text) > 10 and 'model' not in fit_text.lower():
                        fit_info.append(fit_text)
            except:
                continue
        
        if fit_info:
            size_fit_info.append(f"Fit Guide: {' | '.join(fit_info)}")
        
        # Look for Size & Fit accordion section - Ounass specific
        for section in soup.find_all(['section', 'div'], {'class': ['accordion', 'size-fit', 'product-details', 'product-info']}):
            # Look for size & fit related text
            section_text = section.get_text(strip=True).lower()
            if any(keyword in section_text for keyword in ['size', 'fit', 'measurement', 'guide']):
                panel_text = ' '.join(section.stripped_strings)
                if panel_text:
                    if "no fitting details" in panel_text.lower() or "no size guide" in panel_text.lower():
                        size_fit_info.append("Size & Fit: No fitting details available")
                    else:
                        size_fit_info.append(f"Size & Fit Details: {panel_text}")
                break
        
        return ' | '.join(size_fit_info) if size_fit_info else ''
        
    except Exception as e:
        print(f"[Warning] Error extracting size/fit: {e}")
        return ''

def extract_product_details(driver, url):
    product_data = {
        'product_url': url,
        'brand': '',
        'product_name': '',
        'product_details': '',
        'category': '',
        'image_urls': '',
        'original_price': '',
        'sale_price': '',
        'discount': '',
        'price_aed': '',
        'price_usd': '',
        'price_gbp': '',
        'price_eur': '',
        'size_and_fit': ''
    }
    try:
        print(f"\n[*] Scraping: {url}")
        driver.get(url)
        
        # Wait for critical elements to load
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.PDPMobile-name, h1.product-name"))
        )
        
        # Allow time for dynamic content to load
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # BRAND
        brand_elem = soup.select_one('a.PDPMobile-brand, .product-brand, [data-testid="brand-name"]')
        if brand_elem:
            product_data['brand'] = brand_elem.get_text(strip=True)

        # PRODUCT NAME
        name_elem = soup.select_one('h1.PDPMobile-name, h1.product-name, [data-testid="product-name"]')
        if name_elem:
            product_data['product_name'] = name_elem.get_text(strip=True)
            # Remove brand name if included
            if product_data['brand'] and product_data['brand'] in product_data['product_name']:
                product_data['product_name'] = product_data['product_name'].replace(product_data['brand'], '').strip()

        # PRICE
        price_elem = soup.select_one('.PriceContainer-price, .price-value, [data-testid="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Extract numeric value
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                aed_price = float(price_match.group())
                currency_prices = calculate_currency_prices(aed_price)
                product_data.update(currency_prices)

        # CATEGORY
        breadcrumbs = []
        breadcrumb_elems = soup.select('ol.BreadcrumbList li span[itemprop="name"], .breadcrumb a')
        for elem in breadcrumb_elems:
            text = elem.get_text(strip=True)
            if text and text.lower() not in ['home', 'ounass']:
                breadcrumbs.append(text)
        product_data['category'] = ' > '.join(breadcrumbs) if breadcrumbs else 'Unknown'
        details_dict = {}

        # Define the tab-panel IDs you want to process
        panel_ids = [
            'content-tab-panel-0',
            'content-tab-panel-1',
            'content-tab-panel-2',
            'content-tab-panel-3'  # Duplicate intentionally, as mentioned
        ]

        for panel_id in panel_ids:
            tab_id = panel_id.replace('-panel', '')  # e.g., 'content-tab-0'
            
            tab_elem = soup.select_one(f'#{tab_id}')       # For key
            panel_elem = soup.select_one(f'#{panel_id}')   # For value

            if tab_elem and panel_elem:
                key_text = tab_elem.get_text(" ", strip=True)
                
                # Get all <p> tags inside the panel
                p_tags = panel_elem.find_all('p')
                value_text = ' '.join(p.get_text(" ", strip=True) for p in p_tags)

                if key_text and value_text:
                    details_dict[key_text] = value_text

        product_data['product_details'] = details_dict if details_dict else 'No details available'

        # IMAGE URLS
        image_urls = []
        for img in soup.select('img[src*="images.ounass"], .product-image, [data-testid="product-image"]'):
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src:
                # Convert to high-res if possible
                src = re.sub(r'_small|_medium', '_large', src)
                if src not in image_urls:
                    image_urls.append(src)
        product_data['image_urls'] = ', '.join(image_urls[:5])  # Limit to 5 images

        # SALE INFO
        sale_info = extract_sale_info(soup)
        product_data['original_price'] = sale_info['original_price']
        product_data['sale_price'] = sale_info['sale_price']
        product_data['discount'] = sale_info['discount']

        # SIZE & FIT
        product_data['size_and_fit'] = extract_size_and_fit(soup)

        return product_data
    except Exception as e:
        print(f"[Error] Failed to scrape {url}: {e}")
        return product_data

def extract_product_details_enhanced(driver, url):
    product_data = {
        'product_url': url,
        'brand': '',
        'product_name': '',
        'product_details': {},
        'category': '',
        'image_urls': '',
        'original_price': '',
        'sale_price': '',
        'discount': '',
        'price_aed': '',
        'price_usd': '',
        'price_gbp': '',
        'price_eur': '',
        'size_and_fit': ''
    }
    try:
        print(f"\n[*] Scraping: {url}")
        if not wait_and_retry_on_block(driver, url):
            print(f"[❌] Failed to load product page: {url}")
            return product_data
        simulate_human_behavior(driver)
        time.sleep(2)  # Ensure page is rendered
        # Wait for gallery or at least one product image to appear
        try:
            WebDriverWait(driver, 15).until(
                lambda d: (
                    d.find_elements(By.CSS_SELECTOR, '.ImageGalleryMobile-slides img[src*="atgcdn.ae"]') or
                    d.find_elements(By.CSS_SELECTOR, '.ImageGalleryMobile img[src*="atgcdn.ae"]') or
                    d.find_elements(By.CSS_SELECTOR, 'img[src*="atgcdn.ae"]')
                )
            )
            time.sleep(1)  # Give a little extra time for images to load
        except Exception as e:
            print(f"[Warning] Gallery images did not appear in time: {e}")
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        try:
            with open('debug_product_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("[*] Saved debug_product_page.html for inspection.")
        except Exception as e:
            print(f"[Warning] Could not save debug_product_page.html: {e}")
        # BRAND (try h2.PDPDesktop-designerCategoryName, then inside a, then fallbacks)
        brand_elem = soup.select_one('h2.PDPDesktop-designerCategoryName')
        if not brand_elem:
            brand_elem = soup.select_one('a.PDPDesktop-designerCategoryLink h2.PDPDesktop-designerCategoryName')
        if not brand_elem:
            brand_selectors = [
                'a.PDPMobile-brand', '.product-brand', '[data-testid="brand-name"]',
                '[class*="brand"]', '.brand', 'a[class*="brand"]'
            ]
            for selector in brand_selectors:
                brand_elem = soup.select_one(selector)
                if brand_elem:
                    break
        if brand_elem:
            product_data['brand'] = brand_elem.get_text(strip=True)
        # PRODUCT NAME (BeautifulSoup only)
        name_elem = soup.select_one('h1.PDPMobile-name')
        if not name_elem:
            name_selectors = [
                'h1.PLPDesktop-name', 'h1.product-name', 'h1.ProductDetails-name',
                '[data-testid="product-name"]', 'h1[class*="product"]',
                '.product-title', 'h1[class*="name"]', 'h1'  # Fallbacks
            ]
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    break
        if name_elem:
            name = name_elem.get_text(strip=True)
            if product_data['brand'] and product_data['brand'] in name:
                name = name.replace(product_data['brand'], '').strip()
            product_data['product_name'] = name
        if not product_data['product_name']:
            print("[Error] Product name not found in HTML. See debug_product_page.html.")
            print("[DEBUG] HTML snippet:", html[:500])
        # PRICE (prefer .PriceContainer-price)
        price_elem = soup.select_one('.PriceContainer-price')
        if not price_elem:
            price_selectors = [
                '.price-value', '[data-testid="price"]',
                '.price', '.current-price', '[class*="price"]'
            ]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    break
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                aed_price = float(price_match.group())
                currency_prices = calculate_currency_prices(aed_price)
                product_data.update(currency_prices)
        # CATEGORY (breadcrumbs)
        breadcrumb_selectors = [
            'ol.BreadcrumbList li span[itemprop="name"]', '.breadcrumb a',
            '[class*="breadcrumb"] a', 'nav[aria-label*="breadcrumb"] a'
        ]
        breadcrumbs = []
        for selector in breadcrumb_selectors:
            breadcrumb_elems = soup.select(selector)
            if breadcrumb_elems:
                for elem in breadcrumb_elems:
                    text = elem.get_text(strip=True)
                    if text and text.lower() not in ['home', 'ounass']:
                        breadcrumbs.append(text)
                break
        product_data['category'] = ' > '.join(breadcrumbs) if breadcrumbs else 'Unknown'
        # PRODUCT DETAILS (prefer Design details, fallback to first details.ContentAccordion, then others)
        details_dict = {}

        # Define the tab-panel IDs you want to process
        panel_ids = [
            'content-tab-panel-0',
            'content-tab-panel-1',
            'content-tab-panel-2',
            'content-tab-panel-3'  # Duplicate intentionally, as mentioned
        ]

        for panel_id in panel_ids:
            tab_id = panel_id.replace('-panel', '')  # e.g., 'content-tab-0'
            
            tab_elem = soup.select_one(f'#{tab_id}')       # For key
            panel_elem = soup.select_one(f'#{panel_id}')   # For value

            if tab_elem and panel_elem:
                key_text = tab_elem.get_text(" ", strip=True)
                
                # Get all <p> tags inside the panel
                p_tags = panel_elem.find_all('p')
                value_text = ' '.join(p.get_text(" ", strip=True) for p in p_tags)

                if key_text and value_text:
                    details_dict[key_text] = value_text

        product_data['product_details'] = details_dict if details_dict else 'No details available'
        # IMAGE URLS (robust: try gallery, then fallbacks, filter by atgcdn.ae)
        image_urls = []
        # 1. Try .ImageGalleryMobile-slides
        gallery = soup.select_one('.ImageGalleryMobile-slides')
        if gallery:
            for img in gallery.find_all('img', src=True):
                src = img['src']
                if 'atgcdn.ae' in src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://www.ounass.ae' + src
                    src = re.sub(r'dw=\\d+', 'dw=1200', src)
                    if src not in image_urls:
                        image_urls.append(src)
        # 2. Fallback: .ImageGalleryMobile img
        if not image_urls:
            for img in soup.select('.ImageGalleryMobile img[src*="atgcdn.ae"]'):
                src = img['src']
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.ounass.ae' + src
                src = re.sub(r'dw=\\d+', 'dw=1200', src)
                if src not in image_urls:
                    image_urls.append(src)
        # 3. Fallback: any img[src*="atgcdn.ae"]
        if not image_urls:
            for img in soup.find_all('img', src=True):
                src = img['src']
                if 'atgcdn.ae' in src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://www.ounass.ae' + src
                    src = re.sub(r'dw=\\d+', 'dw=1200', src)
                    if src not in image_urls:
                        image_urls.append(src)
        product_data['image_urls'] = ', '.join(image_urls)
        # SALE INFO
        sale_info = extract_sale_info(soup)
        product_data.update(sale_info)
        # SIZE & FIT
        product_data['size_and_fit'] = extract_size_and_fit(soup)
        return product_data
    except Exception as e:
        print(f"[Error] Failed to scrape {url}: {e}")
        with open('debug_product_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("[*] Saved debug_product_page.html for inspection.")
        return product_data

def download_product_images(product_data, download_images_flag=True):
    if not download_images_flag or not product_data['image_urls'] or not product_data['product_name']:
        print(f"[DEBUG] Skipping image download: download_images_flag={download_images_flag}, image_urls={product_data['image_urls']}, product_name={product_data['product_name']}")
        return
    try:
        folder_name = re.sub(r'[^ - \w-]', '', product_data['product_name'])[:50]
        folder_name = re.sub(r'\s+', '_', folder_name)
        if not folder_name.strip('_'):
            folder_name = f"product_{hash(product_data['product_url']) % 10000}"
        product_folder = os.path.join('images', folder_name)
        os.makedirs(product_folder, exist_ok=True)
        print(f"Saving images to: {os.path.abspath(product_folder)}")
        image_urls = product_data['image_urls'].split(', ')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/,/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        print(f"[*] Downloading images to: {product_folder}")
        for i, img_url in enumerate(image_urls[:8], 1):
            try:
                print(f"[DEBUG] Attempting to download image {i}: {img_url}")
                response = requests.get(img_url, timeout=15, headers=headers)
                print(f"[DEBUG] Response status for image {i}: {response.status_code}, Content-Length: {len(response.content)}")
                if response.status_code == 200 and len(response.content) > 1000:
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'
                    elif 'png' in content_type:
                        ext = '.png'
                    elif 'webp' in content_type:
                        ext = '.webp'
                    else:
                        ext = '.jpg'
                    safe_name = re.sub(r'[^ - \w-]', '', product_data['product_name'])[:30]
                    safe_name = re.sub(r'\s+', '_', safe_name)
                    filename = f"{safe_name} pic {i}{ext}"
                    filepath = os.path.join(product_folder, filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    print(f"[✓] Downloaded: {filename}")
                else:
                    print(f"[Warning] Image {i} not downloaded: status {response.status_code}, content length {len(response.content)}")
            except Exception as e:
                print(f"[Warning] Failed to download image {i}: {e}")
            time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"[Error] Failed to download images: {e}")


def load_existing_data():
    """Load existing scraped data to prevent duplicates"""
    existing_products = []
    existing_urls = set()
    
    # Try to load existing CSV file
    csv_filename = 'ounass_products.csv'
    if os.path.exists(csv_filename):
        try:
            df = pd.read_csv(csv_filename, encoding='utf-8-sig')
            existing_products = df.to_dict('records')
            existing_urls = set(product['product_url'] for product in existing_products if 'product_url' in product)
            print(f"[*] Loaded {len(existing_products)} existing products from {csv_filename}")
        except Exception as e:
            print(f"[Warning] Could not load existing CSV: {e}")
    
    # Try to load existing JSON file as backup
    json_filename = 'ounass_products.json'
    if not existing_products and os.path.exists(json_filename):
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
                existing_urls = set(product['product_url'] for product in existing_products if 'product_url' in product)
                print(f"[*] Loaded {len(existing_products)} existing products from {json_filename}")
        except Exception as e:
            print(f"[Warning] Could not load existing JSON: {e}")
    
    return existing_products, existing_urls

def save_data_with_append(all_products, existing_products):
    """Save data by appending to existing files"""
    # Create DataFrame for new products only
    if not all_products:
        print("[!] No new products to save")
        return 'ounass_products.csv', 'ounass_products.json', len(existing_products)
    
    new_df = pd.DataFrame(all_products)
    
    # CSV filename
    csv_filename = 'ounass_products.csv'
    json_filename = 'ounass_products.json'
    
    # Try to append to existing CSV
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if existing_products and os.path.exists(csv_filename):
                # Load existing CSV and append new data
                existing_df = pd.read_csv(csv_filename, encoding='utf-8-sig')
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"[✅] Successfully appended {len(all_products)} new products to {csv_filename}")
            else:
                # No existing data, create new file
                new_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"[✅] Successfully created new {csv_filename} with {len(all_products)} products")
            break
        except PermissionError:
            if attempt < max_retries - 1:
                print(f"[⏳] Permission denied, retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                # Last resort: create timestamped backup
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_csv = f'ounass_products_{timestamp}.csv'
                new_df.to_csv(backup_csv, index=False, encoding='utf-8-sig')
                print(f"[⚠] Could not save to {csv_filename} after {max_retries} attempts")
                print(f"[💾] Saved to backup file: {backup_csv}")
                csv_filename = backup_csv
        except Exception as e:
            print(f"[Error] Failed to save CSV: {e}")
            break
    
    # Save JSON (combine existing + new)
    try:
        combined_products = existing_products + all_products if existing_products else all_products
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(combined_products, f, indent=2, ensure_ascii=False)
        print(f"[✅] Successfully saved to {json_filename}")
    except Exception as e:
        print(f"[Error] Failed to save JSON: {e}")
    
    return csv_filename, json_filename, len(combined_products)

def main():
    MAX_PRODUCTS_PER_CATEGORY = None  # Scrape all products
    DOWNLOAD_IMAGES = True
    categories = {
        'Women Clothing': {
            'url': 'https://www.ounass.ae/women/clothing',
            'path': 'Women > Clothing'
        },
        'Women Shoes': {
            'url': 'https://www.ounass.ae/women/shoes',
            'path': 'Women > Shoes'
        },
        'Women Bags': {
            'url': 'https://www.ounass.ae/women/bags',
            'path': 'Women > Bags'
        },
        'Women Beauty': {
            'url': 'https://www.ounass.ae/women/beauty',
            'path': 'Women > Beauty'
        },
        'Women Fine Jewellery': {
            'url': 'https://www.ounass.ae/women/jewellery/fine-jewellery',
            'path': 'Women > Jewellery > Fine Jewellery'
        },
        'Women Fashion Jewellery': {
            'url': 'https://www.ounass.ae/women/jewellery/fashion-jewellery',
            'path': 'Women > Jewellery > Fashion Jewellery'
        },
        'Women Accessories': {
            'url': 'https://www.ounass.ae/women/accessories',
            'path': 'Women > Accessories'
        },
        'Women Gifts': {
            'url': 'https://www.ounass.ae/women/edits/gifts-for-her',
            'path': 'Women > Gifts'
        },
        'Women Home': {
            'url': 'https://www.ounass.ae/women/home',
            'path': 'Women > Home'
        },
        'Women Pre-loved': {
            'url': 'https://www.ounass.ae/women/pre-loved',
            'path': 'Women > Pre-loved'
        },
        'Men Clothing': {
            'url': 'https://www.ounass.ae/men/clothing',
            'path': 'Men > Clothing'
        },
        'Men Shoes': {
            'url': 'https://www.ounass.ae/men/shoes',
            'path': 'Men > Shoes'
        },
        'Men Accessories': {
            'url': 'https://www.ounass.ae/men/accessories',
            'path': 'Men > Accessories'
        },
        'Men Grooming': {
            'url': 'https://www.ounass.ae/men/grooming',
            'path': 'Men > Grooming'
        },
        'Men Gifts': {
            'url': 'https://www.ounass.ae/men/edits/gifts-for-him',
            'path': 'Men > Gifts'
        },
        'Men Bags': {
            'url': 'https://www.ounass.ae/men/bags',
            'path': 'Men > Bags'
        },
        'Men Watches': {
            'url': 'https://www.ounass.ae/men/watches',
            'path': 'Men > Watches'
        },
        'Men Home': {
            'url': 'https://www.ounass.ae/men/home',
            'path': 'Men > Home'
        },
        'Kids Baby': {
            'url': 'https://www.ounass.ae/kids/baby',
            'path': 'Kids > Baby'
        },
        'Kids Girl': {
            'url': 'https://www.ounass.ae/kids/girl',
            'path': 'Kids > Girl'
        },
        'Kids Boy': {
            'url': 'https://www.ounass.ae/kids/boy',
            'path': 'Kids > Boy'
        },
        'Kids Shoes': {
            'url': 'https://www.ounass.ae/kids/shoes',
            'path': 'Kids > Shoes'
        },
        'Kids Accessories': {
            'url': 'https://www.ounass.ae/kids/accessories',
            'path': 'Kids > Accessories'
        },
        'Kids Gifts': {
            'url': 'https://www.ounass.ae/kids/edits/all-gifts',
            'path': 'Kids > Gifts'
        },
        'Kids Edits': {
            'url': 'https://www.ounass.ae/kids/edits',
            'path': 'Kids > Edits'
        },
    }
    print("=" * 80)
    print("🛍  OUNASS ENHANCED ANTI-DETECTION SCRAPER")
    print("=" * 80)
    print(f"[*] Products per category: {MAX_PRODUCTS_PER_CATEGORY}")
    print(f"[*] Categories to scrape: {len(categories)}")
    existing_products, existing_urls = load_existing_data()
    print(f"[*] Found {len(existing_urls)} existing product URLs to skip")
    print("\n[*] Setting up enhanced anti-detection driver...")
    driver = setup_undetected_driver()
    if not driver:
        print("[❌] Failed to initialize browser driver")
        return
    all_products = []
    try:
        for category_name, category_info in categories.items():
            print(f"\n{'='*50}")
            print(f"📂 SCRAPING {category_name.upper()} CATEGORY")
            print(f"{'='*50}")
            if category_name != list(categories.keys())[0]:
                wait_time = random.uniform(15, 30)
                print(f"[💤] Waiting {wait_time:.1f} seconds before next category...")
                time.sleep(wait_time)
            product_links = enhanced_collect_product_links(driver, category_info['url'], MAX_PRODUCTS_PER_CATEGORY)
            if not product_links:
                print(f"[⚠] No products found in {category_name} category")
                continue
            new_product_links = [url for url in product_links if url not in existing_urls]
            if not new_product_links:
                print(f"[ℹ] All products in {category_name} already scraped")
                continue
            print(f"[🆕] Scraping {len(new_product_links)} new products")
            for i, url in enumerate(new_product_links, 1):
                print(f"\n[*] Processing product {i}/{len(new_product_links)}")
                if i > 1:
                    delay = random.uniform(10, 20)
                    print(f"[💤] Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
                product_data = extract_product_details_enhanced(driver, url)
                if product_data['product_name']:
                    all_products.append(product_data)
                    print(f"[✅] Successfully scraped: {product_data['product_name'][:50]}")
                    print(f"[DEBUG] Extracted image URLs: {product_data['image_urls']}")
                    download_product_images(product_data, True)
    finally:
        driver.quit()
        print("[✅] Browser closed successfully")
    save_data_with_append(all_products, existing_products)

if __name__ == "__main__":
    main()
