#!/usr/bin/env python3
"""
Italist Product Scraper
A comprehensive scraper for Italist product pages with anti-bot detection and multi-region pricing
Adapted from ModeSens scraper format
"""

import time
import random
import json
import csv
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import logging
from ..utils.index import setup_scraping_driver


class ItalistScraper:
    def __init__(self, headless=False, wait_time=10):
        """Initialize the scraper with undetected Chrome driver"""
        self.setup_logging()
        self.wait_time = wait_time
        self.data_list = []

        # Initialize undetected Chrome
        self.driver = setup_scraping_driver(headless=headless)

        self.wait = WebDriverWait(self.driver, wait_time)

        # Define target regions for price extraction
        self.target_regions = [
            # {'country_code': 'gb', 'currency': 'GBP', 'key': 'price_gbp'},
            {'country_code': 'us', 'currency': 'USD', 'key': 'price_usd'},
            # {'country_code': 'en-ae', 'currency': 'AED', 'key': 'price_aed'},
            # {'country_code': 'de', 'currency': 'EUR', 'key': 'price_eur'}
        ]

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('italist_scraper.log'),
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

    def safe_find_element(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """Safely find element with error handling"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
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

    def safe_click(self, element, description="element"):
        """
        Safely click an element with fallback strategies to handle overlapping elements
        """
        try:
            if element is None:
                self.logger.warning(
                    f"Cannot click {description}: element is None")
                return False

            # Step 1: Scroll element into view with larger offset and wait longer
            try:
                # Scroll with much larger offset to avoid all overlapping elements
                self.driver.execute_script("""
                    var element = arguments[0];
                    var headerOffset = 300; // Increased offset for sticky elements
                    var elementPosition = element.getBoundingClientRect().top;
                    var offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                    window.scrollTo({
                        top: Math.max(0, offsetPosition),
                        behavior: 'instant'
                    });
                """, element)

                self.logger.info(
                    f"Scrolled {description} into view with large offset")
                self.random_delay(2, 3)  # Longer wait for page to settle

            except Exception as e:
                self.logger.warning(
                    f"Error scrolling {description} into view: {e}")

            # Step 2: Try JavaScript click first (most reliable for overlapping elements)
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self.logger.info(
                    f"Successfully clicked {description} with JavaScript")
                return True

            except Exception as js_error:
                self.logger.warning(
                    f"JavaScript click failed for {description}: {js_error}")

                # Step 3: Try custom event dispatch
                try:
                    self.driver.execute_script("""
                        var element = arguments[0];
                        var event = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        element.dispatchEvent(event);
                    """, element)
                    self.logger.info(
                        f"Successfully clicked {description} with custom event")
                    return True

                except Exception as event_error:
                    self.logger.warning(
                        f"Custom event click failed for {description}: {event_error}")

                    # Step 4: Try moving overlapping elements temporarily
                    try:
                        # Hide potential overlapping elements temporarily
                        self.driver.execute_script("""
                            // Hide common overlapping elements
                            var overlappingSelectors = [
                                '.jsx-181079620.vertical-spacer',
                                '.jsx-1578029185.header-column-last',
                                '.header-grid-container',
                                '.sticky-header'
                            ];
                            
                            var hiddenElements = [];
                            overlappingSelectors.forEach(function(selector) {
                                var elements = document.querySelectorAll(selector);
                                elements.forEach(function(el) {
                                    if (el.style.display !== 'none') {
                                        hiddenElements.push({element: el, originalDisplay: el.style.display});
                                        el.style.display = 'none';
                                    }
                                });
                            });
                            
                            // Store hidden elements for restoration
                            window.tempHiddenElements = hiddenElements;
                        """)

                        # Now try clicking
                        element.click()
                        self.logger.info(
                            f"Successfully clicked {description} after hiding overlapping elements")

                        # Restore hidden elements
                        self.driver.execute_script("""
                            if (window.tempHiddenElements) {
                                window.tempHiddenElements.forEach(function(item) {
                                    item.element.style.display = item.originalDisplay;
                                });
                                delete window.tempHiddenElements;
                            }
                        """)

                        return True

                    except Exception as hide_error:
                        # Restore elements even if click failed
                        try:
                            self.driver.execute_script("""
                                if (window.tempHiddenElements) {
                                    window.tempHiddenElements.forEach(function(item) {
                                        item.element.style.display = item.originalDisplay;
                                    });
                                    delete window.tempHiddenElements;
                                }
                            """)
                        except:
                            pass

                        self.logger.error(
                            f"All click methods failed for {description}: {hide_error}")
                        return False

        except Exception as e:
            self.logger.error(
                f"Unexpected error in safe_click for {description}: {e}")
            return False

    def get_brand_name(self):
        """Extract brand name"""
        try:
            selector = 'h2.jsx-2275224060.brand a.jsx-2275224060'
            element = self.safe_find_element(selector)
            if element:
                brand = self.extract_text_safely(element)
                return brand

            # Fallback selectors
            fallback_selectors = [
                'h2.brand a',
                '.brand a',
                'h2[class*="brand"] a'
            ]

            for selector in fallback_selectors:
                element = self.safe_find_element(selector)
                if element:
                    brand = self.extract_text_safely(element)
                    if brand:
                        return brand

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting brand name: {str(e)}")
            return ""

    def get_product_name(self):
        """Extract product name"""
        try:
            selector = 'h1.jsx-2275224060.model'
            element = self.safe_find_element(selector)
            if element:
                product_name = self.extract_text_safely(element)
                return product_name

            # Fallback selectors
            fallback_selectors = [
                'h1.model',
                'h1[class*="model"]',
                '.model'
            ]

            for selector in fallback_selectors:
                element = self.safe_find_element(selector)
                if element:
                    name = self.extract_text_safely(element)
                    if name:
                        return name

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting product name: {str(e)}")
            return ""

    def get_prices(self):
        """Extract sale price and original price"""
        try:
            prices = {
                'sale_price': '',
                'original_price': ''
            }

            # Extract sale price
            sale_price_selector = 'span.jsx-982166675.sales-price'
            sale_element = self.safe_find_element(sale_price_selector)
            if sale_element:
                sale_price = self.extract_text_safely(sale_element)
                prices['sale_price'] = sale_price.replace('\xa0', ' ').strip()

            # Extract original price
            original_price_selector = 'span.jsx-982166675.old-price'
            original_element = self.safe_find_element(original_price_selector)
            if original_element:
                original_price = self.extract_text_safely(original_element)
                prices['original_price'] = original_price.replace(
                    '\xa0', ' ').strip()

            return prices
        except Exception as e:
            self.logger.error(f"Error extracting prices: {str(e)}")
            return {'sale_price': '', 'original_price': ''}

    def get_size_and_fit(self):
        """Extract size and fit information by clicking size dropdown"""
        try:
            sizes_in_stock = []

            # Find the size dropdown button
            dropdown_selector = 'button.jsx-377655932'
            dropdown_button = self.safe_find_element(dropdown_selector)

            if dropdown_button:
                # Check if placeholder contains "Size: Italian"
                placeholder_text = self.extract_text_safely(dropdown_button)
                if "Size: Italian" in placeholder_text or "Size" in placeholder_text:

                    # Use safe_click to handle overlapping elements
                    if self.safe_click(dropdown_button, "size dropdown"):
                        self.random_delay(1, 2)

                        # Extract sizes from dropdown
                        size_list_selector = 'ul.jsx-377655932.visibleList.dropdown li.jsx-377655932.item'
                        size_elements = self.safe_find_elements(
                            size_list_selector)

                        for size_element in size_elements:
                            size_text = self.extract_text_safely(size_element)
                            if "in stock" in size_text.lower() or "left in stock" in size_text.lower():
                                # Extract just the size part (before "Only")
                                size_part = size_text.split("Only")[0].strip()
                                if size_part:
                                    sizes_in_stock.append(size_part)

                        # Click dropdown button again to close
                        self.safe_click(dropdown_button,
                                        "size dropdown (to close)")
                        self.random_delay(1, 3)
                    else:
                        self.logger.warning(
                            "Failed to click size dropdown button")

            return ", ".join(sizes_in_stock) if sizes_in_stock else ""

        except Exception as e:
            self.logger.error(f"Error extracting size and fit: {str(e)}")
            return ""

    def get_product_details(self):
        """Extract product details by clicking description accordion"""
        try:
            description = ""

            # Find the description accordion
            accordion_selector = 'div.jsx-3673602886.accordion-heading'
            accordion_elements = self.safe_find_elements(accordion_selector)

            for accordion in accordion_elements:
                accordion_text = self.extract_text_safely(accordion)
                if "Description" in accordion_text:

                    # Use safe_click to handle overlapping elements
                    if self.safe_click(accordion, "description accordion"):
                        self.random_delay(1, 2)

                        # Extract description content
                        description_selector = 'div.jsx-4137049903.expanded-section-text'
                        description_element = self.safe_find_element(
                            description_selector)

                        if description_element:
                            description = self.extract_text_safely(
                                description_element)
                            # Clean up the description text
                            description = description.replace(
                                '\n', ' ').strip()

                        # Click accordion again to close (optional)
                        self.safe_click(
                            accordion, "description accordion (to close)")
                        self.random_delay(1, 4)
                    else:
                        self.logger.warning(
                            "Failed to click description accordion")

                    break

            return description

        except Exception as e:
            self.logger.error(f"Error extracting product details: {str(e)}")
            return ""

    def get_category(self):
        """Extract category from breadcrumbs (last 2 items)"""
        try:
            breadcrumb_selector = 'div.jsx-2360960948.breadcrumbs-row a.jsx-2360960948.breadcrumbs-link'
            breadcrumb_elements = self.safe_find_elements(breadcrumb_selector)

            categories = []
            for element in breadcrumb_elements:
                category = self.extract_text_safely(element)
                if category and category.lower() not in ['home']:
                    categories.append(category)

            # Return last 2 categories
            if len(categories) >= 2:
                return " > ".join(categories[-2:])
            elif len(categories) == 1:
                return categories[0]
            else:
                return ""

        except Exception as e:
            self.logger.error(f"Error extracting category: {str(e)}")
            return ""

    def get_image_url(self):
        """Extract product image URL"""
        try:
            # Try multiple image selectors
            selectors = [
                'img[alt*="Antiqued Pink"]',
                'img[src*="cdn-images.italist.com"]',
                'img[data-nimg="intrinsic"]',
                '.product-image img',
                'img[alt][src*="italist"]'
            ]

            for selector in selectors:
                img_element = self.safe_find_element(selector)
                if img_element:
                    img_url = self.extract_text_safely(img_element, 'src')
                    if img_url and img_url.startswith('http'):
                        return img_url

            return ""

        except Exception as e:
            self.logger.error(f"Error extracting image URL: {str(e)}")
            return ""

    def get_regional_price(self, country_code):
        """Extract price from a specific regional URL"""
        try:
            # Get current URL and construct regional URL properly
            current_url = self.driver.current_url

            # Parse the current URL to construct regional URL
            # Example: https://www.italist.com/pk/women/shoes/... -> https://www.italist.com/gb/women/shoes/...
            if '/pk/' in current_url:
                regional_url = current_url.replace('/pk/', f'/{country_code}/')
            elif '/en/' in current_url:
                regional_url = current_url.replace('/en/', f'/{country_code}/')
            else:
                # Fallback: construct URL manually
                parts = current_url.split('/')
                # Find italist.com and replace the next part
                for i, part in enumerate(parts):
                    if 'italist.com' in part and i + 1 < len(parts):
                        parts[i + 1] = country_code
                        break
                regional_url = '/'.join(parts)

            self.logger.info(f"Navigating to regional URL: {regional_url}")
            self.driver.get(regional_url)
            self.random_delay(3, 5)  # Wait longer for page to load

            # Wait for price element to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'span.jsx-982166675.sales-price'))
                )
            except TimeoutException:
                self.logger.warning(
                    f"Price element not found quickly for {country_code}")

            # Extract price from regional page with multiple attempts
            price_selectors = [
                'span.jsx-982166675.sales-price',
                '.sales-price',
                'span[class*="sales-price"]',
                '.price-current',
                '.current-price'
            ]

            for selector in price_selectors:
                try:
                    sale_element = self.safe_find_element(selector, timeout=5)
                    if sale_element:
                        price = self.extract_text_safely(sale_element)
                        if price:
                            # Clean price and verify it's different from EUR
                            clean_price = price.replace('\xa0', ' ').strip()

                            # Check if price actually changed (not just EUR symbol)
                            if clean_price and not clean_price.startswith('€'):
                                self.logger.info(
                                    f"Found {country_code} price: {clean_price}")
                                return clean_price
                            elif clean_price.startswith('€') and country_code in ['gb', 'us']:
                                # If still showing EUR for GBP/USD regions, try waiting longer
                                self.random_delay(2, 3)
                                # Try again
                                refreshed_element = self.safe_find_element(
                                    selector, timeout=3)
                                if refreshed_element:
                                    refreshed_price = self.extract_text_safely(
                                        refreshed_element)
                                    refreshed_clean = refreshed_price.replace(
                                        '\xa0', ' ').strip()
                                    if refreshed_clean and not refreshed_clean.startswith('€'):
                                        self.logger.info(
                                            f"Found {country_code} price after refresh: {refreshed_clean}")
                                        return refreshed_clean

                            self.logger.info(
                                f"Found {country_code} price: {clean_price}")
                            return clean_price
                except Exception as e:
                    continue

            self.logger.warning(f"No price found for {country_code}")
            return ""

        except Exception as e:
            self.logger.error(
                f"Error extracting regional price for {country_code}: {str(e)}")
            return ""

    def get_multi_region_prices(self, base_url):
        """Extract prices from different regional URLs"""
        try:
            regional_prices = {}
            original_url = self.driver.current_url

            for region in self.target_regions:
                try:
                    price = self.get_regional_price(region['country_code'])
                    regional_prices[region['key']] = price
                    self.random_delay(1, 2)

                except Exception as e:
                    self.logger.error(
                        f"Error getting price for {region['country_code']}: {str(e)}")
                    regional_prices[region['key']] = ""
                    continue

            # Return to original URL
            try:
                self.driver.get(original_url)
                self.random_delay(1, 2)
            except:
                pass

            return regional_prices

        except Exception as e:
            self.logger.error(f"Error in get_multi_region_prices: {str(e)}")
            return {region['key']: "" for region in self.target_regions}

    def calculate_discount(self, original_price, sale_price):
        """Calculate discount percentage"""
        try:
            if not original_price or not sale_price:
                return ""

            # Extract numeric values
            original_num = re.findall(
                r'[\d,]+\.?\d*', original_price.replace(',', ''))
            sale_num = re.findall(r'[\d,]+\.?\d*', sale_price.replace(',', ''))

            if original_num and sale_num:
                original_val = float(original_num[0])
                sale_val = float(sale_num[0])

                if original_val > sale_val:
                    discount = ((original_val - sale_val) / original_val) * 100
                    return f"-{discount:.0f}%"

            return ""

        except Exception as e:
            self.logger.error(f"Error calculating discount: {str(e)}")
            return ""

    def scrape_product(self, url):
        """Scrape a single product page"""
        try:
            self.logger.info(f"Scraping URL: {url}")

            # Navigate to the page
            self.driver.get(url)
            self.random_delay(3, 5)

            # Random scrolling to mimic human behavior
            self.scroll_randomly()

            # Extract basic product information
            brand = self.get_brand_name()
            product_name = self.get_product_name()
            prices = self.get_prices()

            # Calculate discount
            discount = self.calculate_discount(
                prices['original_price'], prices['sale_price'])

            # Extract other product details
            size_and_fit = self.get_size_and_fit()
            product_details = self.get_product_details()
            category = self.get_category()
            image_url = self.get_image_url()

            # Get multi-region prices
            regional_prices = self.get_multi_region_prices(url)

            # Construct product data in the same format as ModeSens scraper
            product_data = {
                'product_url': url,
                'brand': brand,
                'product_name': product_name,  # Using brand as product_name to match format
                'product_details': product_details,
                'category': category,
                'image_urls': image_url,
                'original_price': prices['original_price'],
                'discount': discount,
                'sale_price': prices['sale_price'],
                'size_and_fit': size_and_fit,
                'price_aed': regional_prices.get('price_aed', ''),
                'price_usd': regional_prices.get('price_usd', ''),
                'price_gbp': regional_prices.get('price_gbp', ''),
                'price_eur': regional_prices.get('price_eur', '')
            }

            self.logger.info(f"Successfully scraped: {brand} - {product_name}")
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
                    self.random_delay(5, 10)

            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {str(e)}")
                continue

        return results

    def save_to_csv(self, filename='italist_products.csv'):
        """Save scraped data to CSV file"""
        try:
            if not self.data_list:
                self.logger.warning("No data to save to CSV")
                return

            # Get all possible headers from the data
            all_headers = set()
            for data in self.data_list:
                all_headers.update(data.keys())

            headers = sorted(list(all_headers))

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

    def save_to_json(self, filename='italist_products.json'):
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
