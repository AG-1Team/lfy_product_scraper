import time
import random
import json
import csv
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
import logging


class ModeSensScraper:
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
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36 Edg/124.0.2478.51",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.60 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0"
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

        # Define target regions for price extraction
        self.target_regions = [
            {'country': 'United States', 'currency': 'USD', 'key': 'price_usd'},
            {'country': 'United Kingdom', 'currency': 'GBP', 'key': 'price_gbp'},
            {'country': 'United Arab Emirates',
                'currency': 'AED', 'key': 'price_aed'},
            {'country': 'Germany (Deutschland)',
             'currency': 'EUR', 'key': 'price_eur'}
        ]

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('modesens_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def block_popups(self):
        """Block login popups and overlays that might appear - focuses on clicking background/backdrop"""
        try:
            popup_closed = False

            # First priority: Click on backdrop/background areas to close popups
            backdrop_selectors = [
                # Common backdrop selectors
                '.modal-backdrop',
                '.backdrop',
                '[class*="backdrop"]',
                '.overlay',
                '[class*="overlay"]',
                '.modal-overlay',

                # ModeSens specific selectors (you might need to inspect the actual popup)
                '[class*="popup-overlay"]',
                '[class*="modal-overlay"]',
                '.popup-backdrop',
                '[data-backdrop="true"]',

                # Generic overlay patterns
                'div[style*="position: fixed"]',
                'div[style*="z-index"]'
            ]

            # Try clicking on backdrop elements first (most reliable method)
            for selector in backdrop_selectors:
                try:
                    backdrop_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, selector)
                    for backdrop in backdrop_elements:
                        if backdrop.is_displayed():
                            # Check if this looks like a backdrop (usually covers full screen)
                            size = backdrop.size
                            location = backdrop.location

                            # If element is large enough to be a backdrop, click it
                            if size['width'] > 500 and size['height'] > 500:
                                try:
                                    # Click on the backdrop (not the popup content)
                                    self.driver.execute_script(
                                        "arguments[0].click();", backdrop)
                                    self.logger.info(
                                        f"Clicked backdrop to close popup: {selector}")
                                    popup_closed = True
                                    break
                                except:
                                    try:
                                        # Fallback: regular click
                                        backdrop.click()
                                        self.logger.info(
                                            f"Regular clicked backdrop: {selector}")
                                        popup_closed = True
                                        break
                                    except:
                                        continue

                    if popup_closed:
                        break

                except Exception as e:
                    continue

            # Second method: Click outside any detected popup content
            if not popup_closed:
                try:
                    popup_content_selectors = [
                        '.modal',
                        '.popup',
                        '.dialog',
                        '[role="dialog"]',
                        '[class*="modal"]',
                        '[class*="popup"]',
                        '[id*="modal"]',
                        '[id*="popup"]'
                    ]

                    for selector in popup_content_selectors:
                        popup_elements = self.driver.find_elements(
                            By.CSS_SELECTOR, selector)
                        for popup in popup_elements:
                            if popup.is_displayed():
                                # Get popup boundaries
                                popup_rect = popup.rect

                                # Calculate coordinates outside the popup but within viewport
                                viewport_width = self.driver.execute_script(
                                    "return window.innerWidth")
                                viewport_height = self.driver.execute_script(
                                    "return window.innerHeight")

                                # Try clicking to the left of the popup
                                if popup_rect['x'] > 50:
                                    click_x = popup_rect['x'] - 20
                                    click_y = popup_rect['y'] + \
                                        (popup_rect['height'] // 2)
                                # Try clicking to the right of the popup
                                elif popup_rect['x'] + popup_rect['width'] < viewport_width - 50:
                                    click_x = popup_rect['x'] + \
                                        popup_rect['width'] + 20
                                    click_y = popup_rect['y'] + \
                                        (popup_rect['height'] // 2)
                                # Try clicking above the popup
                                elif popup_rect['y'] > 50:
                                    click_x = popup_rect['x'] + \
                                        (popup_rect['width'] // 2)
                                    click_y = popup_rect['y'] - 20
                                # Try clicking below the popup
                                elif popup_rect['y'] + popup_rect['height'] < viewport_height - 50:
                                    click_x = popup_rect['x'] + \
                                        (popup_rect['width'] // 2)
                                    click_y = popup_rect['y'] + \
                                        popup_rect['height'] + 20
                                else:
                                    continue

                                # Ensure coordinates are within viewport
                                if 0 < click_x < viewport_width and 0 < click_y < viewport_height:
                                    try:
                                        # Click outside the popup
                                        ActionChains(self.driver).move_by_offset(
                                            click_x, click_y).click().perform()
                                        self.logger.info(
                                            f"Clicked outside popup at coordinates ({click_x}, {click_y})")
                                        popup_closed = True
                                        break
                                    except:
                                        continue

                        if popup_closed:
                            break

                except Exception as e:
                    self.logger.debug(f"Error clicking outside popup: {e}")

            # Third method: Press Escape key
            if not popup_closed:
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ESCAPE)
                    self.logger.info("Pressed Escape key to close popup")
                    popup_closed = True
                except:
                    pass

            # Fourth method: Click on body element (sometimes works)
            if not popup_closed:
                try:
                    # Click on a safe area of the page (top-left corner)
                    ActionChains(self.driver).move_by_offset(
                        10, 10).click().perform()
                    self.logger.info(
                        "Clicked on page background to close popup")
                    popup_closed = True
                except:
                    pass

            # Fifth method: JavaScript click on document
            if not popup_closed:
                try:
                    self.driver.execute_script("""
                        // Try to find and click backdrop elements
                        var backdrops = document.querySelectorAll('.modal-backdrop, .backdrop, .overlay, [class*="backdrop"], [class*="overlay"]');
                        for (var i = 0; i < backdrops.length; i++) {
                            if (backdrops[i].offsetParent !== null) {
                                backdrops[i].click();
                                console.log('Clicked backdrop via JS');
                                break;
                            }
                        }
                    """)
                    self.logger.info("Executed JavaScript to close popup")
                except:
                    pass

            # Wait a moment for popup to close
            self.random_delay(1, 2)

        except Exception as e:
            self.logger.debug(f"Error in block_popups: {str(e)}")

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
        """Wait for the page to fully load and block any popups"""
        try:
            # Wait for the main product container to load
            main_selectors = [
                '.prd-brand',
                '.prd-name',
                '[data-v-046b2d68]'
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
                        # Block popups after page loads
                        self.block_popups()
                        return True
                except TimeoutException:
                    continue

            self.logger.warning("Page load timeout - proceeding anyway")
            # Still try to block popups even if page didn't load completely
            self.block_popups()
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

    def click_country_dropdown(self):
        """Click on the country/currency dropdown button"""
        try:
            # Block popups before attempting to click dropdown
            self.block_popups()

            # Try multiple selectors for the dropdown button
            dropdown_selectors = [
                'button.country-language-btn',
                'button[aria-haspopup="menu"]',
                '.country-language-btn',
                'button.dropdown-toggle.country-language-btn'
            ]

            for selector in dropdown_selectors:
                try:
                    dropdown_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if dropdown_button:
                        # Scroll to the element to ensure it's visible
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", dropdown_button)
                        self.random_delay(1, 3)

                        # Click the dropdown
                        dropdown_button.click()
                        self.logger.info(
                            "Successfully clicked country dropdown")
                        self.random_delay(1, 2)
                        return True
                except (TimeoutException, NoSuchElementException):
                    continue
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            self.logger.warning("Could not find or click country dropdown")
            return False

        except Exception as e:
            self.logger.error(f"Error clicking country dropdown: {e}")
            return False

    def select_country_region(self, country_name, currency_code):
        """Select a specific country/region from the dropdown"""
        try:
            # Wait for the country list to be visible
            self.random_delay(1, 2)

            # Try different XPath strategies to find the country box
            xpath_selectors = [
                f"//div[contains(@class, 'country-box')]//span[contains(@class, 'country-name') and contains(text(), '{country_name}')]",
                f"//div[contains(@class, 'country-box')]//span[contains(text(), '{country_name}')]",
                f"//span[contains(@class, 'country-name') and contains(text(), '{country_name}')]/parent::div",
                f"//div[contains(@class, 'country-box') and contains(., '{country_name}') and contains(., '{currency_code}')]"
            ]

            for xpath in xpath_selectors:
                try:
                    country_elements = self.driver.find_elements(
                        By.XPATH, xpath)

                    for element in country_elements:
                        # Verify this element contains both country name and currency
                        element_text = self.extract_text_safely(element)
                        if country_name in element_text and currency_code in element_text:
                            # Scroll to element and click
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", element)
                            self.random_delay(1, 2)

                            # Try clicking the element or its parent
                            try:
                                element.click()
                            except:
                                # If direct click fails, try clicking the parent div
                                parent = element.find_element(By.XPATH, "..")
                                parent.click()

                            self.logger.info(
                                f"Successfully selected {country_name} ({currency_code})")
                            self.random_delay(2, 4)  # Wait for page to update
                            return True

                except (TimeoutException, NoSuchElementException):
                    continue
                except Exception as e:
                    self.logger.debug(f"Error with XPath {xpath}: {e}")
                    continue

            self.logger.warning(
                f"Could not find or select {country_name} ({currency_code})")
            return False

        except Exception as e:
            self.logger.error(
                f"Error selecting country region {country_name}: {e}")
            return False

    def close_dropdown_if_open(self):
        """Close the dropdown if it's still open"""
        try:
            # Try to click somewhere else to close dropdown
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            self.random_delay(1, 3)
        except:
            pass

    def extract_current_price(self, region_name):
        """Extract the current price displayed on the page for the selected region"""
        try:
            price_data = {
                'sale_price': '',
                'high_price': '',
                'original_price': '',
                'full_price_range': ''
            }

            # Try to find the main price container first
            price_container_selectors = [
                'div.price-pid[data-v-351a5081]',
                '.price-pid',
                'div[id*="price"]',
                '[data-v-351a5081][class*="price"]'
            ]

            price_container = None
            for selector in price_container_selectors:
                price_container = self.safe_find_element(selector)
                if price_container:
                    break

            if price_container:
                # Extract sale price (low price)
                try:
                    sale_price_element = price_container.find_element(
                        By.CSS_SELECTOR, '.price-sale')
                    sale_price = self.extract_text_safely(sale_price_element)
                    if sale_price:
                        price_data['sale_price'] = sale_price.strip()
                        self.logger.info(
                            f"Found {region_name} sale price: {sale_price}")
                except:
                    pass

                # Extract high price
                try:
                    high_price_element = price_container.find_element(
                        By.CSS_SELECTOR, '.price-high')
                    high_price = self.extract_text_safely(high_price_element)
                    if high_price:
                        price_data['high_price'] = high_price.strip()
                        self.logger.info(
                            f"Found {region_name} high price: {high_price}")
                except:
                    pass

                # Get full price range text
                full_text = self.extract_text_safely(price_container)
                if full_text:
                    price_data['full_price_range'] = full_text.strip()
                    self.logger.info(
                        f"Found {region_name} full price range: {full_text}")

            # Try to find original price (crossed out or different styling)
            original_price_selectors = [
                '.price-original',
                '.price-before',
                '.text-line-through',
                '.price-was',
                '[style*="text-decoration: line-through"]',
                '.original-price'
            ]

            for selector in original_price_selectors:
                element = self.safe_find_element(selector)
                if element:
                    original_price = self.extract_text_safely(element)
                    if original_price and any(char.isdigit() for char in original_price):
                        price_data['original_price'] = original_price.strip()
                        self.logger.info(
                            f"Found {region_name} original price: {original_price}")
                        break

            # If no structured price found, try fallback methods
            if not any(price_data.values()):
                fallback_selectors = [
                    '.price-min',
                    '.text-secondary-red .price-min',
                    '.sale-price',
                    '[data-v-351a5081] .price-min',
                    '.price-current',
                    '.current-price'
                ]

                for selector in fallback_selectors:
                    element = self.safe_find_element(selector)
                    if element:
                        price_text = self.extract_text_safely(element)
                        if price_text and any(char.isdigit() for char in price_text):
                            price_data['sale_price'] = price_text.strip()
                            price_data['full_price_range'] = price_text.strip()
                            self.logger.info(
                                f"Found {region_name} fallback price: {price_text}")
                            break

            # If still no price, try XPath approach
            if not any(price_data.values()):
                currency_symbols = ['£', '€', 'AED', 'USD', 'GBP', 'EUR']
                for symbol in currency_symbols:
                    try:
                        xpath = f"//*[contains(text(), '{symbol}') and (contains(text(), 'to') or contains(., 'to'))]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            text = self.extract_text_safely(element)
                            if text and symbol in text and 'to' in text:
                                price_data['full_price_range'] = text.strip()

                                # Try to extract individual prices from the range
                                price_matches = re.findall(
                                    rf'{re.escape(symbol)}(\d+(?:,\d{{3}})*(?:\.\d{{2}})?)', text)
                                if len(price_matches) >= 2:
                                    price_data['sale_price'] = f"{symbol}{price_matches[0]}"
                                    price_data['high_price'] = f"{symbol}{price_matches[1]}"
                                elif len(price_matches) == 1:
                                    price_data['sale_price'] = f"{symbol}{price_matches[0]}"

                                self.logger.info(
                                    f"Found {region_name} price range via XPath: {text}")
                                break
                        if price_data['full_price_range']:
                            break
                    except:
                        continue

            return price_data

        except Exception as e:
            self.logger.error(
                f"Error extracting current price for {region_name}: {e}")
            return {
                'sale_price': '',
                'high_price': '',
                'original_price': '',
                'full_price_range': ''
            }

    def get_brand_name(self):
        """Extract brand name - this is the product name in your format"""
        try:
            # Main selector from your example
            selectors = [
                'a.prd-brand.d-flex.font-weight-bold.text-truncate[data-v-046b2d68]',
                'a.prd-brand.d-flex.font-weight-bold.text-truncate',
                '.prd-brand',
                '.brand-name',
                'a[title*="ALEXANDRE"], a[title*="AMI"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    brand = self.extract_text_safely(element)
                    if brand:
                        return brand

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting brand name: {str(e)}")
            return ""

    def get_product_details(self):
        """Extract product details - this is the product details in your format"""
        try:
            # Main selector from your example
            selectors = [
                'div.prd-name.font-weight-light.text-truncate[itemprop="name"][data-v-046b2d68]',
                'div.prd-name.font-weight-light.text-truncate[itemprop="name"]',
                '.prd-name[itemprop="name"]',
                '[itemprop="name"]',
                '.product-title'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    # Try text first
                    details = self.extract_text_safely(element)
                    if details:
                        return details
                    # Try title attribute
                    title = self.extract_text_safely(element, 'title')
                    if title:
                        return title

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting product details: {str(e)}")
            return ""

    def get_image_urls(self):
        """Extract product image URLs"""
        try:
            image_urls = []

            # Try multiple selectors for images
            selectors = [
                'img.mw-100.mh-100.img-wrapper-prd[itemprop="image"]',
                'img[itemprop="image"]',
                '.product-image img',
                '.prd-img img',
                'img[src*="mytheresa"], img[src*="farfetch"], img[src*="ssense"]'
            ]

            for selector in selectors:
                img_elements = self.safe_find_elements(selector)
                for img_element in img_elements:
                    img_url = self.extract_text_safely(img_element, 'src')
                    if img_url and img_url.startswith('http') and img_url not in image_urls:
                        image_urls.append(img_url)

            # Return first image or all images joined by comma
            return image_urls[0] if image_urls else ""

        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {str(e)}")
            return ""

    def get_category_breadcrumb(self):
        """Extract category information from breadcrumb"""
        try:
            breadcrumb_elements = self.safe_find_elements(
                'ul[aria-label="breadcrumb"] li a')
            categories = []

            for element in breadcrumb_elements:
                category = self.extract_text_safely(element)
                if category and category.lower() not in ['modesens', 'designers']:
                    categories.append(category)

            return ' > '.join(categories) if categories else ""

        except Exception as e:
            self.logger.error(f"Error extracting categories: {str(e)}")
            return ""

    def get_multi_region_prices_enhanced(self):
        """Extract prices for multiple regions by switching countries - Simple string format"""
        try:
            # Initialize data structure with simple string format like your example
            price_data = {
                'original_price': '',
                'discount': '',
                'sale_price': '',
                'size_and_fit': '',
                'price_aed': '',
                'price_usd': '',
                'price_gbp': '',
                'price_eur': ''
            }

            # Store the current URL to return to it
            current_url = self.driver.current_url

            # First, extract any existing price information
            # Try to find discount percentage
            discount_selectors = [
                '.price-discount',
                '[data-v-351a5081] .price-discount'
            ]

            for selector in discount_selectors:
                element = self.safe_find_element(selector)
                if element:
                    discount_text = self.extract_text_safely(element)
                    if discount_text:
                        price_data['discount'] = discount_text.strip()
                        break

            # Try to find size and fit information
            try:
                range_elements = self.driver.find_elements(
                    By.XPATH, "//*[contains(text(), 'Sign up to view all available sizes')]")
                if not range_elements:
                    range_elements = self.driver.find_elements(
                        By.XPATH, "//*[contains(text(), 'to ')]")

                for element in range_elements:
                    text = self.extract_text_safely(element)
                    if 'Sign up to view all available sizes' in text:
                        price_data['size_and_fit'] = text.strip()
                        self.logger.info(f"Found size and fit info: {text}")
                        break
                    elif 'to ' in text and not any(curr in text for curr in ['$', '€', '£', 'AED', 'USD', 'GBP', 'EUR']):
                        price_data['size_and_fit'] = text.strip()
                        self.logger.info(f"Found size info: {text}")
                        break
            except:
                pass

            # Now extract prices from different regions
            for region in self.target_regions:
                try:
                    self.logger.info(
                        f"Attempting to get price for {region['country']} ({region['currency']})")

                    # Block popups before interacting with dropdown
                    self.block_popups()

                    # Click the country dropdown
                    if self.click_country_dropdown():
                        # Select the specific region
                        if self.select_country_region(region['country'], region['currency']):
                            # Wait for page to update with new prices
                            self.random_delay(3, 5)

                            # Block popups after region change
                            self.block_popups()

                            # Extract the price for this region
                            current_price = self.extract_current_price(
                                region['country'])

                            # Store the price as a simple string (use full_price_range or sale_price)
                            currency_key = region['key']
                            if currency_key in price_data:
                                if current_price.get('full_price_range'):
                                    price_data[currency_key] = current_price['full_price_range']
                                elif current_price.get('sale_price'):
                                    price_data[currency_key] = current_price['sale_price']

                            # Set main fields for USD region
                            if region['currency'] == 'USD' and current_price:
                                if current_price.get('sale_price'):
                                    price_data['sale_price'] = current_price['sale_price']
                                # Set original_price same as USD price
                                if current_price.get('full_price_range'):
                                    price_data['original_price'] = current_price['full_price_range']
                                elif current_price.get('sale_price'):
                                    price_data['original_price'] = current_price['sale_price']

                            self.logger.info(
                                f"Successfully extracted {region['currency']} price: {price_data[currency_key]}")
                        else:
                            self.logger.warning(
                                f"Failed to select {region['country']}")
                    else:
                        self.logger.warning(
                            f"Failed to open dropdown for {region['country']}")

                    # Close dropdown if still open
                    self.close_dropdown_if_open()

                    # Small delay between regions
                    self.random_delay(1, 2)

                except Exception as e:
                    self.logger.error(
                        f"Error extracting price for {region['country']}: {e}")
                    # Close dropdown if still open and continue
                    self.close_dropdown_if_open()
                    continue

            return price_data

        except Exception as e:
            self.logger.error(
                f"Error in get_multi_region_prices_enhanced: {str(e)}")
            return {
                'original_price': '',
                'discount': '',
                'sale_price': '',
                'size_and_fit': '',
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
            self.random_delay(2, 4)

            # Block popups immediately after page load
            self.block_popups()

            # Random scrolling to mimic human behavior
            self.scroll_randomly()

            # Wait for page to load and block popups again
            self.wait_for_page_load()

            # Extract all product data in your required format
            product_data = {
                'product_url': url,
                'brand': self.get_brand_name(),
                'product_name': self.get_product_details(),
                'product_details': "",
                'category': self.get_category_breadcrumb(),
                'image_urls': self.get_image_urls()
            }

            # Add enhanced multi-region price information with exact nested format
            price_info = self.get_multi_region_prices_enhanced()
            product_data.update(price_info)

            # Log extracted data
            self.logger.info(
                f"Successfully scraped: {product_data['brand']} - {product_data['product_details']}")

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
                    self.random_delay(5, 10)  # Longer delay between products

            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {str(e)}")
                continue

        return results

    def save_to_csv(self, filename='modesens_products.csv'):
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

    def save_to_json(self, filename='modesens_products.json'):
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
