from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import time
import random
import os
import re
import json
from selenium.webdriver.common.keys import Keys

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
