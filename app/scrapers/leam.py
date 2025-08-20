import time
import random
import json
import csv
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import logging


class LeamScraper:
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
                logging.FileHandler('leam_scraper.log'),
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
                '.price',
                '[itemprop="name"]',
                '.base[data-ui-id="page-title-wrapper"]'
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
        """Extract brand name from the product page"""
        try:
            # Updated based on your HTML: <h2><a href="https://www.leam.com/wrl_en/designers/valentino_garavani">VALENTINO GARAVANI</a></h2>
            selectors = [
                # Primary selector - brand link inside h2
                'h2 a[href*="/designers/"]',
                'a[href*="/designers/"]',     # Direct link selector
                'h2 a[href*="designers"]',    # Alternative with h2
                'a[href*="designers"]',       # Alternative without h2
                '.product-brand a',
                '.designer-link'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    brand = self.extract_text_safely(element)
                    if brand:
                        self.logger.info(
                            f"Found brand name with selector '{selector}': {brand}")
                        return brand

            # Additional debugging - try to find any h2 elements and log them
            h2_elements = self.safe_find_elements('h2')
            if h2_elements:
                self.logger.info(
                    f"Found {len(h2_elements)} h2 elements on page")
                for i, h2 in enumerate(h2_elements):
                    h2_text = self.extract_text_safely(h2)
                    self.logger.info(f"H2 {i+1} text: {h2_text}")

                    # Look for links inside each h2
                    try:
                        links = h2.find_elements(By.TAG_NAME, 'a')
                        for link in links:
                            href = self.extract_text_safely(link, 'href')
                            text = self.extract_text_safely(link)
                            self.logger.info(
                                f"H2 {i+1} contains link: href='{href}', text='{text}'")
                            if 'designers' in href.lower() and text:
                                self.logger.info(
                                    f"Found brand in debugging: {text}")
                                return text
                    except Exception as debug_e:
                        self.logger.debug(f"Debug error: {debug_e}")

            self.logger.warning(
                "Brand name not found after trying all selectors")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting brand name: {str(e)}")
            return ""

    def get_product_name(self):
        """Extract product name from the product page"""
        try:
            # Updated based on your HTML: <span class="base" data-ui-id="page-title-wrapper" itemprop="name">Chez Valentino T-shirt</span>
            selectors = [
                # Exact match from your HTML
                'span.base[data-ui-id="page-title-wrapper"][itemprop="name"]',
                # Alternative without itemprop
                '.base[data-ui-id="page-title-wrapper"]',
                'h1.page-title .base',  # In case it's within h1
                '.base[itemprop="name"]',  # Fallback with itemprop
                # Fallback with just data-ui-id
                '[data-ui-id="page-title-wrapper"]',
                '[itemprop="name"]'  # Final fallback
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
        """Extract product details (description as product details)"""
        try:
            # From your example: <div id="description">...</div>
            selectors = [
                'div#description',
                '#description',
                '.product-description',
                '.description',
                '.product-details'
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
            # From your example: <img alt="VALENTINO GARAVANI - Chez Valentino T-shirt" src="https://www.leam.com/media/catalog/product/...">
            selectors = [
                # Specific to your example
                'img[alt*="VALENTINO"], img[alt*="GARAVANI"]',
                '.product-image-main img',
                '.product-image img',
                'img[src*="/media/catalog/product/"]',
                '.gallery-image img',
                'img[alt*="-"]'  # Images with product names usually have dashes
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    img_url = self.extract_text_safely(element, 'src')
                    if img_url and img_url.startswith('http'):
                        return img_url

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {str(e)}")
            return ""

    def get_original_price(self):
        """Extract original price"""
        try:
            # From your example: <span class="price">€483.61</span>
            selectors = [
                'span.price',
                '.price',
                '.regular-price .price',
                '.old-price',
                '.original-price'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    price = self.extract_text_safely(element)
                    if price and ('€' in price or '$' in price or '£' in price):
                        return price

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting original price: {str(e)}")
            return ""

    def get_discount(self):
        """Extract discount percentage"""
        try:
            # From your example: <span class="discountproductpage">50%</span>
            selectors = [
                'span.discountproductpage',
                '.discountproductpage',
                '.discount',
                '.percentage-discount',
                '.price-discount'
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
        """Extract size and fit information (available sizes)"""
        try:
            # From your example: <select name="super_attribute[138]" data-selector="super_attribute[138]"...>
            available_sizes = []

            size_selectors = [
                'select[name*="super_attribute"]',
                'select.super-attribute-select',
                'select[data-selector*="super_attribute"]',
                '.size-selector select',
                '.product-options select'
            ]

            for selector in size_selectors:
                try:
                    size_element = self.safe_find_element(selector)
                    if size_element:
                        # Create a Select object to interact with the dropdown
                        select = Select(size_element)
                        options = select.options

                        for option in options:
                            size_text = self.extract_text_safely(option)
                            if size_text and size_text != "Choose an Option...":
                                available_sizes.append(size_text)

                        if available_sizes:
                            break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            # If no sizes found in dropdown, try alternative methods
            if not available_sizes:
                # Try to find size options in other elements
                size_option_selectors = [
                    '.size-option',
                    '.swatch-option',
                    '.product-option-value',
                    '[data-option-type="1"] .swatch-option'  # Size swatches
                ]

                for selector in size_option_selectors:
                    size_elements = self.safe_find_elements(selector)
                    for element in size_elements:
                        size_text = self.extract_text_safely(element)
                        if size_text and size_text not in available_sizes:
                            available_sizes.append(size_text)

            # If sizes found, format them properly
            if available_sizes:
                return ', '.join(available_sizes)
            else:
                # Return similar message to ModeSens format
                return "Sign up to view all available sizes"

        except Exception as e:
            self.logger.error(f"Error extracting size and fit: {str(e)}")
            return ""

    def get_category_breadcrumb(self):
        """Extract category information from breadcrumb"""
        try:
            breadcrumb_elements = self.safe_find_elements(
                '.breadcrumbs a, .breadcrumb a')
            categories = []

            for element in breadcrumb_elements:
                category = self.extract_text_safely(element)
                if category and category.lower() not in ['home', 'leam']:
                    categories.append(category)

            return ' > '.join(categories) if categories else ""

        except Exception as e:
            self.logger.error(f"Error extracting categories: {str(e)}")
            return ""

    def get_multi_region_prices(self):
        """Extract prices for multiple regions (AED, USD, GBP, EUR)"""
        try:
            price_data = {
                'price_aed': '',
                'price_usd': '',
                'price_gbp': '',
                'price_eur': ''
            }

            # Get the original price first to determine main currency
            original_price = self.get_original_price()

            if original_price:
                # Determine which currency the original price is in and assign it
                if '€' in original_price:
                    price_data['price_eur'] = original_price
                elif '$' in original_price:
                    price_data['price_usd'] = original_price
                elif '£' in original_price:
                    price_data['price_gbp'] = original_price
                elif 'AED' in original_price.upper():
                    price_data['price_aed'] = original_price

            return price_data

        except Exception as e:
            self.logger.error(
                f"Error extracting multi-region prices: {str(e)}")
            return {
                'price_aed': '',
                'price_usd': '',
                'price_gbp': '',
                'price_eur': ''
            }

    def scrape_product(self, url):
        """Scrape a single product page"""
        try:
            self.logger.info(f"Scraping URL: {url}")

            # Navigate to the page
            self.driver.get(url)
            self.random_delay(3, 5)

            # Random scrolling to mimic human behavior
            self.scroll_randomly()

            # Wait for page to load
            self.wait_for_page_load()
            time.sleep(2)

            # Extract brand and product names using updated methods
            brand_name = self.get_brand_name()
            product_name = self.get_product_name()

            # Extract all product data in the exact format as ModeSens
            product_data = {
                'product_url': url,
                'brand': brand_name,  # Brand name from designer link
                'product_name': product_name,  # Product name from page title
                # This is the actual product description
                'product_details': self.get_product_details(),
                'category': self.get_category_breadcrumb(),
                'image_urls': self.get_image_urls(),  # Single URL as string
                'original_price': self.get_original_price(),
                'discount': self.get_discount(),
                'size_and_fit': self.get_size_and_fit()  # Renamed from available_sizes
            }

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

            # Add multi-region price information to match ModeSens format
            price_info = self.get_multi_region_prices()
            product_data.update(price_info)

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

    def save_to_csv(self, filename='leam_products.csv'):
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

    def save_to_json(self, filename='leam_products.json'):
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
