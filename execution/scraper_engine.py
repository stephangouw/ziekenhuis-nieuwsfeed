import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent.parent))
from execution.database import insert_article, get_connection
from execution.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html',
}

def clean_dutch_date(date_str):
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    date_str = date_str.lower().strip()
    match = re.search(r'(\d{1,2})[\s\.\-/]+(\w+|\d{1,2})[\s\.\-/]+(\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        if month.isdigit():
            try:
                return f"{year}-{int(month):02d}-{int(day):02d}"
            except: pass
    return datetime.now().strftime("%Y-%m-%d")

def get_h1_or_title(soup):
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    title = soup.find('title')
    if title:
        return title.get_text(strip=True).split('|')[0].split('-')[0].strip()
    return "Nieuwsbericht"

def get_first_paragraph(soup):
    # Try to find a logical intro or first real paragraph
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 80: # Skip tiny breadcrumb or meta paragraphs
            return text
    return "Lees het volledige artikel op de website van het ziekenhuis."

def extract_date_from_deep(soup):
    time_tag = soup.find('time')
    if time_tag:
         return clean_dutch_date(time_tag.get_text(strip=True))
    # Look for common date spans
    for span in soup.find_all(['span', 'p']):
        text = span.get_text(strip=True).lower()
        if len(text) < 30 and re.search(r'\d{1,2} (jan|feb|maa|apr|mei|jun|jul|aug|sep|okt|nov|dec)', text):
             return clean_dutch_date(text)
    return clean_dutch_date("")

def crawl_hospital(hospital_name, network_name, url):
    logger.info(f"Crawling [scraper-only auto-crawler] {hospital_name}: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch overview {url}: {e}")
        return 0

    soup = BeautifulSoup(resp.text, 'html.parser')
    base_domain = urlparse(url).netloc
    
    # Heuristics: find links that look like news articles
    article_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Resolve to full URL
        full_url = urljoin(url, href)
        # Check if it's on the same domain and not the homepage/news index itself
        if urlparse(full_url).netloc == base_domain and full_url != url:
             if 'nieuws/' in full_url.lower() or 'actueel/' in full_url.lower() or re.search(r'/\d{4}/\d{2}/', full_url) or len(href) > 25:
                 # Exclude pdfs, mailto, pagination
                 if not any(x in href.lower() for x in ['.pdf', 'mailto:', 'page=', '?p=', '#']):
                     article_links.add(full_url)

    count = 0
    # Process only the first 10 per run to save time
    for article_url in list(article_links)[:10]:
        try:
             # Check if we already have it to avoid expensive HTTP requests
             conn = get_connection()
             cursor = conn.cursor()
             cursor.execute("SELECT id FROM articles WHERE url = ?", (article_url,))
             exists = cursor.fetchone()
             conn.close()
             
             if exists:
                 continue
                 
             time.sleep(1) # Be nice
             art_resp = requests.get(article_url, headers=HEADERS, timeout=10)
             art_soup = BeautifulSoup(art_resp.text, 'html.parser')
             
             title = get_h1_or_title(art_soup)
             summary = get_first_paragraph(art_soup)
             pub_date = extract_date_from_deep(art_soup)
             
             # In scraper-only mode, we overload original_content with the summary
             # and set ai_summary directly so the frontend picks it up immediately.
             insert_success = insert_article(hospital_name, network_name, title, article_url, pub_date, original_content=summary)
             if insert_success:
                 # Manually update ai_summary to bypass AI Processor
                 conn = get_connection()
                 c = conn.cursor()
                 c.execute("""
                     UPDATE articles 
                     SET ai_summary = ?, tags = '["' || ? || '", "Nieuws"]'
                     WHERE url = ?
                 """, (summary, network_name, article_url))
                 conn.commit()
                 conn.close()
                 count += 1
                 
        except Exception as e:
             logger.warning(f"Failed deep-crawl on {article_url}: {e}")

    logger.info(f"Successfully processed {count} NEW articles for {hospital_name}")
    return count

def run_scrapers():
    config = load_config()
    total = 0
    for network_name, network_data in config.get("networks", {}).items():
        for hospital in network_data.get("hospitals", []):
            # Fallbacks for specific hospitals users mentioned
            scrape_url = hospital["url"]
            if hospital["name"] == "Anna Ziekenhuis":
                scrape_url = "https://www.annaziekenhuis.nl/nieuws/"
            elif hospital["name"] == "Catharina Ziekenhuis":
                scrape_url = "https://www.catharinaziekenhuis.nl/actueel/"
            elif hospital["name"] == "Elkerliek Ziekenhuis":
                scrape_url = "https://www.elkerliek.nl/nieuws-overzicht"
                
            total += crawl_hospital(hospital["name"], network_name, scrape_url)
            
    logger.info(f"Finished auto-crawler run. Total new articles found: {total}")

if __name__ == "__main__":
    run_scrapers()
