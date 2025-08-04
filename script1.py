from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
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
from selenium.webdriver.common.keys import Keys 
from collections import defaultdict
import traceback 

def setup_driver():
    """Setup stealth-enabled Chrome driver optimized for server environments"""
    try:
        # Rotate user agent
        ua = UserAgent()
        user_agent = ua.random
        print(f"[*] Using User-Agent: {user_agent}")
        
        # Chrome options with server-specific configurations
        options = Options()
        options.add_argument(f"user-agent={user_agent}")
        
        # CRITICAL: Server-specific arguments
        options.add_argument("--headless")  
        options.add_argument("--no-sandbox")  # Required for Docker/containers
        options.add_argument("--disable-dev-shm-usage")  # Prevents crashes
        options.add_argument("--disable-gpu")  # No GPU on most servers
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--disable-oopr-debug-crash-dump")
        options.add_argument("--no-crash-upload")
        options.add_argument("--disable-low-res-tiling")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--mute-audio")
        # options.add_argument("--incognito")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        
        # Memory and performance optimizations for servers
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-gpu-logging")
        options.add_argument("--silent")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-features=BlinkGenPropertyTrees")
        
        # Enhanced timeout and performance settings
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Window size (important even in headless mode)
        options.add_argument("--window-size=1920,1080")
        
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
        
        # Try different service initialization methods
        try:
            # Method 1: Use webdriver-manager (best for servers)
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            print("[*] Using webdriver-manager")
        except Exception as e1:
            print(f"[Warning] Webdriver-manager failed: {e1}")
            try:
                # Method 2: Use system chromedriver
                service = Service()
                driver = webdriver.Chrome(service=service, options=options)
                print("[*] Using system chromedriver")
            except Exception as e2:
                print(f"[Warning] System chromedriver failed: {e2}")
                try:
                    # Method 3: Specify common chromedriver paths
                    for path in ['/usr/local/bin/chromedriver', '/usr/bin/chromedriver', '/opt/chromedriver']:
                        try:
                            service = Service(path)
                            driver = webdriver.Chrome(service=service, options=options)
                            print(f"[*] Using chromedriver at {path}")
                            break
                        except:
                            continue
                    else:
                        raise Exception("No chromedriver found")
                except Exception as e3:
                    print(f"[Error] All methods failed:")
                    print(f"  Webdriver-manager: {e1}")
                    print(f"  System: {e2}")
                    print(f"  Paths: {e3}")
                    print("[*] Install suggestions:")
                    print("    pip install webdriver-manager")
                    print("    sudo apt-get install chromium-browser chromium-chromedriver")
                    return None
        
        # ENHANCED: More aggressive timeout settings for server environments
        driver.set_page_load_timeout(60)  # Increased timeout for slow servers
        driver.implicitly_wait(15)  # Increased implicit wait
        
        # Additional anti-detection measures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
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
                print(f"[✓] Driver initialized successfully (attempt {attempt + 1})")
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
        print("[*] Server setup checklist:")
        print("    1. Install Chrome: sudo apt-get install google-chrome-stable")
        print("    2. Install ChromeDriver: sudo apt-get install chromium-chromedriver")
        print("    3. Install webdriver-manager: pip install webdriver-manager")
        print("    4. Check permissions: ls -la /usr/bin/chromedriver")
        print("    5. Test Chrome: google-chrome --version")
        return None

def extract_breadcrumb_category(driver, soup):
    """Extract breadcrumb category path"""
    try:
        # Look for breadcrumb elements
        breadcrumb_selectors = [
            '[data-testid="breadcrumb"] a',
            '.breadcrumb a',
            '[class*="breadcrumb"] a',
            'nav[aria-label*="breadcrumb"] a',
            '.breadcrumbs a'
        ]
        
        breadcrumbs = []
        for selector in breadcrumb_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and text.lower() not in ['home', 'farfetch']:
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
    """Extract price in AED (raw site currency)"""
    try:
        # Look for price elements
        price_selectors = [
            '[data-testid="price-current"]',
            '.price-current',
            '.current-price',
            '[class*="current"][class*="price"]',
            '[data-component="Price"]',
            '.price'
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

def extract_sale_info(soup):
    """Extract sale price, original price, and discount percentage"""
    sale_info = {
        'original_price': '',
        'sale_price': '',
        'discount': ''
    }
    
    try:
        # Look for original price (strikethrough)
        original_selectors = [
            's',
            'del',
            '.strikethrough',
            '[class*="original"][class*="price"]',
            'span[data-testid="price-original"]'
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
        
        # Look for sale price
        sale_selectors = [
            '[class*="sale"][class*="price"]',
            '.sale-price',
            '[data-testid="price-current"]',
            '.price-current'
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

def extract_size_and_fit(soup, driver=None):
    """Extract size and fit information including all available sizes"""
    try:
        size_fit_info = []
        
        # Try multiple approaches to click on size selector and get all sizes
        if driver:
            try:
                # Wait a bit for page to fully load
                time.sleep(2)
                
                # Try different selectors for the size dropdown
                size_selectors = [
                    '[data-component="SizeSelectorLabel"]',
                    '[role="combobox"]',
                    '.size-selector',
                    '[aria-haspopup="listbox"]'
                ]
                
                clicked = False
                for selector in size_selectors:
                    try:
                        size_selector = driver.find_element(By.CSS_SELECTOR, selector)
                        if size_selector and size_selector.is_displayed():
                            # Scroll element into view
                            driver.execute_script("arguments[0].scrollIntoView(true);", size_selector)
                            time.sleep(1)
                            
                            # Try clicking
                            driver.execute_script("arguments[0].click();", size_selector)
                            time.sleep(2)  # Wait longer for dropdown to open
                            clicked = True
                            print(f"[DEBUG] Successfully clicked size selector: {selector}")
                            break
                    except Exception as e:
                        print(f"[DEBUG] Failed to click selector {selector}: {e}")
                        continue
                
                if clicked:
                    # Now look for size options with more comprehensive selectors
                    size_option_selectors = [
                        '[role="option"]',
                        '[data-component="SizeOption"]',
                        '.size-option',
                        'li[role="option"]',
                        '[data-testid*="size-option"]',
                        '.size-dropdown li',
                        '.size-list li'
                    ]
                    
                    sizes = set()  # Use set to avoid duplicates
                    for option_selector in size_option_selectors:
                        try:
                            size_options = driver.find_elements(By.CSS_SELECTOR, option_selector)
                            for option in size_options:
                                if option.is_displayed():
                                    size_text = option.text.strip()
                                    if size_text and len(size_text) <= 15 and size_text not in ['Select size', 'Size guide']:
                                        sizes.add(size_text)
                                        print(f"[DEBUG] Found size: {size_text}")
                        except Exception as e:
                            print(f"[DEBUG] Error with selector {option_selector}: {e}")
                            continue
                    
                    if sizes:
                        size_fit_info.append(f"Available Sizes: {', '.join(sorted(sizes))}")
                        print(f"[DEBUG] Total sizes found: {len(sizes)}")
                    
                    # Close dropdown by pressing escape or clicking elsewhere
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        driver.execute_script("document.body.click();")
                        time.sleep(1)
                
            except Exception as e:
                print(f"[INFO] Could not interact with size selector: {e}")
        
        # Fallback: Extract sizes from static HTML if interaction failed
        if not any('Available Sizes:' in info for info in size_fit_info):
            print("[DEBUG] Trying fallback size extraction from HTML")
            
            # Look for size elements in the static HTML
            size_selectors = [
                '[data-testid*="size"]',
                '[class*="size"]',
                '.size-option',
                'button[class*="size"]',
                '.size-selector',
                '[role="option"]',
                '[data-component*="Size"]',
                'option[value*="size"]'
            ]
            
            sizes = set()
            for selector in size_selectors:
                try:
                    size_elements = soup.select(selector)
                    for elem in size_elements:
                        size_text = elem.get_text(strip=True)
                        if (size_text and 
                            len(size_text) <= 15 and 
                            size_text not in ['Select size', 'Size guide', 'Size & Fit'] and
                            not size_text.startswith('AED')):
                            sizes.add(size_text)
                except:
                    continue
            
            if sizes:
                size_fit_info.append(f"Available Sizes: {', '.join(sorted(sizes))}")        
        # Look for fit information (keep existing fit guide logic)
        fit_selectors = [
            '[class*="fit"]',
            '[class*="measurement"]',
            '.fit-guide',
            '.size-guide',
            '.measurement-info'
        ]
        
        fit_info = []
        for selector in fit_selectors:
            try:
                fit_elements = soup.select(selector)
                for elem in fit_elements:
                    fit_text = elem.get_text(strip=True)
                    if (fit_text and 
                        len(fit_text) > 10 and 
                        'model' not in fit_text.lower() and
                        'cotton' not in fit_text.lower() and
                        'elastane' not in fit_text.lower()):
                        fit_info.append(fit_text)
            except:
                continue
        
        if fit_info:
            size_fit_info.append(f"Fit Guide: {' | '.join(fit_info)}")
        
        # Look for Size & Fit accordion section
        for section in soup.find_all('section', {'data-component': 'AccordionItem'}):
            btn = section.find('p', string='Size & Fit')
            if btn:
                panel = section.find('div', {'data-component': 'AccordionPanel'})
                if panel:
                    panel_text = ' '.join(panel.stripped_strings)
                    if panel_text:
                        if "couldn't find fitting details" in panel_text.lower():
                            size_fit_info.append("Size & Fit: No fitting details available")
                        else:
                            # Filter out composition info from accordion content
                            if not any(word in panel_text.lower() for word in ['cotton', 'elastane', 'polyester', 'silk', 'wool']):
                                size_fit_info.append(f"Size & Fit Details: {panel_text}")
                break
        
        return ' | '.join(size_fit_info) if size_fit_info else ''
        
    except Exception as e:
        print(f"[Warning] Error extracting size/fit: {e}")
        return ''

def collect_product_links(driver, category_url, max_products=None):
    """Collect product links from Farfetch category page"""
    print(f"\n[*] Collecting product links from: {category_url}")
    
    try:
        driver.get(category_url)
        print("[*] Category page loaded successfully")
        
        # Wait for products to load
        time.sleep(random.uniform(3, 6))
        
        # Scroll to load more products - increased for comprehensive scraping
        scroll_attempts = 20 if max_products is None else 8  # More scrolls when no limit
        for _ in range(scroll_attempts):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(random.uniform(2, 4))
            
            # Try to click "Load More" button if it exists
            try:
                load_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Load More') or contains(text(), 'Show More')]")
                if load_more_button.is_displayed():
                    load_more_button.click()
                    print("[+] Clicked 'Load More' button")
                    time.sleep(random.uniform(3, 5))
            except:
                pass
        
        # Find product links - only actual product pages
        product_links = []
        
        # Get all links on the page
        all_links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in all_links:
            try:
                href = link.get_attribute('href')
                if href:
                    # Only include URLs that are actual product pages
                    # Product URLs contain '-item-' followed by a numeric ID
                    if ('-item-' in href and 
                        re.search(r'-item-\d+\.aspx', href) and
                        '/shopping/' in href and
                        href not in product_links):
                        
                        product_links.append(href)
                        print(f"[+] Found product: {href.split('/')[-1]}")
                        
                        # Only break if we have a limit and reached it
                        if max_products is not None and len(product_links) >= max_products:
                            break
            except:
                pass
        
        print(f"[✓] Found {len(product_links)} actual product links")
        return product_links
        
    except Exception as e:
        print(f"[Error] Failed to collect links: {e}")
        return []

def extract_price_for_region(soup, region_name):
    """Extract price information for a specific region"""
    try:
        price_info = {
            'region': region_name,
            'currency': '',
            'price': '',
            'original_price': '',
            'sale_price': '',
            'discount': ''
        }
        
        # Extract current price
        price_elem = soup.select_one('p[data-component="PriceFinalLarge"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_info['price'] = price_text
            
            currency_match = re.search(r'([A-Z]{3}|£|$|€)', price_text)
            if currency_match:
                price_info['currency'] = currency_match.group(1)
        
        # Extract original price if on sale
        original_elem = soup.select_one('p[data-component="PriceOriginal"]')
        if original_elem:
            price_info['original_price'] = original_elem.get_text(strip=True)
            
            # Calculate discount
            try:
                current_num = float(re.search(r'[\d,]+\.?\d*', price_info['price'].replace(',', '')).group())
                original_num = float(re.search(r'[\d,]+\.?\d*', price_info['original_price'].replace(',', '')).group())
                if original_num > current_num:
                    discount = ((original_num - current_num) / original_num) * 100
                    price_info['discount'] = f"{discount:.0f}%"
                    price_info['sale_price'] = price_info['price']
            except:
                pass
        
        return price_info
        
    except Exception as e:
        print(f"[Warning] Error extracting price for {region_name}: {e}")
        return price_info

# Modify the extract_product_details function to use multi-region pricing
def extract_product_details(driver, url):
    """Extract product details from UAE first, then get prices from other regions"""
    try:
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

        # 1. Get UAE details first
        print("[*] Getting full product details from UAE...")
        driver.get(url)
        time.sleep(random.uniform(4, 6))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Extract basic info
        brand_elem = soup.select_one('h1.ltr-i980jo.el610qn0 a')
        product_data['brand'] = brand_elem.get_text(strip=True) if brand_elem else ''

        name_elem = soup.select_one('p[data-testid="product-short-description"]')
        product_data['product_name'] = name_elem.get_text(strip=True) if name_elem else ''

        # Get UAE price info - Updated selectors and logic
        price_aed = None
        original_price = None
        current_price = None

        price_wrapper = soup.select_one('div[data-component="BasePriceWrapper"]')
        if price_wrapper:
            # Extract original price from PriceOriginal
            original_elem = price_wrapper.select_one('p[data-component="PriceOriginal"]')
            if original_elem:
                orig_text = original_elem.get_text(strip=True)
                match = re.search(r'\d[\d,]*\.?\d*', orig_text.replace(',', ''))
                if match:
                    original_price = float(match.group())
            
            # Current/Sale price
            current_elem = price_wrapper.select_one('p[data-component="PriceFinalLarge"]')
            if current_elem:
                current_text = current_elem.get_text(strip=True)
                match = re.search(r'\d[\d,]*\.?\d*', current_text.replace(',', ''))
                if match:
                    current_price = float(match.group())
                    price_aed = current_price  # Use current price as AED price
        else:
            # Fallback to the old method
            price_elem = soup.select_one('p[data-component="PriceFinalLarge"]')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                match = re.search(r'\d[\d,]*\.?\d*', price_text.replace(',', ''))
                if match:
                    price_aed = float(match.group())
                    current_price = price_aed

        if current_price:
            product_data['sale_price'] = f"AED {current_price:,.2f}"
            
            if original_price and original_price > current_price:
                # Product is on sale
                product_data['original_price'] = f"AED {original_price:,.2f}"
                discount_percent = ((original_price - current_price) / original_price) * 100
                product_data['discount'] = f"{discount_percent:.0f}%"
                print(f"[DEBUG] Sale detected: Original {original_price} -> Sale {current_price} ({discount_percent:.0f}% off)")
            else:
                # Product is not on sale, original price is the same as current
                product_data['original_price'] = f"AED {current_price:,.2f}"
                product_data['discount'] = ''
        else:
            product_data['sale_price'] = ''
            product_data['original_price'] = ''
            product_data['discount'] = ''

        breadcrumb = ''
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'BreadcrumbList':
                    items = data['itemListElement']
                    breadcrumb = ' > '.join([i['item']['name'] for i in items if 'Home' not in i['item']['name']])
                    break
            except Exception:
                continue
        product_data['category'] = breadcrumb

# Product Details (all text under product-information-accordion)
        details_elem = soup.find('div', {'data-testid': 'product-information-accordion'})
        details = []
        if details_elem:
            # Get all text from the accordion, including collapsed sections
            for text in details_elem.stripped_strings:
                if text and len(text.strip()) > 2:  # Filter out very short text
                    details.append(text.strip())
        product_data['product_details'] = ' | '.join(details) if details else 'No details available'


        # Get images with high resolution
        image_urls = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            src = re.sub(r'w=\d+', 'w=1200', src)
            if src not in image_urls:
                image_urls.append(src)
        product_data['image_urls'] = ', '.join(image_urls)

        # Get size and fit
        product_data['size_and_fit'] = extract_size_and_fit(soup, driver)

        # 2. Get prices from other regions
        regions = {
            'us': {'code': 'us', 'key': 'price_usd'},
            'uk': {'code': 'uk', 'key': 'price_gbp'},
            'de': {'code': 'de', 'key': 'price_eur'}
        }

        for region, info in regions.items():
            region_url = url.replace('/ae/', f'/{info["code"]}/')
            print(f"[*] Getting price from {region.upper()}...")
            
            try:
                driver.get(region_url)
                time.sleep(random.uniform(3, 5))
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                price_elem = soup.select_one('p[data-component="PriceFinalLarge"]')
                if price_elem:
                    product_data[info['key']] = price_elem.get_text(strip=True)
                    print(f"[✓] {region.upper()}: {product_data[info['key']]}")
            except Exception as e:
                print(f"[!] Failed to get {region.upper()} price: {e}")

            if region != list(regions.keys())[-1]:
                time.sleep(random.uniform(2, 4))

        return product_data

    except Exception as e:
        print(f"[Error] Failed to extract product details: {e}")
        return None
    
import os
import re
import requests
import time
import random

def download_product_images(product_data, download_images_flag=True):
    if not download_images_flag or not product_data.get('image_urls') or not product_data.get('product_name'):
        return

    try:
        # Root folder is the Railway-mounted volume
        base_image_dir = "/app/data/product_images"

        # Sanitize product folder name
        folder_name = re.sub(r'[^\w\s-]', '', product_data['product_name'])[:50]
        folder_name = re.sub(r'\s+', '_', folder_name)
        if not folder_name.strip('_'):
            folder_name = f"product_{hash(product_data['product_url']) % 10000}"

        # Full path: /app/data/product_images/FolderName
        product_folder = os.path.join(base_image_dir, folder_name)
        os.makedirs(product_folder, exist_ok=True)

        image_urls = product_data['image_urls'].split(', ')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        }

        print(f"[*] Downloading images to: {product_folder}")
        for i, img_url in enumerate(image_urls[:8], 1):
            try:
                response = requests.get(img_url, timeout=15, headers=headers)
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

                    safe_name = re.sub(r'[^\w\s-]', '', product_data['product_name'])[:30]
                    safe_name = re.sub(r'\s+', '_', safe_name)
                    filename = f"{safe_name}_pic_{i}{ext}"
                    filepath = os.path.join(product_folder, filename)

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    print(f"[✓] Downloaded: {filename}")
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
    csv_filename = 'farfetch_products.csv'
    if os.path.exists(csv_filename):
        try:
            df = pd.read_csv(csv_filename, encoding='utf-8-sig')
            existing_products = df.to_dict('records')
            existing_urls = set(product['product_url'] for product in existing_products if 'product_url' in product)
            print(f"[*] Loaded {len(existing_products)} existing products from {csv_filename}")
        except Exception as e:
            print(f"[Warning] Could not load existing CSV: {e}")
    
    # Try to load existing JSON file as backup
    json_filename = 'farfetch_products.json'
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
    """Save data by appending to existing files in /app/data (Railway volume)"""
    
    # Volume base directory
    output_dir = "/app/data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create DataFrame for new products only
    new_df = pd.DataFrame(all_products)
    
    # Set file paths inside volume
    csv_filename = os.path.join(output_dir, 'farfetch_products.csv')
    json_filename = os.path.join(output_dir, 'farfetch_products.json')
    
    # Try to append to existing CSV
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if existing_products and os.path.exists(csv_filename) and os.path.getsize(csv_filename) > 0:
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
                backup_csv = os.path.join(output_dir, f'farfetch_products_{timestamp}.csv')
                if existing_products:
                    existing_df = pd.read_csv(csv_filename, encoding='utf-8-sig')
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    combined_df.to_csv(backup_csv, index=False, encoding='utf-8-sig')
                else:
                    new_df.to_csv(backup_csv, index=False, encoding='utf-8-sig')
                print(f"[⚠] Could not save to {csv_filename} after {max_retries} attempts")
                print(f"[💾] Saved to backup file: {backup_csv}")
                print(f"[💡] Please close any open Excel files and manually rename {backup_csv} to {csv_filename}")
                csv_filename = backup_csv
    
    # Save JSON (combine existing + new)
    combined_products = existing_products + all_products
    for attempt in range(max_retries):
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(combined_products, f, indent=2, ensure_ascii=False)
            print(f"[✅] Successfully saved to {json_filename}")
            break
        except PermissionError:
            if attempt < max_retries - 1:
                print(f"[⏳] Permission denied, retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_json = os.path.join(output_dir, f'farfetch_products_{timestamp}.json')
                with open(backup_json, 'w', encoding='utf-8') as f:
                    json.dump(combined_products, f, indent=2, ensure_ascii=False)
                print(f"[⚠] Could not save to {json_filename} after {max_retries} attempts")
                print(f"[💾] Saved to backup file: {backup_json}")
                json_filename = backup_json
    
    return csv_filename, json_filename, len(combined_products)

def main():
    """Main scraping function with enhanced error handling and data display"""
    # Constants
    MAX_PRODUCTS_PER_CATEGORY = None  
    DOWNLOAD_IMAGES = True
    
    categories = {
        'Women Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/women/clothing-1/items.aspx',
            'path': 'Women > Clothing'
        },
        'Women Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/women/shoes-1/items.aspx',
            'path': 'Women > Shoes'
        },
        'Women Bags': {
            'url': 'https://www.farfetch.com/ae/shopping/women/bags-purses-1/items.aspx',
            'path': 'Women > Bags & Purses'
        },
        'Women Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/women/accessories-all-1/items.aspx',
            'path': 'Women > Accessories'
        },
        'Women Jewellery': {
            'url': 'https://www.farfetch.com/ae/shopping/women/jewellery-1/items.aspx',
            'path': 'Women > Jewellery'
        },
        'Women Lifestyle': {
            'url': 'https://www.farfetch.com/ae/shopping/women/lifestyle-1/items.aspx',
            'path': 'Women > Lifestyle'
        },
        'Women Pre-owned': {
            'url': 'https://www.farfetch.com/ae/shopping/women/pre-owned-1/items.aspx',
            'path': 'Women > Pre-owned'
        },
        'Men Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/men/clothing-2/items.aspx',
            'path': 'Men > Clothing'
        },
        'Men Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/men/shoes-2/items.aspx',
            'path': 'Men > Shoes'
        },
        'Men Bags': {
            'url': 'https://www.farfetch.com/ae/shopping/men/bags-purses-2/items.aspx',
            'path': 'Men > Bags & Purses'
        },
        'Men Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/men/accessories-all-2/items.aspx',
            'path': 'Men > Accessories'
        },
        'Men Watches': {
            'url': 'https://www.farfetch.com/ae/shopping/men/watches-4/items.aspx',
            'path': 'Men > Watches'
        },
        'Men Lifestyle': {
            'url': 'https://www.farfetch.com/ae/shopping/men/lifestyle-2/items.aspx',
            'path': 'Men > Lifestyle'
        },
        'Baby Girls Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-girl-accessories-6/items.aspx',
            'path': 'Baby Girls > Accessories'
        },
        'Baby Girls Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-girl-shoes-6/items.aspx',
            'path': 'Baby Girls > Shoes'
        },
        'Baby Girls Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-girl-clothing-6/items.aspx',
            'path': 'Baby Girls > Clothing'
        },
        'Baby Boys Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-boy-accessories-5/items.aspx',
            'path': 'Baby Boys > Accessories'
        },
        'Baby Boys Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-boy-shoes-5/items.aspx',
            'path': 'Baby Boys > Shoes'
        },
        'Baby Boys Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-boy-clothing-5/items.aspx',
            'path': 'Baby Boys > Clothing'
        },
        'Baby Nursery': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/baby-nursery-5/items.aspx',
            'path': 'Baby > Nursery'
        },
        'Kids Girls Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/girls-accessories-1/items.aspx',
            'path': 'Kids Girls > Accessories'
        },
        'Kids Girls Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/girls-shoes-4/items.aspx',
            'path': 'Kids Girls > Shoes'
        },
        'Kids Girls Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/girls-clothing-4/items.aspx',
            'path': 'Kids Girls > Clothing'
        },
        'Kids Boys Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/boys-accessories-3/items.aspx',
            'path': 'Kids Boys > Accessories'
        },
        'Kids Boys Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/boys-shoes-3/items.aspx',
            'path': 'Kids Boys > Shoes'
        },
        'Kids Boys Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/boys-clothing-3/items.aspx',
            'path': 'Kids Boys > Clothing'
        },
        'Teen Girls Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-girl-accessories-7/items.aspx',
            'path': 'Teen Girls > Accessories'
        },
        'Teen Girls Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-girl-shoes-1/items.aspx',
            'path': 'Teen Girls > Shoes'
        },
        'Teen Girls Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-girl-clothing-7/items.aspx',
            'path': 'Teen Girls > Clothing'
        },
        'Teen Boys Accessories': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-boy-accessories-8/items.aspx',
            'path': 'Teen Boys > Accessories'
        },
        'Teen Boys Shoes': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-boy-shoes-1/items.aspx',
            'path': 'Teen Boys > Shoes'
        },
        'Teen Boys Clothing': {
            'url': 'https://www.farfetch.com/ae/shopping/kids/teen-boy-clothing-8/items.aspx',
            'path': 'Teen Boys > Clothing'
        },
    }
    
    
    try:
        print("=" * 80)
        print("🛍️  FARFETCH COMPREHENSIVE SCRAPER")
        print("=" * 80)
        print(f"[*] Products per category: {MAX_PRODUCTS_PER_CATEGORY}")
        print(f"[*] Download images: {'Yes' if DOWNLOAD_IMAGES else 'No'}")
        
        # Load existing data to prevent duplicates
        existing_products, existing_urls = load_existing_data()
        print(f"[*] Found {len(existing_urls)} existing product URLs to skip")
        
        # Setup driver
        driver = setup_driver()
        if not driver:
            print("[❌] Failed to initialize browser driver")
            return
        
        all_products = []
        skipped_duplicates = 0
        
        # Main scraping loop
        for category_name, category_info in categories.items():
            try:
                print(f"\n{'='*50}")
                print(f"📂 SCRAPING {category_name.upper()} CATEGORY")
                print(f"{'='*50}")
                
                # Collect and filter product links
                product_links = collect_product_links(driver, category_info['url'], MAX_PRODUCTS_PER_CATEGORY)
                if not product_links:
                    print(f"[⚠] No products found in {category_name} category")
                    continue
                
                new_product_links = [url for url in product_links if url not in existing_urls]
                skipped_in_category = len(product_links) - len(new_product_links)
                skipped_duplicates += skipped_in_category
                
                if not new_product_links:
                    print(f"[ℹ️] All products in {category_name} already scraped")
                    continue
                
                # Process each product
                for i, url in enumerate(new_product_links, 1):
                    try:
                        print(f"\n[*] Processing product {i}/{len(new_product_links)}")
                        product_data = extract_product_details(driver, url)
                        
                        if product_data and isinstance(product_data, dict):
                            # Convert single dict to list for consistency
                            all_products.append(product_data)  # Use append instead of extend
                            print(f"[✅] Successfully scraped product")
                            
                            if DOWNLOAD_IMAGES and product_data.get('image_urls'):
                                try:
                                    download_product_images(product_data, True)
                                except Exception as img_error:
                                    print(f"[⚠] Error downloading images: {str(img_error)}")
                        else:
                            print(f"[⚠] No valid product data returned")
                        
                        # Random delay between products
                        if i < len(new_product_links):
                            delay = random.uniform(8, 15)
                            print(f"[💤] Waiting {delay:.1f}s...")
                            time.sleep(delay)
                            
                    except Exception as e:
                        print(f"[❌] Error processing product: {str(e)}")
                        continue       
                # Random delay between categories
                if category_name != list(categories.keys())[-1]:
                    delay = random.uniform(10, 20)
                    print(f"[💤] Waiting {delay:.1f}s before next category...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"[❌] Error processing category {category_name}: {str(e)}")
                continue
                
    except KeyboardInterrupt:
        print("\n[⚠] Scraping interrupted by user")
    except Exception as e:
        print(f"\n[❌] Unexpected error: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
    finally:
        try:
            driver.quit()
            print("\n[✅] Browser closed successfully")
        except:
            print("\n[⚠] Browser was already closed")
    
    # Save and display results
    if all_products:
        try:
            csv_filename, json_filename, total_products = save_data_with_append(all_products, existing_products)
            
            # Display results summary
            print("\n" + "=" * 60)
            print("📊 FINAL SCRAPING RESULTS")
            print("=" * 60)
            print(f"🆕 New products scraped: {len(all_products)}")
            print(f"⏭️ Duplicates skipped: {skipped_duplicates}")
            print(f"📈 Total in database: {total_products}")
            print(f"💾 Files saved: {csv_filename}, {json_filename}")
            
            if DOWNLOAD_IMAGES:
                print(f"🖼️ Images saved to: /app/data/product_images/")
                print(f"📁 CSV/JSON saved in: /app/data/")
            
            # Group and display sample data
            print("\n📋 Sample of scraped data:")
            try:
                products_by_name = defaultdict(list)
                
                # Group products by name
                for product in all_products:
                    if isinstance(product, dict):
                        name = product.get('product_name', 'Unknown')
                        products_by_name[name].append(product)
                
                # Show products with multiple regions first
                multi_region = {name: data for name, data in products_by_name.items() 
                              if len(data) > 1}
                
                if multi_region:
                    print("\n🌍 Products with multiple regional prices:")
                    for idx, (name, variants) in enumerate(list(multi_region.items())[:3]):
                        print(f"\n{idx + 1}. {name[:45]}...")
                        for variant in variants:
                            region = variant.get('region', 'Unknown')
                            price = variant.get('price_local', 'N/A')
                            print(f"   {region}: {price}")
                else:
                    print("\n💰 Sample product prices:")
                    for idx, product in enumerate(all_products[:5]):
                        if isinstance(product, dict):
                            name = product.get('product_name', 'N/A')
                            price = product.get('price_local', 'N/A')
                            region = product.get('region', 'N/A')
                            print(f"{idx + 1}. {name[:40]}... ({region}: {price})")
                            
            except Exception as e:
                print(f"[⚠] Error displaying results: {str(e)}")
                
            print("\n🎉 Scraping completed successfully!")
            
        except Exception as e:
            print(f"\n[❌] Error saving/displaying results: {str(e)}")
            print(f"[DEBUG] Error traceback: {traceback.format_exc()}")
    else:
        print("\n[ℹ️] No new products were scraped")

if __name__ == "__main__":
    main()
