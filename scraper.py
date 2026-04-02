import requests
from bs4 import BeautifulSoup
import os
import time

BASE_URL = "https://novascotia.ca"
INDEX_URL = "https://novascotia.ca/just/regulations/regsbyact.htm"
DATA_DIR = "data"
MAX_REGS = 15  # keep small for local testing

HEADERS = {
    "User-Agent": "Mozilla/5.0 (educational research project)"
}

def get_regulation_links(index_url):
    """
    Scrape the index page and return a list of (title, url) tuples
    for individual regulation pages.
    """
    print(f"Fetching index page: {index_url}")
    response = requests.get(index_url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    # Each regulation link is an <a> tag pointing to regs/*.htm
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Filter: only links that go into the /regs/ subfolder
        if href.startswith("regs/") and href.endswith(".htm"):
            full_url = BASE_URL + "/just/regulations/" + href
            title = a_tag.get_text(strip=True)
            if title:  # skip empty link text
                links.append((title, full_url))

    print(f"Found {len(links)} regulation links on index page")
    return links


def download_regulation(title, url):
    """
    Download one regulation page and save it as an HTML file in data/.
    Returns the filepath it was saved to, or None if download failed.
    """
    # Make a safe filename from the URL
    filename = url.split("/")[-1]  # e.g. "envairqt.htm"
    filepath = os.path.join(DATA_DIR, filename)

    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"  Already have: {filename}")
        return filepath

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"  Downloaded: {title} -> {filename}")
        return filepath

    except Exception as e:
        print(f"  FAILED: {title} ({e})")
        return None


def run_scraper():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Step 1: get all links from the index
    all_links = get_regulation_links(INDEX_URL)

    # Step 2: take only the first MAX_REGS
    subset = all_links[:MAX_REGS]
    print(f"\nDownloading {len(subset)} regulations...\n")

    downloaded = []
    for title, url in subset:
        filepath = download_regulation(title, url)
        if filepath:
            downloaded.append((title, url, filepath))
        time.sleep(0.5)  # be polite, don't hammer the server

    print(f"\nDone. Downloaded {len(downloaded)} regulation files to '{DATA_DIR}/'")
    return downloaded


if __name__ == "__main__":
    run_scraper()
