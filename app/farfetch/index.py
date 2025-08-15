from ..product.index import extract_product_details, download_product_images


def farfetch_retrieve_products(driver, url):
    """Main scraping function with enhanced error handling and data display"""
    try:
        product_data = extract_product_details(driver, url)

        # if download_images:
        #     try:
        #         download_product_images(product_data, True)
        #     except Exception as img_error:
        #         print(f"[⚠] Error downloading images: {str(img_error)}")

        return product_data

    except KeyboardInterrupt:
        print("\n[⚠] Scraping interrupted by user")

    except Exception as e:
        print(f"\n[❌] Unexpected error: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
