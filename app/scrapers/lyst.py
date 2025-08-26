"""
Lyst.com Product Scraper
A comprehensive scraper for Lyst.com product pages with anti-bot detection
"""

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
from ..utils.index import setup_scraping_driver


class LystScraper:
    def __init__(self, headless=False, wait_time=10):
        """Initialize the scraper with undetected Chrome driver"""
        self.setup_logging()
        self.wait_time = wait_time
        self.data_list = []

        # Initialize undetected Chrome
        self.driver = setup_scraping_driver(headless=headless, website="lyst")

        self.wait = WebDriverWait(self.driver, wait_time)

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                # logging.FileHandler('lyst_scraper.log'),
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
                'a.W2cCC[href*="/designer/"]',  # Brand name selector
                'div._1b08vvhqu.vjlibs5.vjlibs2',  # Product name selector
                'div._1b08vvhrq.vjlibs2'  # Price selector
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
            # Based on your HTML: <a class="W2cCC" href="/designer/the-row/">The Row</a>
            selectors = [
                'a.W2cCC[href*="/designer/"]',  # Primary selector
                'a[href*="/designer/"].W2cCC',  # Alternative order
                'a[href*="/designer/"]',        # Fallback without class
                '.W2cCC[href*="/designer/"]'    # Class first
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    brand = self.extract_text_safely(element)
                    if brand:
                        self.logger.info(f"Found brand name: {brand}")
                        return brand

            self.logger.warning("Brand name not found")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting brand name: {str(e)}")
            return ""

    def get_product_name(self):
        """Extract product name from the product page"""
        try:
            # Based on your HTML: <div class="_1b08vvhqu vjlibs5 vjlibs2" style="--vjlibs4: 2;">Women's Black Liisa Ankle Boots</div>
            selectors = [
                'div._1b08vvhqu.vjlibs5.vjlibs2',  # Exact match from your HTML
                # More flexible
                'div[class*="_1b08vvhqu"][class*="vjlibs5"][class*="vjlibs2"]',
                'div._1b08vvhqu',  # Partial match
                'div[class*="_1b08vvhqu"]'  # Very flexible
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

    def click_product_details_dropdown(self):
        """Click on the Product details dropdown to expand it"""
        try:
            # Based on your HTML: <div class="_1j1nmye3">
            dropdown_selectors = [
                'div._1j1nmye3',
                'h2._1b08vvhru.vjlibs0.vjlibs2',  # The actual h2 element
                'div[class*="_1j1nmye3"]'
            ]

            for selector in dropdown_selectors:
                try:
                    dropdown_element = self.safe_find_element(selector)
                    if dropdown_element:
                        # Scroll to element to make it visible
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", dropdown_element)
                        self.random_delay(1, 2)

                        # Try to click the dropdown
                        self.driver.execute_script(
                            "arguments[0].click();", dropdown_element)
                        self.logger.info("Clicked product details dropdown")

                        # Wait a bit for the dropdown to expand
                        self.random_delay(1, 2)
                        return True
                except Exception as e:
                    self.logger.debug(
                        f"Could not click with selector {selector}: {e}")
                    continue

            self.logger.warning("Could not click product details dropdown")
            return False

        except Exception as e:
            self.logger.error(
                f"Error clicking product details dropdown: {str(e)}")
            return False

    def get_product_details(self):
        """Extract product details by clicking dropdown and getting description"""
        try:
            # First, try to click the dropdown to expand it
            dropdown_clicked = self.click_product_details_dropdown()

            if dropdown_clicked:
                # Wait for content to load
                self.random_delay(1, 2)

            # Based on your HTML: <div class="_1b08vvh31 *1b08vvhq6 vjlibs2">
            # Note: The asterisk in the class name might be a typo, so we'll try different variations
            selectors = [
                'div._1b08vvh31[class*="1b08vvhq6"].vjlibs2',  # Most specific
                'div._1b08vvh31.vjlibs2',  # Without the problematic class
                'div[class*="_1b08vvh31"][class*="vjlibs2"]',  # More flexible
                'div[class*="_1b08vvh31"]',  # Just the first class
                '.product-details-content',  # Generic fallback
                '[data-testid="product-details"]'  # Another fallback
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    details = self.extract_text_safely(element)
                    if details:
                        # Clean up the description (remove extra whitespace, line breaks)
                        details = ' '.join(details.split())
                        self.logger.info(
                            f"Found product details: {details[:100]}...")
                        return details

            self.logger.warning("Product details not found")
            return ""

        except Exception as e:
            self.logger.error(f"Error extracting product details: {str(e)}")
            return ""

    def get_image_urls(self):
        """Extract product image URL"""
        try:
            # Based on your HTML: <img class="qptelu3" ... src="https://cdna.lystit.com/...">
            selectors = [
                'img.qptelu3',  # Exact match from your HTML
                'img[class*="qptelu"]',  # Partial match
                'img[src*="lystit.com"]',  # By domain
                'img[alt*="Black Liisa Ankle Boots"]',  # By alt text pattern
                '.product-image img',  # Generic fallback
                'img[src*="photos"]'  # Generic photo selector
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    img_url = self.extract_text_safely(element, 'src')
                    if img_url and img_url.startswith('http'):
                        self.logger.info(f"Found image URL: {img_url}")
                        return img_url

            self.logger.warning("Image URL not found")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {str(e)}")
            return ""

    def get_original_price(self):
        """Extract original price"""
        try:
            # Based on your HTML: <div class="_1b08vvhrq vjlibs2">$1,791.00</div>
            selectors = [
                'div._1b08vvhrq.vjlibs2',  # Exact match from your HTML
                'div[class*="_1b08vvhrq"][class*="vjlibs2"]',  # More flexible
                'div._1b08vvhrq',  # Partial match
                'div[class*="_1b08vvhrq"]',  # Very flexible
                '.price',  # Generic fallback
                '[data-testid="price"]'  # Another fallback
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    price = self.extract_text_safely(element)
                    if price and ('$' in price or '€' in price or '£' in price):
                        self.logger.info(f"Found original price: {price}")
                        return price

            self.logger.warning("Original price not found")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting original price: {str(e)}")
            return ""

    def get_discount(self):
        """Extract discount percentage - Lyst might not always show discount"""
        try:
            # Look for common discount selectors
            selectors = [
                '.discount',
                '.sale-percentage',
                '.price-reduction',
                '[data-testid="discount"]',
                'span[class*="discount"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    discount = self.extract_text_safely(element)
                    if discount and '%' in discount:
                        self.logger.info(f"Found discount: {discount}")
                        return discount

            # If no explicit discount found, return empty
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting discount: {str(e)}")
            return ""

    def get_category_from_breadcrumb(self):
        """Extract category information from breadcrumb - last 2 items"""
        try:
            # Based on your HTML: <ol class="_17myytj0"><li class="_17myytj1"><a href="/" class="_17myytj3"><span class="_17myytj2">Home</span></a></li>...
            breadcrumb_selectors = [
                'ol._17myytj0 li._17myytj1 span._17myytj2',  # Exact match
                'ol[class*="_17myytj0"] span[class*="_17myytj2"]',  # More flexible
                '.breadcrumb span',  # Generic fallback
                'ol li span',  # Very generic
                '[data-testid="breadcrumb"] span'  # Another fallback
            ]

            categories = []

            for selector in breadcrumb_selectors:
                elements = self.safe_find_elements(selector)
                if elements:
                    for element in elements:
                        category = self.extract_text_safely(element)
                        if category and category.lower() not in ['home', 'lyst']:
                            categories.append(category)

                    if categories:
                        break

            # Return last 2 categories as requested
            if len(categories) >= 2:
                last_two = categories[-2:]
                category_string = ' > '.join(last_two)
                self.logger.info(
                    f"Found categories (last 2): {category_string}")
                return category_string
            elif categories:
                category_string = ' > '.join(categories)
                self.logger.info(f"Found categories (all): {category_string}")
                return category_string

            self.logger.warning("Categories not found in breadcrumb")
            return ""

        except Exception as e:
            self.logger.error(f"Error extracting categories: {str(e)}")
            return ""

    def get_size_and_fit(self):
        """Extract size and fit information"""
        try:
            # Look for size selectors on Lyst
            size_selectors = [
                'select[name*="size"]',
                '.size-selector select',
                '.product-options select',
                '[data-testid="size-selector"]',
                'select.size-dropdown'
            ]

            available_sizes = []

            for selector in size_selectors:
                try:
                    size_element = self.safe_find_element(selector)
                    if size_element:
                        select = Select(size_element)
                        options = select.options

                        for option in options:
                            size_text = self.extract_text_safely(option)
                            if size_text and size_text not in ["Choose size", "Select size", ""]:
                                available_sizes.append(size_text)

                        if available_sizes:
                            break
                except Exception as e:
                    self.logger.debug(
                        f"Error with size selector {selector}: {e}")
                    continue

            # If no dropdown found, look for size buttons/options
            if not available_sizes:
                size_option_selectors = [
                    '.size-option',
                    '.size-button',
                    '[data-testid="size-option"]',
                    '.product-size-option'
                ]

                for selector in size_option_selectors:
                    size_elements = self.safe_find_elements(selector)
                    for element in size_elements:
                        size_text = self.extract_text_safely(element)
                        if size_text and size_text not in available_sizes:
                            available_sizes.append(size_text)

            if available_sizes:
                size_string = ', '.join(available_sizes)
                self.logger.info(f"Found sizes: {size_string}")
                return size_string
            else:
                return "Size information not available"

        except Exception as e:
            self.logger.error(f"Error extracting size and fit: {str(e)}")
            return ""

    def get_multi_region_prices(self):
        """Extract prices for multiple regions"""
        try:
            price_data = {
                'price_aed': '',
                'price_usd': '',
                'price_gbp': '',
                'price_eur': ''
            }

            # Get the original price first
            original_price = self.get_original_price()

            if original_price:
                # Determine currency and assign to appropriate field
                if '$' in original_price:
                    price_data['price_usd'] = original_price
                elif '€' in original_price:
                    price_data['price_eur'] = original_price
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

            # Extract all product data
            product_data = {
                'product_url': url,
                'brand': self.get_brand_name(),
                'product_name': self.get_product_name(),
                # This will click dropdown and get details
                'product_details': self.get_product_details(),
                'category': self.get_category_from_breadcrumb(),
                'image_urls': self.get_image_urls(),
                'original_price': self.get_original_price(),
                'discount': self.get_discount(),
                'size_and_fit': self.get_size_and_fit()
            }

            # Calculate sale price if discount exists
            sale_price = ""
            if product_data['original_price'] and product_data['discount']:
                try:
                    price_match = re.search(
                        r'[\d,]+\.?\d*', product_data['original_price'])
                    discount_match = re.search(
                        r'\d+', product_data['discount'])

                    if price_match and discount_match:
                        price_value = float(
                            price_match.group().replace(',', ''))
                        discount_percent = int(discount_match.group())
                        sale_value = price_value * (1 - discount_percent / 100)

                        currency = '$' if '$' in product_data['original_price'] else '€' if '€' in product_data[
                            'original_price'] else '£' if '£' in product_data['original_price'] else ''
                        sale_price = f"{currency}{sale_value:.2f}"

                except Exception as e:
                    self.logger.debug(f"Error calculating sale price: {e}")

            product_data['sale_price'] = sale_price

            # Add multi-region pricing
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
                if i < len(urls) - 1:
                    self.random_delay(3, 7)

            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {str(e)}")
                continue

        return results[0]

    def save_to_csv(self, filename='lyst_products.csv'):
        """Save scraped data to CSV file"""
        try:
            if not self.data_list:
                self.logger.warning("No data to save to CSV")
                return

            headers = [
                'product_url', 'brand', 'product_name', 'product_details', 'category',
                'image_urls', 'original_price', 'sale_price', 'discount',
                'size_and_fit', 'price_aed', 'price_usd', 'price_gbp', 'price_eur'
            ]

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()

                for data in self.data_list:
                    row_data = {header: data.get(header, '')
                                for header in headers}
                    writer.writerow(row_data)

            self.logger.info(f"Data saved to CSV: {filename}")

        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")

    def save_to_json(self, filename='lyst_products.json'):
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
            try:
                import gc
                gc.collect()
            except:
                pass
