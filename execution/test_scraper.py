import requests
from bs4 import BeautifulSoup
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7'
}

def test_scrape(url, article_selector):
    print(f"Testing URL: {url}")
    print(f"Using Selector: '{article_selector}'")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Request failed: {e}")
        return
        
    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = soup.select(article_selector)
    
    print(f"Found {len(articles)} articles.")
    
    if len(articles) == 0:
        print("\n--- HTML Snippet (first 1000 chars of body) ---")
        body = soup.find('body')
        if body:
            print(str(body)[:1000])
        else:
            print("No body tag found")
            print(resp.text[:1000])
    else:
        for i, a in enumerate(articles[:3]):
            print(f"\n--- Article {i+1} HTML ---")
            print(str(a)[:500]) # First 500 chars

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_scraper.py <url> <selector>")
    else:
        test_scrape(sys.argv[1], sys.argv[2])
