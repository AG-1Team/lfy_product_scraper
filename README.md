# Farfetch Product Scraper

This project is a comprehensive web scraper for [Farfetch](https://www.farfetch.com/ae/), designed to extract detailed product information from all major categories (Women, Men, Kids, etc.). The scraper collects product details, prices in multiple currencies, images, size and fit info, and more, and saves the data to CSV and JSON files. It also downloads product images into organized folders.

## Features
- Scrapes all products from all main Farfetch categories (no product limit by default)
- Extracts:
  - Brand
  - Product name
  - Product details
  - Category (breadcrumb)
  - Prices (AED, USD, GBP, EUR)
  - Sale/original price and discount
  - Size and fit info
  - High-resolution image URLs
  - Downloads product images
- Appends new data to existing CSV/JSON files without duplicates
- Human-like anti-detection behavior (random delays, stealth, user-agent rotation)
- Robust error handling and retry logic

## Requirements
- Python 3.8+
- Google Chrome browser
- ChromeDriver (matching your Chrome version, in PATH)
- The following Python packages:
  - selenium
  - selenium-stealth
  - fake-useragent
  - beautifulsoup4
  - pandas
  - requests

You can install dependencies with:
```bash
pip install -r requirements.txt
```

Example `requirements.txt`:
```
selenium
selenium-stealth
fake-useragent
beautifulsoup4
pandas
requests
```

## Setup
1. Ensure you have Google Chrome installed.
2. Download the matching ChromeDriver from [here](https://chromedriver.chromium.org/downloads) and add it to your system PATH.
3. (Optional) Create a virtual environment:
   ```bash
   python -m venv myenv
   myenv\Scripts\activate  # On Windows
   source myenv/bin/activate  # On Mac/Linux
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the scraper with:
```bash
python script1.py
```

- The script will scrape all products from all categories and save results to `farfetch_products.csv` and `farfetch_products.json`.
- Product images are saved in the `product_images/` folder, organized by product name.
- Existing products are skipped to avoid duplicates.

## Troubleshooting
- **ChromeDriver errors:** Ensure ChromeDriver is installed and matches your Chrome version. Add it to your PATH.
- **Permission errors on CSV/JSON:** Close any open Excel or editor windows using the output files and retry.
- **Blocked or missing data:** The script uses anti-detection, but scraping may fail if Farfetch changes their site or blocks bots. Try rerunning or updating selectors.
- **Slow scraping:** The script uses random delays and human-like behavior to avoid detection. This is normal.
- **Image download issues:** Check your internet connection and ensure the `product_images/` folder is writable.

## Customization
- To limit the number of products per category, set `MAX_PRODUCTS_PER_CATEGORY` in `main()`.
- To disable image downloading, set `DOWNLOAD_IMAGES = False` in `main()`.
- To add or remove categories, edit the `categories` dictionary in `main()`.

## License
This project is for educational and personal use only. Scraping commercial websites may violate their terms of service. Use responsibly. 


# Ounass Web Scraper

This is an advanced web scraper for the Ounass e-commerce website, designed to extract product information while bypassing anti-bot measures.

## Features

- 🛡️ Advanced anti-detection techniques
- 🚀 Multi-threaded browsing with realistic human behavior simulation
- 📦 Product data extraction (brand, name, price, category, images, etc.)
- 💾 Data export to CSV and JSON formats
- 🖼️ Automatic image downloading

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ounass-scraper.git
   cd ounass-scraper