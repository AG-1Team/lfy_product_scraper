#!/usr/bin/env python3
"""
Selfridges Product Scraper
A comprehensive scraper for Selfridges product pages with anti-bot detection and multi-region pricing
Adapted from ModeSens scraper to match exact output format requirements
"""

import time
import random
import json
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import logging
from ..utils.index import setup_scraping_driver


class SelfridgesScraper:
    def __init__(self, headless=False, wait_time=10):
        """Initialize the scraper with undetected Chrome driver"""
        self.setup_logging()
        self.wait_time = wait_time
        self.data_list = []

        # Initialize undetected Chrome
        self.driver = setup_scraping_driver(
            headless=headless, website="selfridge")

        self.wait = WebDriverWait(self.driver, wait_time)

        # Define target regions for price extraction
        self.target_regions = [
            # {'region': 'GB', 'currency': 'GBP', 'key': 'price_gbp', 'name': 'UK'},
            {'region': 'US', 'currency': 'USD', 'key': 'price_usd', 'name': 'US'},
            # {'region': 'DE', 'currency': 'EUR',
            #     'key': 'price_eur', 'name': 'Germany'},
            # {'region': 'US', 'currency': 'USD', 'key': 'price_aed',
            #     'name': 'UAE'}  # UAE uses same as USA
        ]

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('selfridges_scraper.log'),
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

                # Selfridges specific selectors
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

            # Second method: Press Escape key
            if not popup_closed:
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ESCAPE)
                    self.logger.info("Pressed Escape key to close popup")
                    popup_closed = True
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
        """Wait for the page to fully load and block any popups with enhanced delays"""
        try:
            # Initial delay to let page start loading
            self.logger.info("Waiting for initial page load...")
            self.random_delay(3, 5)

            # Accept cookies popup if present
            try:
                accept_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'button.cm__btn[data-role="all"]'))
                )
                self.driver.execute_script("arguments[0].click();", accept_btn)
                self.logger.info("Clicked 'Accept all' cookies button")
                self.random_delay(2, 3)
            except TimeoutException:
                self.logger.debug("No cookie popup found.")

            # Wait for main content to load
            main_selectors = [
                'a.sc-5ec017c-2',  # Brand name
                'p.sc-5ec017c-3.gsrfZb',  # Product name
                '.sc-eb97dd86-1'    # Price container
            ]

            page_loaded = False
            for selector in main_selectors:
                try:
                    self.logger.info(f"Waiting for element: {selector}")
                    element = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, selector))
                    )
                    if element:
                        self.logger.info(
                            f"Page loaded - found element: {selector}")
                        page_loaded = True
                        break
                except TimeoutException:
                    self.logger.warning(
                        f"Timeout waiting for element: {selector}")
                    continue

            # Additional delay for any popups/overlays to appear
            self.logger.info("Waiting for any popups/overlays to appear...")
            self.random_delay(3, 5)

            # Block popups after everything has loaded
            self.block_popups()

            # Final delay to ensure page is stable
            self.logger.info("Final stabilization delay...")
            self.random_delay(2, 4)

            if not page_loaded:
                self.logger.warning("Page load timeout - proceeding anyway")

            return page_loaded

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
        """Extract brand name from Selfridges page"""
        try:
            # Brand name selector as specified
            selectors = [
                'a.sc-5ec017c-2.fkKSpD',
                'a.sc-5ec017c-2',
                '[href*="/cat/"]'
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
        """Extract product name from Selfridges page"""
        try:
            # Product name selector as specified
            selectors = [
                'p.sc-5ec017c-3.gsrfZb',
                'p.sc-5ec017c-3'
                'h1 p[class^="sc-"]'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    product_name = self.extract_text_safely(element)
                    if product_name:
                        return product_name

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting product name: {str(e)}")
            return ""

    def get_current_price(self):
        """Extract current price from the page"""
        try:
            self.random_delay(3, 5)
            # Price selector as specified
            selectors = [
                'div.sc-eb97dd86-1.fCZakM span',
                'div.sc-eb97dd86-1 span',
                '.sc-eb97dd86-1 span'
            ]

            for selector in selectors:
                element = self.safe_find_element(selector)
                if element:
                    price = self.extract_text_safely(element)
                    if price:
                        return price.strip()

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting price: {str(e)}")
            return ""

    def get_sizes(self):
        """Extract available sizes with proper waiting and specific element targeting"""
        try:
            sizes = []

            self.logger.info("Starting size extraction process...")

            # Wait for size button to be present and clickable
            self.logger.info("Waiting for size button to load...")
            self.random_delay(2, 3)

            # Specific selector for the size button
            size_button_selector = 'button.sc-5476e0ca-1.huOPMo'

            button_clicked = False
            try:
                # Wait for the specific button to be present
                self.logger.info(
                    f"Looking for size button with selector: {size_button_selector}")
                button = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, size_button_selector))
                )

                if button:
                    # Verify this is the correct button by checking the inner div text
                    try:
                        inner_div = button.find_element(
                            By.CSS_SELECTOR, 'div.sc-5476e0ca-3.cdyaQx')
                        div_text = self.extract_text_safely(inner_div)
                        self.logger.info(f"Found button with text: {div_text}")

                        if "choose size" in div_text.lower():
                            # Scroll button into view and wait
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", button)
                            self.random_delay(1, 2)

                            # Wait for button to be clickable
                            clickable_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable(
                                    (By.CSS_SELECTOR, size_button_selector))
                            )

                            # Click the button
                            self.driver.execute_script(
                                "arguments[0].click();", clickable_button)
                            self.logger.info(
                                "Successfully clicked 'Choose size' button")
                            button_clicked = True
                        else:
                            self.logger.warning(
                                f"Button text doesn't match expected 'Choose size': {div_text}")
                    except Exception as e:
                        self.logger.warning(
                            f"Could not verify button text, trying to click anyway: {e}")
                        # Fallback: click button anyway
                        try:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", button)
                            self.random_delay(1, 2)
                            self.driver.execute_script(
                                "arguments[0].click();", button)
                            self.logger.info("Clicked size button (fallback)")
                            button_clicked = True
                        except Exception as e2:
                            self.logger.error(f"Failed to click button: {e2}")

            except TimeoutException:
                self.logger.warning(
                    f"Size button not found with selector: {size_button_selector}")
            except Exception as e:
                self.logger.error(f"Error finding size button: {e}")

            # Alternative approach if specific selector fails
            if not button_clicked:
                self.logger.info(
                    "Trying alternative approach to find size button...")
                try:
                    # Look for any button containing "choose size" text
                    all_buttons = self.driver.find_elements(
                        By.TAG_NAME, 'button')
                    for button in all_buttons:
                        try:
                            button_text = self.extract_text_safely(
                                button).lower()
                            if "choose size" in button_text or "select size" in button_text:
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView(true);", button)
                                self.random_delay(1, 2)
                                self.driver.execute_script(
                                    "arguments[0].click();", button)
                                self.logger.info(
                                    f"Successfully clicked size button (alternative): {button_text}")
                                button_clicked = True
                                break
                        except:
                            continue
                except Exception as e:
                    self.logger.error(
                        f"Alternative size button search failed: {e}")

            if not button_clicked:
                self.logger.warning(
                    "Could not click any size button - returning empty sizes")
                return []

            # Wait for size options to load after clicking
            self.logger.info("Waiting for size options to load...")
            self.random_delay(3, 5)  # Longer delay to ensure sizes load

            # Wait for size elements to appear
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div.sc-9e741bf7-3.fAGkUT'))
                )
                self.logger.info(
                    "Size elements detected, proceeding with extraction...")
            except TimeoutException:
                self.logger.warning(
                    "Size elements didn't load in time, trying anyway...")

            # Extract size options using the specific class you provided
            size_selector = 'div.sc-9e741bf7-3.fAGkUT'

            self.logger.info(
                f"Looking for sizes with selector: {size_selector}")
            size_elements = self.safe_find_elements(size_selector)

            self.logger.info(
                f"Found {len(size_elements)} potential size elements")

            for i, size_element in enumerate(size_elements):
                try:
                    size_text = self.extract_text_safely(size_element)
                    self.logger.info(f"Size element {i+1}: '{size_text}'")

                    # Check if size is available (not out of stock)
                    # Check the element and its parent for "out of stock" indicators
                    is_out_of_stock = False

                    # Check element text for out of stock indicators
                    if any(term in size_text.lower() for term in ['out of stock', 'notify me', 'notify', 'sold out', 'unavailable']):
                        is_out_of_stock = True
                        self.logger.info(
                            f"Size '{size_text}' marked as out of stock (text)")

                    # Check parent element for out of stock class or text
                    if not is_out_of_stock:
                        try:
                            parent = size_element.find_element(By.XPATH, "..")
                            parent_class = parent.get_attribute("class") or ""
                            parent_text = self.extract_text_safely(
                                parent).lower()

                            if ("out" in parent_class.lower() or "stock" in parent_class.lower() or
                                    "out of stock" in parent_text or "notify" in parent_text):
                                is_out_of_stock = True
                                self.logger.info(
                                    f"Size '{size_text}' marked as out of stock (parent)")
                        except:
                            pass

                    # Check for disabled state
                    if not is_out_of_stock:
                        try:
                            # Check if parent label/button is disabled
                            clickable_parent = size_element.find_element(
                                By.XPATH, "./ancestor::*[self::label or self::button][1]")
                            if (clickable_parent.get_attribute("disabled") or
                                    "disabled" in (clickable_parent.get_attribute("class") or "")):
                                is_out_of_stock = True
                                self.logger.info(
                                    f"Size '{size_text}' marked as disabled")
                        except:
                            pass

                    # If size is available, add it
                    if not is_out_of_stock and size_text and len(size_text.strip()) > 0:
                        clean_size = size_text.strip()
                        if clean_size not in sizes:
                            sizes.append(clean_size)
                            self.logger.info(
                                f"Added available size: '{clean_size}'")
                    elif is_out_of_stock:
                        self.logger.info(
                            f"Skipped out of stock size: '{size_text}'")

                except Exception as e:
                    self.logger.error(
                        f"Error processing size element {i+1}: {e}")
                    continue

            self.logger.info(
                f"Final result: Found {len(sizes)} available sizes: {sizes}")

            # Close the size modal after scraping
            self.logger.info("Closing size modal...")
            self.close_size_modal()

            return sizes

        except Exception as e:
            self.logger.error(f"Error extracting sizes: {str(e)}")
            # Try to close modal even if extraction failed
            try:
                self.close_size_modal()
            except:
                pass
            return []

    def close_size_modal(self):
        """Close the size selection modal"""
        try:
            close_button_selectors = [
                'button.sc-94ece902-4.bMxayC',
                'button.sc-94ece902-4',
                'button[class*="sc-94ece902-4"]'
            ]

            modal_closed = False
            for selector in close_button_selectors:
                try:
                    self.logger.info(
                        f"Looking for size modal close button with selector: {selector}")
                    close_buttons = self.safe_find_elements(selector)

                    for close_button in close_buttons:
                        try:
                            # Look for the specific span text "Close size list modal"
                            spans = close_button.find_elements(
                                By.TAG_NAME, 'span')
                            for span in spans:
                                span_text = self.extract_text_safely(span)
                                if "close size list modal" in span_text.lower():
                                    self.logger.info(
                                        f"Found size modal close button with text: '{span_text}'")
                                    self.driver.execute_script(
                                        "arguments[0].click();", close_button)
                                    self.logger.info(
                                        "Successfully clicked close button for size modal")
                                    modal_closed = True
                                    break

                            if modal_closed:
                                break
                        except Exception as e:
                            self.logger.debug(
                                f"Error checking button text: {e}")
                            # Fallback: try clicking if it has the right class structure
                            try:
                                # Check if button has the expected div structure
                                div_element = close_button.find_element(
                                    By.CSS_SELECTOR, 'div.sc-94ece902-5.gPsmKS')
                                if div_element:
                                    self.driver.execute_script(
                                        "arguments[0].click();", close_button)
                                    self.logger.info(
                                        "Clicked size modal close button (fallback method)")
                                    modal_closed = True
                                    break
                            except:
                                continue

                    if modal_closed:
                        break

                except Exception as e:
                    self.logger.debug(
                        f"Error with close button selector {selector}: {e}")
                    continue

            if not modal_closed:
                self.logger.warning(
                    "Could not find or click size modal close button - trying Escape key")
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ESCAPE)
                    self.logger.info("Pressed Escape key to close size modal")
                    modal_closed = True
                except Exception as e:
                    self.logger.error(
                        f"Failed to close modal with Escape key: {e}")

            # Wait for modal to close
            if modal_closed:
                self.logger.info("Waiting for size modal to close...")
                self.random_delay(2, 3)

            return modal_closed

        except Exception as e:
            self.logger.error(f"Error closing size modal: {str(e)}")
            return False

    def get_image_urls(self):
        """Extract product image URLs with enhanced lazy-load handling"""
        try:
            image_urls = []

            self.logger.info("Starting image URL extraction...")

            # Enhanced scrolling to trigger lazy-load for all images
            self.driver.execute_script(
                "window.scrollTo(0, 0);")  # Start from top
            self.random_delay(1, 2)

            # Scroll through different parts of the page
            scroll_positions = [
                "document.body.scrollHeight/6",
                "document.body.scrollHeight/4",
                "document.body.scrollHeight/3",
                "document.body.scrollHeight/2",
                "document.body.scrollHeight/1.5",
                "document.body.scrollHeight"
            ]

            for position in scroll_positions:
                self.driver.execute_script(f"window.scrollTo(0, {position});")
                self.random_delay(0, 2)

            # More comprehensive image selectors
            image_selectors = [
                # Primary selectors
                'img.Image-sc-1m9d13g-0',
                '.sc-8e7d5337-6 img',
                'img[loading="eager"]',
                'img[loading="lazy"]',

                # Additional selectors for Selfridges
                'img[class*="Image"]',
                'img[class*="sc-"]',
                'div[class*="image"] img',
                'div[class*="Image"] img',
                'picture img',
                'figure img',

                # Gallery and carousel images
                '[class*="gallery"] img',
                '[class*="carousel"] img',
                '[class*="slide"] img',

                # General product image selectors
                'img[src*="selfridges"]',
                'img[data-src*="selfridges"]',
                'img[srcset*="selfridges"]',
                'img[alt*="product"]',
                'img[alt*="Product"]'
            ]

            all_found_images = []

            for selector in image_selectors:
                try:
                    img_elements = self.safe_find_elements(selector)
                    self.logger.info(
                        f"Found {len(img_elements)} images with selector: {selector}")
                    all_found_images.extend(img_elements)
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")

            # Remove duplicates while preserving order
            unique_images = []
            seen_elements = set()
            for img in all_found_images:
                try:
                    # Use element's location and size as a unique identifier
                    element_id = (
                        img.location['x'], img.location['y'], img.size['width'], img.size['height'])
                    if element_id not in seen_elements:
                        unique_images.append(img)
                        seen_elements.add(element_id)
                except:
                    # Add anyway if we can't get location/size
                    unique_images.append(img)

            self.logger.info(
                f"Processing {len(unique_images)} unique image elements...")

            for img_element in unique_images:
                try:
                    # Try multiple attributes to get the image URL
                    img_url = None

                    # Check various attributes in order of preference
                    url_attributes = ['data-srcset', 'srcset',
                                      'data-src', 'src', 'data-original', 'data-lazy']

                    for attr in url_attributes:
                        try:
                            url_value = img_element.get_attribute(attr)
                            if url_value and url_value.strip():
                                img_url = url_value.strip()
                                break
                        except:
                            continue

                    if not img_url:
                        continue

                    # Handle srcset (comma-separated URLs with sizes)
                    if ',' in img_url and (' ' in img_url):
                        # Parse srcset and get the largest image
                        srcset_parts = img_url.split(',')
                        largest_url = None
                        largest_size = 0

                        for part in srcset_parts:
                            part = part.strip()
                            if ' ' in part:
                                url_part, size_part = part.rsplit(' ', 1)
                                try:
                                    # Extract numeric size (width)
                                    size_num = int(
                                        ''.join(filter(str.isdigit, size_part)))
                                    if size_num > largest_size:
                                        largest_size = size_num
                                        largest_url = url_part.strip()
                                except:
                                    # If we can't parse size, just take the URL
                                    largest_url = url_part.strip()

                        if largest_url:
                            img_url = largest_url

                    # Clean and validate URL
                    img_url = img_url.split()[0] if ' ' in img_url else img_url

                    # Filter valid URLs
                    if (img_url and
                        img_url.startswith(('http://', 'https://')) and
                        'data:image/gif' not in img_url and
                        'data:image/svg' not in img_url and
                            len(img_url) > 10):  # Reasonable URL length

                        # Avoid duplicates
                        if img_url not in image_urls:
                            image_urls.append(img_url)
                            self.logger.info(
                                f"Added image URL: {img_url[:100]}...")

                except Exception as e:
                    self.logger.debug(f"Error processing image element: {e}")
                    continue

            # If we still don't have images, try a more aggressive approach
            if not image_urls:
                self.logger.warning(
                    "No images found with standard methods, trying alternative approach...")

                # Look for any img tags and check their attributes
                all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
                self.logger.info(
                    f"Found {len(all_imgs)} total img elements on page")

                for img in all_imgs:
                    try:
                        # Get all attributes
                        src = img.get_attribute('src')
                        data_src = img.get_attribute('data-src')
                        srcset = img.get_attribute('srcset')

                        for url in [src, data_src, srcset]:
                            if (url and
                                url.startswith(('http://', 'https://')) and
                                'selfridges' in url and
                                'data:image/' not in url and
                                    url not in image_urls):

                                # Handle srcset
                                if ',' in url:
                                    url = url.split(',')[-1].split()[0]

                                image_urls.append(url)
                                self.logger.info(
                                    f"Found image via alternative method: {url[:100]}...")
                                break
                    except:
                        continue

            final_urls = ', '.join(image_urls) if image_urls else ""
            self.logger.info(
                f"Final image extraction result: {len(image_urls)} URLs found")

            if image_urls:
                self.logger.info(f"Sample URLs: {image_urls[0][:100]}...")
            else:
                self.logger.warning("No image URLs extracted")

            return final_urls

        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {str(e)}")
            return ""

    def get_product_details_extended(self):
        """Click on More information button, extract detailed information, then close the modal - UPDATED"""
        try:
            # Click on "More information" button
            detail_button_selectors = [
                'button.src__StyledLinkBase-sc-1dc10bo-0.cHLnnB',
                'button[class*="StyledLinkBase"]'
            ]

            button_clicked = False
            for selector in detail_button_selectors:
                try:
                    button = self.safe_find_element(selector)
                    if button and "more information" in self.extract_text_safely(button).lower():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", button)
                        self.random_delay(1, 3)
                        self.driver.execute_script(
                            "arguments[0].click();", button)
                        self.logger.info("Clicked More information button")
                        button_clicked = True
                        break
                except:
                    continue

            if not button_clicked:
                self.logger.warning("Could not click More information button")
                return ""

            # Wait for modal to open
            self.random_delay(2, 3)

            # Extract details from the modal
            detail_text = ""
            detail_selectors = [
                'div.sc-325c216d-1.gCbHlO',
                'div.sc-325c216d-1',
                '.gCbHlO ul',
                'div[class*="sc-325c216d"]'
            ]

            for selector in detail_selectors:
                detail_element = self.safe_find_element(selector)
                if detail_element:
                    detail_text = self.extract_text_safely(detail_element)
                    if detail_text:
                        break

            # Now click the close button to close the modal
            close_button_selectors = [
                'button.sc-94ece902-4.bMxayC',
                'button.sc-94ece902-4',
                'button[class*="sc-94ece902-4"]'
            ]

            modal_closed = False
            for selector in close_button_selectors:
                try:
                    close_buttons = self.safe_find_elements(selector)
                    for close_button in close_buttons:
                        # Verify this is the close button by checking for the text content
                        try:
                            # Look for span with close text inside the button
                            spans = close_button.find_elements(
                                By.TAG_NAME, 'span')
                            for span in spans:
                                span_text = self.extract_text_safely(span)
                                if "close product details modal" in span_text.lower():
                                    self.driver.execute_script(
                                        "arguments[0].click();", close_button)
                                    self.logger.info(
                                        "Successfully clicked close button for product details modal")
                                    modal_closed = True
                                    break
                            if modal_closed:
                                break
                        except:
                            # Fallback: just try clicking if it has the right class
                            try:
                                self.driver.execute_script(
                                    "arguments[0].click();", close_button)
                                self.logger.info(
                                    "Clicked close button (fallback method)")
                                modal_closed = True
                                break
                            except:
                                continue
                    if modal_closed:
                        break
                except Exception as e:
                    self.logger.debug(
                        f"Error clicking close button with selector {selector}: {e}")
                    continue

            if not modal_closed:
                self.logger.warning(
                    "Could not find or click close button - trying Escape key")
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ESCAPE)
                    self.logger.info("Pressed Escape key to close modal")
                except:
                    pass

            # Wait for modal to close
            self.random_delay(1, 2)

            return detail_text.strip() if detail_text else ""

        except Exception as e:
            self.logger.error(f"Error extracting product details: {str(e)}")
            return ""

    def get_category_breadcrumb(self):
        """Extract category information from breadcrumb"""
        try:
            breadcrumb_selectors = [
                'nav[aria-label="Breadcrumb"] ul.src__BreadcrumbWrapper-sc-rejbql-0 li a',
                'nav[aria-label="Breadcrumb"] li a',
                '.src__BreadcrumbWrapper-sc-rejbql-0 li a'
            ]

            categories = []
            for selector in breadcrumb_selectors:
                breadcrumb_elements = self.safe_find_elements(selector)
                if breadcrumb_elements:
                    for element in breadcrumb_elements:
                        category = self.extract_text_safely(element)
                        if category and category.lower() not in ['selfridges', 'home']:
                            categories.append(category)
                    break

            return ' > '.join(categories) if categories else ""

        except Exception as e:
            self.logger.error(f"Error extracting categories: {str(e)}")
            return ""

    def get_multi_region_prices_enhanced(self, base_url):
        """Extract prices for multiple regions by switching URLs"""
        self.random_delay(3, 5)
        try:
            # Initialize data structure with simple string format
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

            # Extract base product URL pattern
            base_pattern = base_url.replace('/GB/en/', '/{region}/en/')

            # Get sizes for size_and_fit field (this will also close the size modal)
            sizes = self.get_sizes()
            if sizes:
                price_data['size_and_fit'] = ', '.join(
                    sizes[:5])  # First 5 sizes

            # Wait after closing size modal before continuing
            self.logger.info(
                "Waiting after size modal closure before continuing...")
            self.random_delay(2, 4)

            # Extract prices from different regions
            for region in self.target_regions:
                try:
                    if region['key'] == 'price_aed':
                        # UAE uses US pricing
                        region_url = base_pattern.format(region='US')
                    else:
                        region_url = base_pattern.format(
                            region=region['region'])

                    self.logger.info(
                        f"Attempting to get price for {region['name']} from {region_url}")

                    # Navigate to region-specific URL
                    self.driver.get(region_url)
                    self.random_delay(3, 5)

                    # Block popups after navigation
                    self.block_popups()

                    # Wait for page to load
                    self.wait_for_page_load()

                    # Extract the price for this region
                    current_price = self.get_current_price()

                    if current_price:
                        currency_key = region['key']
                        price_data[currency_key] = current_price

                        # Set main fields for GBP region (original page)
                        if region['currency'] == 'GBP':
                            price_data['sale_price'] = current_price
                            price_data['original_price'] = current_price

                        self.logger.info(
                            f"Successfully extracted {region['currency']} price: {current_price}")
                    else:
                        self.logger.warning(
                            f"No price found for {region['name']}")

                    # Small delay between regions
                    self.random_delay(2, 3)

                except Exception as e:
                    self.logger.error(
                        f"Error extracting price for {region['name']}: {e}")
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
        """Scrape a single product page with enhanced waiting and popup handling"""
        try:
            self.logger.info(f"Scraping URL: {url}")

            # Navigate to the page
            self.driver.get(url)

            # Initial delay for page to start loading
            self.logger.info("Initial page load delay...")
            self.random_delay(3, 5)

            # Wait for page to fully load and handle popups properly
            self.wait_for_page_load()

            # Additional delay after popup handling
            self.logger.info("Post-popup handling delay...")
            self.random_delay(2, 4)

            # Random scrolling to mimic human behavior (after popups are handled)
            self.scroll_randomly()

            # Another small delay for page stabilization
            self.random_delay(1, 2)

            # Extract all product data in required format
            product_data = {
                'product_url': url,
                'brand': self.get_brand_name(),
                'product_name': self.get_product_details(),
                'product_details': self.get_product_details_extended(),
                'category': self.get_category_breadcrumb(),
                'image_urls': self.get_image_urls()
            }

            # Add enhanced multi-region price information
            price_info = self.get_multi_region_prices_enhanced(url)
            product_data.update(price_info)

            # Log extracted data
            self.logger.info(
                f"Successfully scraped: {product_data['brand']} - {product_data.get('product_details', 'No details')[:50]}...")

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

    def save_to_csv(self, filename='selfridges_products.csv'):
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

    def save_to_json(self, filename='selfridges_products.json'):
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
