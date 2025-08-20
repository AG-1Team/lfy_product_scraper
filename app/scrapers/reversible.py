import time
import random
import json
import csv
import re
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import logging


class ReversibleScraper:
    def __init__(self, headless=False, wait_time=10):
        """Initialize the scraper with undetected Chrome driver"""
        self.setup_logging()
        self.wait_time = wait_time
        self.data_list = []

        # Initialize undetected Chrome driver
        options = uc.ChromeOptions()

        # User agent rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")

        options.binary_location = "/usr/local/bin/google-chrome"

        # Initialize undetected Chrome
        self.driver = uc.Chrome(
            headless=headless, options=options, use_subprocess=False, version_main=130)

        # Execute script to remove webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.wait = WebDriverWait(self.driver, wait_time)

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('reversible_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def random_delay(self, min_delay=1, max_delay=3):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def scroll_randomly(self):
        """Randomly scroll the page to mimic human behavior"""
        scroll_height = self.driver.execute_script(
            "return document.body.scrollHeight")
        random_position = random.randint(0, scroll_height)
        self.driver.execute_script(f"window.scrollTo(0, {random_position})")
        self.random_delay(1, 2)

    def wait_for_page_load(self):
        """Wait for the page to fully load"""
        try:
            # Wait for the main product container to load
            main_selectors = [
                '.card_price_value__JS1Ao',
                '.product_name__AYH0V',
                '.brand-display_designer__SQx5q'
            ]

            for selector in main_selectors:
                try:
                    element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, selector))
                    )
                    if element:
                        self.logger.info(
                            f"Page loaded - found element: {selector}")
                        return True
                except TimeoutException:
                    continue

            self.logger.warning("Page load timeout - proceeding anyway")
            return False

        except Exception as e:
            self.logger.error(f"Error waiting for page load: {str(e)}")
            return False

    def safe_find_element(self, selector, by=By.CSS_SELECTOR):
        """Safely find element with error handling"""
        try:
            element = self.wait.until(
                EC.presence_of_element_located((by, selector)))
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found: {selector}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {selector}: {str(e)}")
            return None

    def safe_find_elements(self, selector, by=By.CSS_SELECTOR):
        """Safely find multiple elements with error handling"""
        try:
            elements = self.driver.find_elements(by, selector)
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements {selector}: {str(e)}")
            return []

    def extract_text_safely(self, element, attribute=None):
        """Safely extract text from element"""
        try:
            if element is None:
                return ""
            if attribute:
                return element.get_attribute(attribute) or ""
            return element.text.strip()
        except Exception as e:
            self.logger.error(f"Error extracting text: {str(e)}")
            return ""

    def get_brand_name(self):
        """Extract product brand name"""
        try:
            selectors = [
                '.brand_name__',                  # Matches Reversible's brand class
                '.product-brand',
                'span[class*="brand"]',
                '.brand a',
                '.product-details__brand',
                'meta[itemprop="brand"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    brand = self.extract_text_safely(element)
                    if brand:
                        return brand

            # Check meta tag for brand
            try:
                meta_brand = self.driver.find_element(
                    By.CSS_SELECTOR, 'meta[itemprop="brand"]'
                ).get_attribute('content')
                if meta_brand:
                    return meta_brand.strip()
            except:
                pass

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting brand name: {str(e)}")
            return ""

    def get_product_name(self):
        """Extract product name from the product page"""
        try:
            # Based on your HTML: <div class="product_name__AYH0V" bis_skin_checked="1">Wool and cashmere diagonal scarf with striped edge</div>
            selectors = [
                'div.product_name__AYH0V',     # Exact match from your HTML
                '.product_name__AYH0V',       # Alternative without div
                '.product-name',              # Generic product name class
                '.product_name',              # Alternative naming
                'h1.product-title',           # H1 title fallback
                '[class*="product_name"]'     # Partial class match
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    name = self.extract_text_safely(element)
                    if name:
                        self.logger.info(f"Found product name: {name}")
                        return name

            self.logger.warning("Product name not found")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting product name: {str(e)}")
            return ""

    def get_product_details(self):
        """Extract product details (description)"""
        try:
            # Based on your HTML: <p class="multiline product_description__pre5a">...</p>
            selectors = [
                'p.product_description__pre5a',    # Exact match from your HTML
                '.product_description__pre5a',     # Alternative without p
                '.product-description',            # Generic description class
                '.product_description',            # Alternative naming
                '[class*="product_description"]',  # Partial class match
                '.description'                     # Simple fallback
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    description = self.extract_text_safely(element)
                    if description:
                        # Clean up the description (remove extra whitespace, line breaks)
                        description = ' '.join(description.split())
                        return description

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting product details: {str(e)}")
            return ""

    def get_image_urls(self):
        """Extract product image URL (single URL as string)"""
        try:
            selectors = [
                '.gallery_img__b1Dq1',              # Exact from provided HTML
                '.product-image img',
                '.main-product-image img',
                'img[src*="image-raw.reversible.com"]',  # Direct domain match
                'img[src*="/images/"]',
                'img[alt*="product"], img[alt*="item"]',
                '.product-gallery img',
                '.hero-image img'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    img_url = self.extract_text_safely(element, 'src')
                    if img_url and img_url.startswith('http'):
                        return img_url
                    elif img_url and img_url.startswith('/'):
                        return f"https://www.reversible.com{img_url}"

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {str(e)}")
            return ""

    def close_popups(self):
        """Close visible popups if they exist (non-blocking)."""
        try:
            popups = self.driver.find_elements(
                By.CSS_SELECTOR, ".popup_close, .modal-close, .overlay-close")
            if popups:
                for popup in popups:
                    try:
                        self.driver.execute_script(
                            "arguments[0].click();", popup)
                        self.logger.info("Popup detected and closed.")
                        time.sleep(0.5)  # Small delay so UI settles
                    except Exception as e:
                        self.logger.debug(f"Popup close failed: {e}")
        except Exception:
            pass

    def convert_currency(self, amount, from_currency, to_currency):
        """Convert currency using free exchange rate API"""
        try:
            if from_currency == to_currency:
                return amount

            # First try exchangerate-api.com (free tier, no key required)
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                if 'rates' in data and to_currency in data['rates']:
                    exchange_rate = data['rates'][to_currency]
                    converted_amount = amount * exchange_rate
                    self.logger.info(
                        f"Converted {amount} {from_currency} to {converted_amount:.2f} {to_currency}")
                    return converted_amount
                else:
                    self.logger.error(
                        f"Currency {to_currency} not found in rates")

            except Exception as e:
                self.logger.warning(
                    f"Primary API failed, trying fallback: {e}")

            # Fallback to exchangerate.host with latest endpoint (no key required)
            try:
                url = f"https://api.exchangerate.host/latest?base={from_currency}&symbols={to_currency}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get('success', False) and 'rates' in data:
                    if to_currency in data['rates']:
                        exchange_rate = data['rates'][to_currency]
                        converted_amount = amount * exchange_rate
                        self.logger.info(
                            f"Converted {amount} {from_currency} to {converted_amount:.2f} {to_currency} (fallback API)")
                        return converted_amount
                    else:
                        self.logger.error(
                            f"Currency {to_currency} not found in fallback API rates")
                else:
                    self.logger.error(
                        f"Fallback currency conversion failed: {data}")

            except Exception as e:
                self.logger.warning(f"Fallback API also failed: {e}")

            # Manual fallback rates (approximate, update periodically)
            manual_rates = {
                'USD': {'EUR': 0.92, 'GBP': 0.79, 'AED': 3.67},
                'EUR': {'USD': 1.09, 'GBP': 0.86, 'AED': 4.0},
                'GBP': {'USD': 1.27, 'EUR': 1.16, 'AED': 4.66},
                'AED': {'USD': 0.27, 'EUR': 0.25, 'GBP': 0.21}
            }

            if from_currency in manual_rates and to_currency in manual_rates[from_currency]:
                rate = manual_rates[from_currency][to_currency]
                converted_amount = amount * rate
                self.logger.info(
                    f"Using manual rate: {amount} {from_currency} to {converted_amount:.2f} {to_currency}")
                return converted_amount

            self.logger.error(
                f"Could not convert {from_currency} to {to_currency}")
            return None

        except Exception as e:
            self.logger.error(f"Currency conversion failed: {e}")
            return None

    def extract_price_value(self, price_text):
        """Extract numeric price value from price text"""
        try:
            if not price_text:
                return None

            # Remove currency symbols and extract number
            price_match = re.search(
                r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                return float(price_match.group())
            return None
        except Exception as e:
            self.logger.error(
                f"Error extracting price value from '{price_text}': {e}")
            return None

    def get_price_in_currency(self, target_currency, base_currency="USD"):
        """Get price converted to target currency"""
        try:
            # Get the original price from the page
            original_price_text = self.get_original_price()
            if not original_price_text:
                self.logger.warning("No original price found for conversion")
                return None

            # Extract numeric value
            price_value = self.extract_price_value(original_price_text)
            if price_value is None:
                self.logger.error(
                    f"Could not extract price value from: {original_price_text}")
                return None

            # Convert currency
            converted_amount = self.convert_currency(
                price_value, base_currency, target_currency)
            if converted_amount is None:
                return None

            # Format the result
            currency_symbols = {
                'USD': '$',
                'EUR': '€',
                'GBP': '£',
                'AED': 'AED '
            }

            symbol = currency_symbols.get(
                target_currency, f'{target_currency} ')
            if target_currency == 'AED':
                return f"{symbol}{converted_amount:.2f}"
            else:
                return f"{symbol}{converted_amount:.2f}"

        except Exception as e:
            self.logger.error(f"Error getting price in {target_currency}: {e}")
            return None

    def get_original_price(self):
        """Extract original price"""
        try:
            # Based on your HTML: <div class="card_price_value__JS1Ao" bis_skin_checked="1">$398</div>
            selectors = [
                'div.card_price_value__JS1Ao',    # Exact match from your HTML
                '.card_price_value__JS1Ao',      # Alternative without div
                '.price-value',                  # Generic price class
                '.card_price_value',             # Alternative naming
                '[class*="card_price_value"]',   # Partial class match
                '.price',                        # Simple fallback
                # Any element with price in class
                '[class*="price"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    price = self.extract_text_safely(element)
                    if price and ('€' in price or '$' in price or '£' in price):
                        self.logger.info(f"Found price: {price}")
                        return price

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting original price: {str(e)}")
            return ""

    def get_discount(self):
        """Extract discount percentage"""
        try:
            # Look for discount/sale indicators
            selectors = [
                '.discount',
                '.sale-badge',
                '.price-discount',
                '.percentage-discount',
                '[class*="discount"]',
                '[class*="sale"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    discount = self.extract_text_safely(element)
                    if discount and '%' in discount:
                        return discount

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting discount: {str(e)}")
            return ""

    def get_size_and_fit(self):
        """Extract size and fit information"""
        try:
            # Based on your HTML: <div class="ellipsis offer-filter_fixed_value__KUD2l" bis_skin_checked="1">ONE SIZE</div>
            selectors = [
                'div.offer-filter_fixed_value__KUD2l',  # Exact match from your HTML
                '.offer-filter_fixed_value__KUD2l',    # Alternative without div
                '[class*="offer-filter_fixed_value"]',  # Partial class match
                '.size-value',                          # Generic size class
                '.product-size',                        # Alternative naming
                # Any element with size in class
                '[class*="size"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    size = self.extract_text_safely(element)
                    if size:
                        self.logger.info(f"Found size: {size}")
                        return size

            # Try to find size options in dropdowns or selectors
            size_selectors = [
                'select.size-selector option',
                '.size-option',
                '.swatch-option',
                '.size-list li'
            ]

            available_sizes = []
            for selector in size_selectors:
                size_elements = self.safe_find_elements(selector)
                for element in size_elements:
                    size_text = self.extract_text_safely(element)
                    if size_text and size_text not in available_sizes:
                        available_sizes.append(size_text)

            if available_sizes:
                return ', '.join(available_sizes)

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting size and fit: {str(e)}")
            return ""

    def get_category_breadcrumb(self):
        """Extract category information from breadcrumb"""
        try:
            # Based on your HTML: <ol class="breadcrumbs_list__rEk3l no_scrollbar"><li class="breadcrumbs_breadcrumb__4Sog0"><a href="/shopping/men">Men</a></li>...
            breadcrumb_selectors = [
                'ol.breadcrumbs_list__rEk3l a',      # Exact from your HTML
                '.breadcrumbs_breadcrumb__4Sog0 a',  # Individual breadcrumb links
                '.breadcrumbs a',                     # Generic breadcrumb links
                '[class*="breadcrumbs"] a',          # Any breadcrumb class
                # Ordered list with breadcrumbs
                'ol[class*="breadcrumbs"] a'
            ]

            categories = []

            for selector in breadcrumb_selectors:
                breadcrumb_elements = self.safe_find_elements(selector)
                if breadcrumb_elements:
                    for element in breadcrumb_elements:
                        category = self.extract_text_safely(element)
                        if category and category.lower() not in ['home', 'reversible']:
                            categories.append(category)
                    break  # Use first successful selector

            if categories:
                category_path = ' > '.join(categories)
                self.logger.info(f"Found categories: {category_path}")
                return category_path

            return ""

        except Exception as e:
            self.logger.error(f"Error extracting categories: {str(e)}")
            return ""

    def scrape_product(self, url):
        """Scrape a single product page"""
        try:
            self.logger.info(f"Scraping URL: {url}")
            self.close_popups()
            self.random_delay(1, 2)

            # Navigate to the page
            self.driver.get(url)
            self.random_delay(3, 5)

            # Random scrolling to mimic human behavior
            self.scroll_randomly()

            # Wait for page to load
            self.wait_for_page_load()
            time.sleep(2)

            # Extract brand and product names
            brand = self.get_brand_name()
            self.logger.info(f"Brand name: {brand}")
            product_name = self.get_product_name()

            # Get original price first
            original_price = self.get_original_price()

            # Extract all product data in the exact format as ModeSens/Leam
            product_data = {
                'product_url': url,
                'brand': brand,
                'product_name': product_name,
                'product_details': self.get_product_details(),
                'category': self.get_category_breadcrumb(),
                'image_urls': self.get_image_urls(),
                'original_price': original_price,
                'discount': self.get_discount(),
                'size_and_fit': self.get_size_and_fit(),
            }

            # Add currency conversions
            self.logger.info("Converting prices to different currencies...")
            product_data.update({
                # Original is USD
                "price_usd": self.get_price_in_currency("USD", "USD"),
                "price_eur": self.get_price_in_currency("EUR", "USD"),
                "price_gbp": self.get_price_in_currency("GBP", "USD"),
                "price_aed": self.get_price_in_currency("AED", "USD")
            })

            # Calculate sale price if discount is available
            sale_price = ""
            if product_data['original_price'] and product_data['discount']:
                try:
                    # Extract price number
                    price_match = re.search(
                        r'[\d,]+\.?\d*', product_data['original_price'])
                    discount_match = re.search(
                        r'\d+', product_data['discount'])

                    if price_match and discount_match:
                        price_value = float(
                            price_match.group().replace(',', ''))
                        discount_percent = int(discount_match.group())

                        # Calculate sale price
                        sale_value = price_value * (1 - discount_percent / 100)

                        # Extract currency symbol
                        currency = '€' if '€' in product_data['original_price'] else '$' if '$' in product_data[
                            'original_price'] else '£' if '£' in product_data['original_price'] else ''

                        sale_price = f"{currency}{sale_value:.2f}"

                except Exception as e:
                    self.logger.debug(f"Error calculating sale price: {e}")

            product_data['sale_price'] = sale_price

            # Log extracted data
            self.logger.info(
                f"Successfully scraped: {product_data['brand']} - {product_data['product_name']}")

            return product_data

        except Exception as e:
            self.logger.error(f"Error scraping product from {url}: {str(e)}")
            return None

    def scrape_multiple_products(self, urls):
        """Scrape multiple product URLs"""
        results = []

        for i, url in enumerate(urls):
            try:
                self.logger.info(f"Processing {i+1}/{len(urls)}: {url}")

                product_data = self.scrape_product(url)
                if product_data:
                    results.append(product_data)
                    self.data_list.append(product_data)

                # Random delay between requests
                if i < len(urls) - 1:  # Don't delay after the last URL
                    self.random_delay(3, 7)

            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {str(e)}")
                continue

        return results

    def save_to_csv(self, filename='reversible_products.csv'):
        """Save scraped data to CSV file"""
        try:
            if not self.data_list:
                self.logger.warning("No data to save to CSV")
                return

            # Define CSV headers to match ModeSens output exactly
            headers = [
                'product_url', 'brand', 'product_name', 'product_details', 'category',
                'image_urls', 'original_price', 'sale_price', 'discount',
                'size_and_fit', 'price_aed', 'price_usd', 'price_gbp', 'price_eur'
            ]

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()

                for data in self.data_list:
                    # Ensure all headers are present in data
                    row_data = {header: data.get(header, '')
                                for header in headers}
                    writer.writerow(row_data)

            self.logger.info(f"Data saved to CSV: {filename}")

        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")

    def save_to_json(self, filename='reversible_products.json'):
        """Save scraped data to JSON file"""
        try:
            if not self.data_list:
                self.logger.warning("No data to save to JSON")
                return

            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.data_list, jsonfile,
                          indent=2, ensure_ascii=False)

            self.logger.info(f"Data saved to JSON: {filename}")

        except Exception as e:
            self.logger.error(f"Error saving to JSON: {str(e)}")

    def close(self):
        """Close the browser and cleanup"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
        finally:
            # Additional cleanup to prevent handle errors
            try:
                import gc
                gc.collect()
            except:
                pass
