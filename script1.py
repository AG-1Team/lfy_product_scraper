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
import random
import time
import traceback
import base64
import requests

def setup_driver():
    """Setup undetected Chrome driver with maximum stealth"""
    try:
        print("[*] Setting up undetected Chrome driver...")
        options = uc.ChromeOptions()

        # ✅ Specify binary location explicitly (for Docker/Headless)
        options.binary_location = "/usr/bin/google-chrome"

        # --- User-Agent ---
        realistic_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        user_agent = random.choice(realistic_agents)
        print(f"[*] Using User-Agent: {user_agent}")

        # --- Chrome Flags ---
        chrome_flags = [
            "--headless=new",  # modern headless
            f"--user-agent={user_agent}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-sync",
            "--disable-translate",
            "--mute-audio",
            "--hide-scrollbars",
            "--disable-background-networking",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-infobars",
            "--disable-ipc-flooding-protection",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees"
        ]
        for flag in chrome_flags:
            options.add_argument(flag)

        # --- Randomize window size and position ---
        common_resolutions = [(1920, 1080), (1366, 768), (1536, 864)]
        width, height = random.choice(common_resolutions)
        options.add_argument(f"--window-size={width},{height}")
        options.add_argument(f"--window-position={random.randint(0,100)},{random.randint(0,100)}")

        # --- Language & Timezone ---
        lang = random.choice(["en-US,en", "en-GB,en", "en-CA,en"])
        options.add_argument(f"--accept-lang={lang}")
        timezone = random.choice(["Asia/Dubai", "Asia/Riyadh", "Asia/Kuwait"])
        options.add_argument(f"--timezone={timezone}")

        # --- Chrome Preferences ---
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
                "geolocation": 2
            },
            "profile.managed_default_content_settings.images": 1,
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        }
        options.add_experimental_option("prefs", prefs)

        # --- Initialize Chrome Driver ---
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)
        driver.implicitly_wait(10)

        # --- Stealth JavaScript ---
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
        if (window.chrome) {
            Object.defineProperty(window.chrome, 'runtime', {get: () => undefined});
        }
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """

        try:
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
                'platform': random.choice(['Win32', 'Linux x86_64', 'MacIntel'])
            })
        except Exception as js_err:
            print(f"[!] Stealth script injection failed: {js_err}")

        print("[✅] Undetected driver setup complete")
        return driver

    except Exception as e:
        print(f"[❌] Failed to setup undetected driver:\n{traceback.format_exc()}")
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

def extract_size_and_fit(soup):
    """Extract size and fit information including model measurements"""
    try:
        size_fit_info = []
        
        # Look for model measurements table
        model_measurements = soup.find('div', {'class': 'ltr-92qs1a'})
        if model_measurements:
            # Extract model measurements
            measurements = []
            
            # Find the measurements table
            table = model_measurements.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        property_name = cells[0].get_text(strip=True)
                        property_value = cells[1].get_text(strip=True)
                        measurements.append(f"{property_name}: {property_value}")
            
            # Extract model description
            model_desc = model_measurements.find('p', {'data-component': 'Body'})
            if model_desc:
                desc_text = model_desc.get_text(strip=True)
                if desc_text:
                    measurements.append(f"Model Info: {desc_text}")
            
            if measurements:
                size_fit_info.append(f"Model Measurements: {' | '.join(measurements)}")
        
        # Look for size elements
        size_selectors = [
            '[data-testid*="size"]',
            '[class*="size"]',
            '.size-option',
            'button[class*="size"]',
            '.size-selector'
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
        
        # Look for fit information
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
                    if fit_text and len(fit_text) > 10 and 'model' not in fit_text.lower():
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
        time.sleep(random.uniform(4, 8))
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("[Warning] Page load timeout")
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(random.uniform(2, 4))
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Brand
        brand_elem = soup.select_one('h1.ltr-i980jo.el610qn0 a')
        product_data['brand'] = brand_elem.get_text(strip=True) if brand_elem else ''

        # Product Name
        name_elem = soup.select_one('p[data-testid="product-short-description"]')
        product_data['product_name'] = name_elem.get_text(strip=True) if name_elem else ''

        # Price AED - Updated to handle BasePriceWrapper structure
        price_aed = None
        original_price = None
        current_price = None
        
        # First try to find the BasePriceWrapper div
        price_wrapper = soup.select_one('div[data-component="BasePriceWrapper"]')
        if price_wrapper:
            # Extract original price from PriceOriginal
            original_elem = price_wrapper.select_one('p[data-component="PriceOriginal"]')
            if original_elem:
                orig_text = original_elem.get_text(strip=True)
                match = re.search(r'\d[\d,]*\.?\d*', orig_text.replace(',', ''))
                if match:
                    original_price = float(match.group())
            
            # Extract current/sale price from PriceFinalLarge
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
        
        # Set the currency prices
        product_data['price_aed'] = f"AED {price_aed:,.2f}" if price_aed else ''
        product_data['price_usd'] = f"USD {price_aed * 0.27:.2f}" if price_aed else ''
        product_data['price_gbp'] = f"GBP {price_aed * 0.21:.2f}" if price_aed else ''
        product_data['price_eur'] = f"EUR {price_aed * 0.25:.2f}" if price_aed else ''

        # Sale/Original/Discount - Updated logic
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

        # Breadcrumb category from ld+json
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

        # Size & Fit - Use enhanced extraction function
        product_data['size_and_fit'] = extract_size_and_fit(soup)

        # Image URLs (high-res)
        image_urls = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            src = re.sub(r'w=\d+', 'w=1200', src)
            if src not in image_urls:
                image_urls.append(src)
        product_data['image_urls'] = ', '.join(image_urls)

        return product_data
    except Exception as e:
        print(f"[Error] Failed to scrape {url}: {e}")
        return product_data

def download_product_images(product_data, download_images_flag=True):
    if not download_images_flag or not product_data['image_urls'] or not product_data['product_name']:
        return
    try:
        folder_name = re.sub(r'[^\w\s-]', '', product_data['product_name'])[:50]
        folder_name = re.sub(r'\s+', '_', folder_name)
        if not folder_name.strip('_'):
            folder_name = f"product_{hash(product_data['product_url']) % 10000}"
        product_folder = os.path.join('product_images', folder_name)
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
                    filename = f"{safe_name} pic {i}{ext}"
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
    """Save data by appending to existing files"""
    # Create DataFrame for new products only
    new_df = pd.DataFrame(all_products)
    
    # CSV filename
    csv_filename = 'farfetch_products.csv'
    json_filename = 'farfetch_products.json'
    
    # Try to append to existing CSV
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if existing_products:
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
                backup_csv = f'farfetch_products_{timestamp}.csv'
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
                backup_json = f'farfetch_products_{timestamp}.json'
                with open(backup_json, 'w', encoding='utf-8') as f:
                    json.dump(combined_products, f, indent=2, ensure_ascii=False)
                print(f"[⚠] Could not save to {json_filename} after {max_retries} attempts")
                print(f"[💾] Saved to backup file: {backup_json}")
                json_filename = backup_json
    
    return csv_filename, json_filename, len(combined_products)
    
def upload_to_github(file_path, repo, token, path_in_repo, commit_msg="Upload scraped data"):
    """Uploads a local file to a GitHub repository."""
    with open(file_path, "rb") as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode('utf-8')
    api_url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"

    headers = {"Authorization": f"token {token}"}
    payload = {
        "message": commit_msg,
        "content": content_b64,
        "branch": "main"
    }

    # Check if file exists to get SHA (needed for updates)
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200 and 'sha' in response.json():
        payload["sha"] = response.json()['sha']

    put_response = requests.put(api_url, headers=headers, json=payload)

    if put_response.status_code in [200, 201]:
        print(f"[📤] Uploaded {file_path} to GitHub at {path_in_repo}")
    else:
        print(f"[❌] Failed to upload {file_path}: {put_response.text}")


def main():
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
    
    try:
        for category_name, category_info in categories.items():
            print(f"\n{'='*50}")
            print(f"📂 SCRAPING {category_name.upper()} CATEGORY")
            print(f"{'='*50}")
            
            # Collect product links - no limit when MAX_PRODUCTS_PER_CATEGORY is None
            product_links = collect_product_links(driver, category_info['url'], MAX_PRODUCTS_PER_CATEGORY)
            
            if not product_links:
                print(f"[⚠] No products found in {category_name} category")
                continue
            
            print(f"[✅] Found {len(product_links)} products in {category_name}")
            
            # Filter out already scraped URLs
            new_product_links = [url for url in product_links if url not in existing_urls]
            skipped_in_category = len(product_links) - len(new_product_links)
            
            if skipped_in_category > 0:
                print(f"[⏭️] Skipping {skipped_in_category} already scraped products")
                skipped_duplicates += skipped_in_category
            
            if not new_product_links:
                print(f"[ℹ️] All products in {category_name} already scraped, skipping")
                continue
            
            print(f"[🆕] Scraping {len(new_product_links)} new products")
            
            # Scrape each new product
            for i, url in enumerate(new_product_links, 1):
                print(f"\n[*] Processing {category_name} product {i}/{len(new_product_links)}")
                
                product_data = extract_product_details(driver, url)
                
                if product_data['product_name'] or product_data['brand']:
                    all_products.append(product_data)
                    
                    # Download images
                    if DOWNLOAD_IMAGES:
                        download_product_images(product_data, True)
                    
                    print(f"[✅] Successfully scraped product {i}")
                else:
                    print(f"[⚠] Failed to extract data for product {i}")
                
                # Delay between products
                if i < len(new_product_links):
                    delay = random.uniform(8, 15)
                    print(f"[💤] Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
            
            # Delay between categories
            if category_name != list(categories.keys())[-1]:
                delay = random.uniform(10, 20)
                print(f"[💤] Waiting {delay:.1f} seconds before next category...")
                time.sleep(delay)
    
    except KeyboardInterrupt:
        print("\n[⚠] Scraping interrupted by user")
    except Exception as e:
        print(f"\n[❌] Unexpected error: {e}")
    finally:
        driver.quit()
        print("\n[✅] Browser closed successfully")
    
    # Save results with append functionality
    if all_products:
        csv_filename, json_filename, total_products = save_data_with_append(all_products, existing_products)
        
        GITHUB_REPO = "os959345/webscrapper"
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # ✅ correct usage
        
        upload_to_github(csv_filename, GITHUB_REPO, GITHUB_TOKEN, f"data/{csv_filename}")
        upload_to_github(json_filename, GITHUB_REPO, GITHUB_TOKEN, f"data/{json_filename}")

        print("\n" + "=" * 60)
        print("📊 FINAL SCRAPING RESULTS")
        print("=" * 60)
        print(f"🆕 New products scraped: {len(all_products)}")
        print(f"⏭️ Duplicates skipped: {skipped_duplicates}")
        print(f"📈 Total products in database: {total_products}")
        print(f"💾 CSV file: {csv_filename}")
        print(f"💾 JSON file: {json_filename}")
        
        if DOWNLOAD_IMAGES:
            print(f"🖼️ Images saved to: ./product_images/ folders")
        
        # Show sample of new data
        if all_products:
            print(f"\n📋 Sample of newly scraped data:")
            sample = all_products[0]
            print(f"   Brand: {sample['brand']}")
            print(f"   Product: {sample['product_name'][:40]}...")
            print(f"   Category: {sample['category']}")
            print(f"   Price AED: {sample['price_aed']}")
            print(f"   Price USD: {sample['price_usd']}")
            print(f"   Images: {len(sample['image_urls'].split(', ')) if sample['image_urls'] else 0}")
        
        print("\n🎉 Scraping completed successfully!")
        
    else:
        print("\n[ℹ️] No new products were scraped (all were duplicates or failed)")

if __name__ == "__main__":
    main()
