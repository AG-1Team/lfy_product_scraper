def extract_website(url):
    # Extract website name from URL
    return url.split("//")[1].split("/")[0]
