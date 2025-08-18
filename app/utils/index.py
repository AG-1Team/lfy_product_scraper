def switch_website(url):
    if "farfetch" in url:
        return "farfetch"

    # Extract website name from URL
    return url.split("//")[1].split("/")[0]
