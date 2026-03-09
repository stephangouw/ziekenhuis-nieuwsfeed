import requests
from bs4 import BeautifulSoup
import sys
import re

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def debug_links(url):
    print(f"Fetching {url}")
    resp = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    seen = set()
    for a in soup.find_all('a'):
        href = a.get('href', '')
        # Only print urls that might be news articles (long paths)
        if len(href) > 30 and ('nieuws' in href or 'actueel' in href or '202' in href or 'artikel' in href):
            if href not in seen:
                # find the parent container 
                parent = a.find_parent('div')
                parent_class = parent.get('class') if parent else None
                article_parent = a.find_parent('article')
                
                print(f"---")
                print(f"HREF: {href}")
                print(f"A Class: {a.get('class')}")
                print(f"Parent Div Class: {parent_class}")
                print(f"In <article>? {bool(article_parent)}")
                seen.add(href)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_links(sys.argv[1])
    else:
        print("Usage: python debug_selectors.py <url>")
