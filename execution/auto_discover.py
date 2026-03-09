import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
import sys
import logging
from pathlib import Path
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common headers to mimic a regular browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7'
}

# Load API key
load_dotenv(Path(__file__).parent.parent / '.env')
try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("Please install google-genai: pip install google-genai")
    sys.exit(1)

def discover_news_url(base_url):
    """Attempt to find the news section link from the homepage."""
    logger.info(f"Scanning homepage {base_url} for a news section...")
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {base_url}: {e}")
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Common keywords in Dutch for news sections
    keywords = ['nieuws', 'actueel', 'persberichten', 'media', 'nieuwsberichten']
    
    found_links = []
    for a in soup.find_all('a', href=True):
        text = a.get_text().lower()
        href = a['href'].lower()
        if any(kw in text for kw in keywords) or any(kw in href for kw in keywords):
            full_url = urljoin(base_url, a['href'])
            # Avoid generic # links or mailto
            if full_url != base_url and not full_url.startswith('javascript:'):
                found_links.append(full_url)
                
    if found_links:
        # Just pick the first likely candidate. In a real scenario we could rank them.
        best_link = found_links[0]
        # Prefer links that actually end in /nieuws or similar
        for link in found_links:
            if '/nieuws' in link or '/actueel' in link:
                best_link = link
                break
        logger.info(f"Discovered likely news URL: {best_link}")
        return best_link
    
    logger.warning("Could not automatically discover a news page URL.")
    return None

def analyze_with_ai(hospital_name, news_url):
    """Fetch the news page HTML and send it to AI for selector extraction."""
    logger.info(f"Fetching HTML from {news_url} for AI analysis...")
    try:
        response = requests.get(news_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {news_url}: {e}")
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Strip unnecessary tags to save context and tokens
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'svg', 'img']):
        tag.decompose()
        
    # Get a portion of the main body (gemini flash has a big context, but let's keep it reasonable)
    main_content = soup.find('main') or soup.find('body')
    html_snippet = str(main_content)[:50000] # roughly 50k chars is plenty for list structure
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in .env files.")
        return None
        
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to load genai client: {e}")
        return None
        
    prompt = f"""
    Je bent een expert in web scraping. Hieronder vind je de (gedeeltelijke) HTML van de nieuwspagina van het '{hospital_name}' ziekenhuis: {news_url}.
    
    HTML Snippet:
    ```html
    {html_snippet}
    ```
    
    Jouw taak: Bepaal de meest robuuste CSS selectors om een lijst van nieuwsartikelen te scrapen, en stuur de output EXACT en ALLEEN als JSON terug.
    
    - 'article': Selector voor de 'container' van één nieuwsbericht in de lijst (bijv. '.news-item', 'article', '.card').
    - 'title': Selector BINNEN de article-container voor de titeltekst (bijv. 'h2', 'h3', '.title').
    - 'link': Selector BINNEN de article-container voor link / href (bijv. 'a', 'a.read-more'). Vaak is deze gewoon 'a'.
    - 'date': Selector BINNEN de article-container voor de publicatiedatum (bijv. 'time', '.date', 'span.date').
    - 'content': Omdat dit de overzichtspagina is, moeten we raden wat de content selector op de DETAILpagina zal zijn. Gebruik standaard '.content-block, main, article, .entry-content' tenzij je duidelijke aanwijzingen in de classnames zit.

    Output format EXPECTED:
    {{
        "name": "{hospital_name}",
        "url": "{news_url}",
        "selectors": {{
            "article": "...",
            "title": "...",
            "link": "...",
            "date": "...",
            "content": "..."
        }}
    }}
    """
    
    logger.info("Sending HTML to Gemini for selector generation...")
    try:
         response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
         
         result_json = json.loads(response.text.strip())
         return result_json
         
    except Exception as e:
         logger.error(f"AI generation failed: {e}")
         return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python auto_discover.py \"Ziekenhuis Naam\" \"https://www.ziekenhuis.nl\"")
        sys.exit(1)
        
    hospital_name = sys.argv[1]
    base_url = sys.argv[2]
    
    print(f"\n--- ZorgNieuws Auto-Discovery: {hospital_name} ---")
    news_url = discover_news_url(base_url)
    
    if not news_url:
        print("Could not find a news URL automatically. Please provide it manually.")
        sys.exit(1)
        
    config_entry = analyze_with_ai(hospital_name, news_url)
    
    if config_entry:
        print("\n✅ Auto-Discovery Succesvol! Voeg dit blok toe aan je config.py:\n")
        print(json.dumps(config_entry, indent=4))
    else:
        print("\n❌ AI analyse is helaas mislukt.")
        
if __name__ == "__main__":
    main()
