import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import dateparser

try:
    from curl_cffi import requests as c_requests
except ImportError:
    c_requests = None

# Add parent dir to path to import database and config
sys.path.append(str(Path(__file__).parent.parent))
from execution.database import insert_article, get_connection
from execution.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Stap 1: Blacklisting (Uitsluitingen)
BLACKLIST = [
    '/english/', '/polski/', 'lang=en', 
    '/patienten/', '/aandoeningen/', '/behandelingen/', '/specialismen/', 
    '/contact/', '/over-ons/', '/werken-bij/', '/bereikbaarheid/', 
    '/stichting/', '/vrienden-van/', '/vacatures/', '/agenda/',
    '/folders', '/locaties', '/verhalen/', 'cookie-policy', 'sitemap', 
    '/translate', '/mijn', '/zorglocaties/', '/opleiding/', '/ggz/',
    'algemene-voorwaarden', 'disclaimer', 'privacy', 'login', '/faq/',
    '/praktische-informatie/', '/patientinformatie/', '/ziekenhuis/',
    '/specialisme/', '/behandeling/', '/onderzoek/', '/afdeling/',
    '/locatie/', '/clientondersteuning/', '/verpleegafdeling/',
    'ziekenhuishulp', 'waar-staan-we-voor', 'kwaliteit', 'klachten',
    'cookies', 'cookieverklaring', 'google-translate', 'disclaimer',
    'voor-verwijzers', 'toegangstijden', 'vergoeding', 'rechten-en-plichten'
]

def is_valid_url(url):
    url_lower = url.lower()
    for bad in BLACKLIST:
        if bad in url_lower:
            return False
            
    # Specifieke uitsluitingen voor categorie/overzicht pagina's ipv artikelen
    path_parts = [p for p in urlparse(url).path.split('/') if p]
    slug = path_parts[-1] if path_parts else ''
    if slug.isdigit() and len(slug) == 4: # bijv. /2026
        return False
    if 'overzicht' in slug or slug == 'nieuws' or slug == 'actueel':
        return False
        
    return True

def is_article_url(url, portal_url, base_domain):
    parsed = urlparse(url)
    
    # Strip www. for comparison
    clean_netloc = parsed.netloc.replace('www.', '')
    clean_base = base_domain.replace('www.', '')
    
    if clean_netloc != clean_base or url == portal_url:
        return False
        
    path_parts = [p for p in parsed.path.split('/') if p]
    slug = path_parts[-1] if path_parts else ''
    
    # --- HOSPITAAL-SPECIFIEKE REGELS (HOGE PRIORITEIT) ---
        
    # Zuyderland nieuws MOET onder /nieuws/ staan om patientinfo te vermijden
    if 'zuyderland.nl' in url.lower():
        if 'https://zuyderland.nl/nieuws/' in url or 'https://www.zuyderland.nl/nieuws/' in url:
            return True
        return False
        
    # Elkerliek nieuws MOET onder /nieuws-overzicht/ staan om patientinfo/horeca te vermijden
    if 'elkerliek.nl' in url.lower():
        if '/nieuws-overzicht/' in url:
            return True
        return False
        
    # Noordwest Ziekenhuisgroep nieuws MOET onder /nieuwsoverzicht-pagina/ staan
    if 'nwz.nl' in url.lower():
        if '/nieuwsoverzicht-pagina/' in url and len(url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]) > 10:
            if not any(x in url.lower() for x in ['afdelingen-overzicht', 'zorgverleners', 'bezoekers', 'werken-en', 'over-ons', 'contact', 'vrienden-van']):
                return True
        return False
        
    # Rijnstate nieuws MOET onder /over-rijnstate/nieuws/ of /nieuws/ staan
    if 'rijnstate.nl' in url.lower():
        if '/over-rijnstate/nieuws/' in url or '/nieuws/' in url:
            return True
        return False
        
    # ASZ nieuws MOET onder /nieuws/nieuwsberichten/ staan (niet de base portal)
    if 'asz.nl' in url.lower():
        if '/nieuws/nieuwsberichten/' in url and len(url) > len('https://www.asz.nl/nieuws/nieuwsberichten/') + 5:
            return True
        return False
        
    # JBZ nieuws MOET onder /nieuws/ staan en lang genoeg zijn (om "/nieuws?page=1" uit te sluiten)
    if 'jeroenboschziekenhuis.nl' in url.lower():
        if '/nieuws/' in url and len(url) > len('https://www.jeroenboschziekenhuis.nl/nieuws/') + 5:
            if '?page=' not in url:
                return True
        return False
        
    # SJG Weert nieuws MOET onder /actueel/nieuws/ staan
    if 'sjgweert.nl' in url.lower():
        if '/actueel/nieuws/' in url and len(url) > len('https://www.sjgweert.nl/actueel/nieuws/') + 5:
            return True
        return False

    # Anna Ziekenhuis nieuws MOET onder /nieuws/ staan
    if 'annaziekenhuis.nl' in url.lower():
        if '/nieuws/' in url and len(url) > len('https://www.annaziekenhuis.nl/nieuws/') + 5:
            return True
        return False

    # Amsterdam UMC
    if 'amsterdamumc.org' in url.lower():
        if ('/vandaag/' in url or '/nieuws/' in url) and (len(slug) > 10 or '?' in url):
            return True
        return False

    # Erasmus MC
    if 'erasmusmc.nl' in url.lower():
        if '/artikelen/' in url and len(slug) > 10:
            return True
        return False

    # MUMC+
    if 'mumc.nl' in url.lower():
        if '/actueel/nieuws/' in url and len(slug) > 10:
            return True
        return False

    # Radboudumc & UMCG
    if 'radboudumc.nl' in url.lower() or 'umcg.nl' in url.lower():
        if '/nieuws/' in url and len(slug) > 10:
            return True
        return False

    # CWZ
    if 'cwz.nl' in url.lower():
        if '/nieuws/' in url and len(slug) > 10:
            return True
        return False

    # Franciscus
    if 'franciscus.nl' in url.lower():
        if '/nieuws/' in url and len(slug) > 10:
            return True
        return False

    # ETZ
    if 'etz.nl' in url.lower():
        if '/actueel/' in url and len(slug) > 10:
            return True
        return False

    # Gelre & Haga (Both use ?urile=wcm:path%3A%2Factueel...)
    if 'gelreziekenhuizen.nl' in url.lower() or 'hagaziekenhuis.nl' in url.lower():
        if '?urile=' in url and ('actueel' in url or 'nieuws' in url):
            return True
        # Haga also has normal /nieuws/ links sometimes
        if '/nieuws/' in url and len(slug) > 10 and 'hagaziekenhuis' in url.lower():
            return True
        return False

    # Martini Ziekenhuis
    if 'martiniziekenhuis.nl' in url.lower():
        if ('/nieuws/' in url or '/nieuws-ontwikkelingen/' in url) and len(slug) > 10:
            return True
        return False

    # HMC, Maasstad
    if any(domain in url.lower() for domain in ['haaglandenmc.nl', 'maasstadziekenhuis.nl']):
        if '/nieuws/' in url and len(slug) > 10:
            return True
        return False

    # Meander MC
    if 'meandermc.nl' in url.lower():
        if '/nieuws/' in url and (len(slug) > 10 or '?urile=' in url):
            return True
        return False

    # --- ALGEMENE HEURISTIEK ---
    
    has_seo_slug = '-' in slug and len(slug) > 12 # bijv. "isala-opent-nieuw-gebouw"
    has_id_slug = slug.isdigit() and len(slug) >= 4 # bijv. "/nieuws/123049"
    has_date_path = bool(re.search(r'/\d{4}/\d{2}/', url))
    
    if has_seo_slug or has_id_slug or has_date_path:
        if 'nieuws' in url.lower() or 'actueel' in url.lower():
            return True
        if url.startswith(portal_url) and len(url) > len(portal_url) + 5:
            return True
        # Slimme heuristiek: echte nieuwsberichten hebben vaak volledige zinnen als slug (veel streepjes)
        if slug.count('-') >= 3 and len(slug) > 20:
            bad_path_keywords = ['voorwaarden', 'disclaimer', 'privacy', 'folder', 'locatie', 'agenda']
            if not any(x in url.lower() for x in bad_path_keywords):
                return True
                
    # St. Antonius nieuws MOET onder /nieuwsoverzicht/ staan
    if 'antoniusziekenhuis.nl' in url.lower():
        if '/nieuwsoverzicht/' in url:
            # Vermijd de overzichtspagina zelf en algemene service links
            if url.rstrip('/') == 'https://www.antoniusziekenhuis.nl/nieuwsoverzicht':
                return False
            # Artikelen hebben meestal een diepere slug
            return len(parsed.path.rstrip('/').split('/')) >= 3
        return False

    return False

def clean_dutch_date(date_str):
    if not date_str:
        return None
    date_str = date_str.lower().strip()
    
    # Custom fallback voor relatieve datums ("3 weken geleden")
    rel_match = re.search(r'(\d+)\s+(uur|uren|dag|dagen|week|weken|maand|maanden)\s+geleden', date_str)
    if rel_match:
        amount = int(rel_match.group(1))
        unit = rel_match.group(2)
        if 'uur' in unit or 'uren' in unit:
             return (datetime.now() - timedelta(hours=amount)).strftime('%Y-%m-%d')
        if 'dag' in unit:
             return (datetime.now() - timedelta(days=amount)).strftime('%Y-%m-%d')
        elif 'week' in unit or 'weken' in unit:
             return (datetime.now() - timedelta(weeks=amount)).strftime('%Y-%m-%d')
        elif 'maand' in unit:
             return (datetime.now() - timedelta(days=amount*30)).strftime('%Y-%m-%d')

    # Gebruik dateparser als primaire robuuste engine (Forceer DMY voor NL sites)
    dt = dateparser.parse(date_str, languages=['nl', 'en'], settings={'DATE_ORDER': 'DMY'})
    if dt:
        return dt.strftime("%Y-%m-%d")
        
    match = re.search(r'(\d{1,2})[\s\.\-/]+(\w+|\d{1,2})[\s\.\-/]+(\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        if month.isdigit():
            try:
                return f"{year}-{int(month):02d}-{int(day):02d}"
            except: pass
        else:
            months = {'jan': 1, 'feb': 2, 'maa': 3, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12}
            for m_str, m_num in months.items():
                if m_str in month:
                    return f"{year}-{m_num:02d}-{int(day):02d}"
    return None

def extract_date_from_deep(soup, article_url=None):
    # 1. Bekende tags
    time_tag = soup.find('time')
    if time_tag:
         return clean_dutch_date(time_tag.get_text(strip=True))
         
    # 2. Hospitaal-specifieke selectors
    # Isala meta header: "Gepubliceerd op: 04-03-2026"
    if article_url and 'isala.nl' in str(article_url):
        meta = soup.select_one('.c-pageheader__intro__meta')
        if meta:
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', meta.get_text())
            if date_match:
                return date_match.group(1)

    # Martini specific logic
    if article_url and 'martiniziekenhuis.nl' in str(article_url):
        date_el = soup.select_one('.c-news__item__date, .news-detail__date, time')
        if date_el:
            text = date_el.get_text(strip=True)
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', text)
            if date_match:
                return date_match.group(1)

    # Meander MC specific logic
    if article_url and 'meandermc.nl' in str(article_url):
        date_el = soup.select_one('span.date, .card span, .meta-info span')
        if date_el:
            return clean_dutch_date(date_el.get_text(strip=True))

    # Elkerliek cards or article meta
    if article_url and 'elkerliek.nl' in str(article_url):
        # In article: often in a bold tag, strong tag, or paragraph with a date pattern
        # Elkerliek format: "3 maart 2026"
        for tag in soup.find_all(['strong', 'p', 'span', 'h2']):
            text = tag.get_text(strip=True)
            if re.search(r'\d{1,2}\s+(jan|feb|maa|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)', text.lower()):
                 return clean_dutch_date(text)
        # Fallback: check early paragraphs
        for p in soup.find_all('p')[:5]:
             text = p.get_text(strip=True)
             if re.search(r'\d{1,2}\s+(jan|feb|maa|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)', text.lower()):
                 return clean_dutch_date(text)

    # ASZ specific: embedded in first paragraph "Dordrecht, 31 oktober 2024 - " or URL fallback
    if article_url and 'asz.nl' in str(article_url):
        for p in soup.find_all('p')[:3]:
            text = p.get_text(strip=True).lower()
            if re.search(r'\d{1,2}[\s\.\-]+(jan|feb|maa|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)[^\d]{0,5}\d{4}', text):
                parsed = clean_dutch_date(text)
                if parsed: return parsed
                
        match = re.search(r'/(\d{4})/(\d{1,2})/\d+/', article_url)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-01"

    # 3. Zoeken in spans/paragraphs (Generiek)
    for span in soup.find_all(['span', 'p']):
        text = span.get_text(strip=True).lower()
        if len(text) < 40 and re.search(r'\d{1,2} (jan|feb|maa|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)', text):
             return clean_dutch_date(text)
             
    # 4. Try to extract from URL if present (e.g. /2026/03/08/...)
    if article_url:
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', article_url)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            
    return None

def get_h1_or_title(soup):
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    title = soup.find('title')
    if title:
        return title.get_text(strip=True).split('|')[0].split('-')[0].strip()
    return "Nieuwsbericht"

def get_first_paragraph(soup):
    boilerplate_keywords = ['cookie', 'browser', 'internet explorer', 'privacy', 'akkoord', 'instellingen']
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 80:
            if not any(k in text.lower() for k in boilerplate_keywords):
                return text
    return "Lees het volledige artikel op de website van het ziekenhuis."

# --- RSS LOGICA ---
def try_fetch_rss(portal_url):
    parsed = urlparse(portal_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    candidates = [
        portal_url if portal_url.endswith(('rss', 'feed', 'xml')) else None,
        urljoin(base_url, '/rss'),
        urljoin(base_url, '/feed'),
        urljoin(portal_url, 'feed/'),
        urljoin(portal_url, 'rss/')
    ]
    candidates = list(dict.fromkeys([c for c in candidates if c]))
    
    # Check endpoints first
    for url in candidates:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            if 'xml' in resp.headers.get('Content-Type', '') or '<rss' in resp.text[:200] or '<feed' in resp.text[:200]:
                return url, resp.content
        except Exception:
            pass
            
    # Parse HTML head to find alternate RSS link
    try:
        resp = requests.get(portal_url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        link = soup.find('link', type='application/rss+xml')
        if link and link.get('href'):
            rss_url = urljoin(portal_url, link.get('href'))
            r_resp = requests.get(rss_url, headers=HEADERS, timeout=5)
            if 'xml' in r_resp.headers.get('Content-Type', '') or '<rss' in r_resp.text[:200] or '<feed' in r_resp.text[:200]:
                return rss_url, r_resp.content
    except Exception:
        pass
        
    return None, None

def process_rss(hospital_name, network_name, rss_xml_bytes, cutoff_date):
    logger.info(f"   📡 [RSS Gevonden] Verwerk items via RSS feed...")
    try:
        root = ET.fromstring(rss_xml_bytes)
    except ET.ParseError as e:
        logger.error(f"   ❌ Fout bij parsen XML: {e}")
        return 0, False
        
    total_processed = 0
    items = root.findall('.//item')
    if not items:
        # Probeer namespaces te omzeilen door naar alle tags te zoeken die eindigen op 'item'
        items = [el for el in root.iter() if el.tag.endswith('item')]
        
    if not items:
        # Misschien ATOM format? proberen we `<entry>`
        items = [el for el in root.iter() if el.tag.endswith('entry')]
        
    for item in items:
        title = item.findtext('title')
        link = item.findtext('link')
        pub_date_str = item.findtext('pubDate') or item.findtext('{http://purl.org/dc/elements/1.1/}date')
        
        if not title or not link:
            continue
            
        dt = dateparser.parse(pub_date_str, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': False}) if pub_date_str else datetime.now()
        if dt and dt < cutoff_date:
            logger.info(f"   🛑 6-maanden limiet bereikt ({dt.strftime('%Y-%m-%d')}). Stopt met RDF/RSS traversal.")
            break
            
        pub_date_formatted = dt.strftime("%Y-%m-%d") if dt else datetime.now().strftime("%Y-%m-%d")
        
        # Verwerk samenvatting (zonder Bron label)
        summary = (item.findtext('description') or "Lees het artikel online.")
        summary = BeautifulSoup(summary, 'html.parser').get_text(strip=True)[:400]

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT date_published FROM articles WHERE url = ?", (link,))
            row = cursor.fetchone()
            
            if not row:
                insert_success = insert_article(hospital_name, network_name, title, link, pub_date_formatted, original_content=summary)
                if insert_success:
                    c = conn.cursor()
                    c.execute("""
                        UPDATE articles 
                        SET ai_summary = ?, tags = '["' || ? || '", "Nieuws"]'
                        WHERE url = ?
                    """, (summary, network_name, link))
                    conn.commit()
                    total_processed += 1
            conn.close()
        except Exception as e:
            logger.warning(f"DB Error for {link}: {e}")
            
    logger.info(f"✅ Afgerond {hospital_name} via RSS: {total_processed} nieuwe artikelen binnen 6 maanden toegevoegd.")
    return total_processed, True


# --- PORTAL LOGICA (Fallback) ---
def get_next_page_url(soup, current_url):
    # Detecteer dynamische 'Laad meer' of 'Toon meer' knoppen (AJAX/JS block)
    load_more = soup.find(string=re.compile(r'laad meer|toon meer|meer nieuws|bekijk meer', re.I))
    if load_more:
        parent = load_more.find_parent(['a', 'button'])
        if parent:
            href = parent.get('href', '')
            if not href or href.startswith('javascript:') or href == '#':
                logger.warning(f"   ⚠️ Dynamische 'Laad meer' knop gedetecteerd. Paginering stopt hier (Headless API vereist).")
                return None

    next_link = soup.find('a', attrs={'rel': 'next'})
    if next_link and next_link.get('href'):
        return urljoin(current_url, next_link.get('href'))
        
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True).lower()
        if text in ['volgende', 'next', 'volgende pagina', 'volgende >', '>', '&raquo;', '»']:
            href = a['href']
            if not href.startswith('javascript:'):
                return urljoin(current_url, href)
            
    next_btn = soup.find('a', class_=re.compile(r'next|volgende|pagination', re.I))
    if next_btn and next_btn.get('href'):
        href = next_btn.get('href')
        if 'page' in href or 'p=' in href or 'offset' in href or re.search(r'/\d+/?$', href):
            return urljoin(current_url, href)
            
    parsed = urlparse(current_url)
    qs = parse_qs(parsed.query)
    for key in ['page', 'p']:
        if key in qs:
            try:
                val = int(qs[key][0])
                qs[key] = [str(val + 1)]
                new_query = urlencode(qs, doseq=True)
                return urlunparse(parsed._replace(query=new_query))
            except ValueError:
                pass
                
    match = re.search(r'/page/(\d+)/?$', parsed.path)
    if match:
        next_path = parsed.path.replace(f"/page/{match.group(1)}", f"/page/{int(match.group(1)) + 1}")
        return urlunparse(parsed._replace(path=next_path))
        
    return None

def process_portal(hospital_name, network_name, portal_url, cutoff_date):
    logger.info(f"   🌐 [Fallback Website] Crawling Portal: {hospital_name} -> {portal_url}")
    
    current_url = portal_url
    seen_articles = set()
    total_processed = 0
    page_count = 0
    max_pages = 25 
    
    while current_url and page_count < max_pages:
        page_count += 1
        logger.info(f"   📄 Paginering {page_count}: {current_url}")
        
        try:
            resp = requests.get(current_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            
            # Anti-bot detection (e.g. Isala or Martini block pages)
            is_blocked = ('cloudflare' in resp.text.lower() or 'browser' in resp.text.lower() or 
                         'isala.nl' in current_url or 'martiniziekenhuis.nl' in current_url or 
                         'web page blocked' in resp.text.lower() or 'attack id:' in resp.text.lower())
            
            if is_blocked and len(resp.text) < 150000: # WAF pages are usually small
                 logger.warning(f"   🚫 Anti-bot firewall / JS-challenge gedetecteerd. Poging tot bypass via curl_cffi TLS impersonation...")
                 if c_requests:
                     resp = c_requests.get(current_url, impersonate="chrome110", timeout=15)
                 else:
                     logger.error("   ❌ curl_cffi niet geïnstalleerd. Paginering afgebroken (Headless API vereist).")
                     break
                 
        except requests.RequestException as e:
            logger.error(f"   ❌ Failed to fetch {current_url}: {e}")
            break
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        base_domain = urlparse(portal_url).netloc
        
        article_links_on_page = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(current_url, href)
            
            if not is_valid_url(full_url):
                continue
                
            if is_article_url(full_url, portal_url, base_domain):
                 # Verwijder over-agressieve '?' check, want Isala gebruikt dit voor context
                 if not any(x in href.lower() for x in ['.pdf', 'mailto:', 'page=', '?p=', '#', 'filter=', 'sort=']):
                     if full_url not in seen_articles:
                         article_links_on_page.append(full_url)
                         seen_articles.add(full_url)
                             
        if not article_links_on_page:
            logger.info("   ⚠️ Geen nieuwe artikellinks gevonden op deze pagina.")
            break
            
        page_oldest_date = None
        
        for article_url in article_links_on_page:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT date_published FROM articles WHERE url = ?", (article_url,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    pub_date_str = row[0]
                else:
                    time.sleep(1)
                    art_resp = requests.get(article_url, headers=HEADERS, timeout=10)
                    if len(art_resp.text) < 3000 and c_requests:
                        art_resp = c_requests.get(article_url, impersonate="chrome110", timeout=15)
                        
                    art_soup = BeautifulSoup(art_resp.text, 'html.parser')
                    
                    title = get_h1_or_title(art_soup)
                    summary = get_first_paragraph(art_soup)
                    pub_date_str = extract_date_from_deep(art_soup, article_url)
                    
                    if not pub_date_str:
                        pub_date_str = datetime.now().strftime("%Y-%m-%d")
                        
                    is_too_old = False
                    try:
                        if datetime.strptime(pub_date_str, "%Y-%m-%d") < cutoff_date:
                            is_too_old = True
                    except ValueError: pass
                    
                    if not is_too_old:
                        insert_success = insert_article(hospital_name, network_name, title, article_url, pub_date_str, original_content=summary)
                        if insert_success:
                            conn = get_connection()
                            c = conn.cursor()
                            c.execute("""
                                UPDATE articles 
                                SET ai_summary = ?, tags = '["' || ? || '", "Nieuws"]'
                                WHERE url = ?
                            """, (summary, network_name, article_url))
                            conn.commit()
                            conn.close()
                            total_processed += 1
                        
                if pub_date_str:
                    try:
                        dt = datetime.strptime(pub_date_str, "%Y-%m-%d")
                        if page_oldest_date is None or dt < page_oldest_date:
                            page_oldest_date = dt
                    except ValueError:
                        pass
                        
            except Exception as e:
                logger.warning(f"   ⚠️ Fout bij ophalen artikel {article_url}: {e}")
                
        if page_oldest_date and page_oldest_date < cutoff_date:
            logger.info(f"   🛑 6-maanden limiet bereikt ({page_oldest_date.strftime('%Y-%m-%d')}). Stopt met pagineren.")
            break
            
        time.sleep(3) 
        next_url = get_next_page_url(soup, current_url)
        if next_url and next_url != current_url:
            current_url = next_url
        else:
            logger.info("   🚫 Geen 'Volgende' pagina of patroon meer gevonden.")
            break

    logger.info(f"✅ Afgerond {hospital_name}: {total_processed} nieuwe artikelen binnen 6 maanden toegevoegd.")
    return total_processed

# --- PORTAL LOGICA (Playwright Fallback) ---
def process_portal_playwright(hospital, network_name, portal_url, cutoff_date):
    hospital_name = hospital["name"]
    logger.info(f"   🤖 [Playwright Headless] Crawling Portal: {hospital_name} -> {portal_url}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("   ❌ Playwright is niet geïnstalleerd.")
        return 0
        
    total_processed = 0
    seen_articles = set()
    base_domain = urlparse(portal_url).netloc
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS['User-Agent'], viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # Handle cookie walls and anti-bot layers
            page.goto(portal_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Generieke Cookie Acceptatie (werkt voor meeste NL sites)
            cookie_selectors = [
                "button:has-text('Akkoord')", 
                "button:has-text('Accepteer')", 
                "button:has-text('Cookies accepteren')", 
                "button:has-text('Alle cookies')",
                "button#acc-agree",
                "a:has-text('Akkoord')",
                "a.cc-btn.cc-allow"
            ]
            
            for selector in cookie_selectors:
                try:
                    btn = page.query_selector(selector)
                    if btn and btn.is_visible():
                        logger.info(f"   🍪 Klikken op cookie button: {selector}")
                        btn.click()
                        page.wait_for_timeout(1500)
                        break # Meestal 1 knop genoeg
                except:
                    continue
                
            # Specifieke wait acties per ziekenhuis
            if hospital_name == 'Rijnstate':
                try:
                    page.wait_for_selector("a[href*='/nieuws/']", timeout=10000)
                except: pass
                        
        except Exception as e:
            logger.error(f"   ❌ Failed to load {portal_url}: {e}")
            browser.close()
            return 0
            
        page_count = 0
        while page_count < 15: # Limiet
            page_count += 1
            logger.info(f"   📄 Playwright Iteration {page_count}...")
            
            # Wacht 2 seconden om tegels / AJAX de tijd te geven
            page.wait_for_timeout(2000)
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            article_links_on_page = []
            article_selector = hospital.get("selectors", {}).get("article")
            if article_selector:
                 # If the article selector itself is an <a> tag, use its href. Otherwise search for <a> inside.
                 elements = soup.select(article_selector)
                 links = []
                 for el in elements:
                     if el.name == 'a' and el.get('href'):
                         links.append(el.get('href'))
                     elif el.find('a', href=True):
                         links.append(el.find('a', href=True).get('href'))
            else:
                 links = [a['href'] for a in soup.find_all('a', href=True)]

            for href in links:
                full_url = urljoin(page.url, href)
                    
                if is_article_url(full_url, portal_url, base_domain):
                    # Verwijder over-agressieve '?' check (maar behoud PDF/Mailto)
                    if not any(x in href.lower() for x in ['.pdf', 'mailto:', 'filter=', 'sort=']):
                        if full_url not in seen_articles:
                            article_links_on_page.append(full_url)
                            seen_articles.add(full_url)
                            
            if not article_links_on_page:
                logger.info("   ⚠️ Geen artikellinks gevonden op deze view.")
                break
                
            page_oldest_date = None
            
            for article_url in article_links_on_page:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT date_published FROM articles WHERE url = ?", (article_url,))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row:
                        pub_date_str = row[0]
                    else:
                        art_page = context.new_page()
                        try:
                            art_page.goto(article_url, wait_until="domcontentloaded", timeout=15000)
                            art_soup = BeautifulSoup(art_page.content(), 'html.parser')
                        except Exception:
                            art_soup = BeautifulSoup("<html></html>", 'html.parser')
                        finally:
                            art_page.close()
                            
                        title = get_h1_or_title(art_soup)
                        summary = get_first_paragraph(art_soup)
                        pub_date_str = extract_date_from_deep(art_soup, article_url)
                        
                        if not pub_date_str:
                            pub_date_str = datetime.now().strftime("%Y-%m-%d")
                            
                        is_too_old = False
                        try:
                            if datetime.strptime(pub_date_str, "%Y-%m-%d") < cutoff_date:
                                is_too_old = True
                        except ValueError: pass
                        
                        if not is_too_old:
                            insert_success = insert_article(hospital_name, network_name, title, article_url, pub_date_str, original_content=summary)
                            if insert_success:
                                conn = get_connection()
                                c = conn.cursor()
                                c.execute("""
                                    UPDATE articles 
                                    SET ai_summary = ?, tags = '["' || ? || '", "Nieuws"]'
                                    WHERE url = ?
                                """, (summary, network_name, article_url))
                                conn.commit()
                                conn.close()
                                total_processed += 1
                            
                    if pub_date_str:
                        try:
                            dt = datetime.strptime(pub_date_str, "%Y-%m-%d")
                            if page_oldest_date is None or dt < page_oldest_date:
                                page_oldest_date = dt
                        except ValueError: pass
                except Exception as e:
                    logger.warning(f"   ⚠️ Fout bij ophalen {article_url}: {e}")
                    
            if page_oldest_date and page_oldest_date < cutoff_date:
                logger.info(f"   🛑 6-maanden limiet bereikt ({page_oldest_date.strftime('%Y-%m-%d')}). Stopt met pagineren.")
                break
                
            # Click next / load more
            if hospital_name == 'Zuyderland':
                try:
                    load_more_btn = page.query_selector("a.ajax-load-more, a:has-text('Toon meer'), button:has-text('Laad meer')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Isala':
                try:
                    next_btn = page.query_selector("a.next, a:has-text('Volgende'), a:has-text('Next')")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Noordwest Ziekenhuisgroep':
                try:
                    next_page_num = page_count + 1
                    next_btn = page.query_selector(f"button:has-text('{next_page_num}')")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)  # Next.js SPA hydrate time
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Rijnstate':
                try:
                    load_more_btn = page.query_selector("button:has-text('meer nieuwsberichten'), a:has-text('meer nieuwsberichten')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(2000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Albert Schweitzer':
                try:
                    # In de test zagen we class="volgende" of nummers, Playwright test toonde geen expliciete knop in de log, maar we zoeken naar de standaard a href
                    load_more_btn = page.query_selector("a.volgende, button:has-text('meer'), a:has-text('Ouder bericht'), a:has-text('Volgende')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(2000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Jeroen Bosch Ziekenhuis':
                try:
                    load_more_btn = page.query_selector("a[href*='?page='], a:has-text('Volgende')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'St. Anna Ziekenhuis':
                try:
                    load_more_btn = page.query_selector("a.paging__next")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'SJG Weert':
                try:
                    load_more_btn = page.query_selector(".pager__item--next a")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Amsterdam UMC':
                try:
                    load_more_btn = page.query_selector(".umc-button.primary:has-text('Meer')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Erasmus MC':
                try:
                    next_btn = page.query_selector("a.pagination__link--next")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'MUMC+':
                try:
                    next_btn = page.query_selector("a[href*='?page='], a:has-text('Volgende')")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Radboudumc':
                try:
                    load_more_btn = page.query_selector("button.js-GridLoadMoreBtn")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'UMCG':
                try:
                    load_more_btn = page.query_selector("a.btn-pagination:has-text('Meer')")
                    if load_more_btn and load_more_btn.is_visible():
                        load_more_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'CWZ':
                try:
                    next_btn = page.query_selector("button[aria-label='Volgende pagina']")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Franciscus Gasthuis & Vlietland':
                try:
                    next_btn = page.query_selector("a[href*='?page='], a:has-text('Volgende'), nav.pager a[title*='pagina']")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'ETZ':
                try:
                    next_btn = page.query_selector("a:has-text('Volgende')")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name in ['HMC', 'Maasstad Ziekenhuis', 'Meander MC']:
                try:
                    next_btn = page.query_selector("a.next, a:has-text('Volgende'), a[href*='?page=']:last-child")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'HagaZiekenhuis':
                try:
                    # Often uses 'Meer nieuws' or 'Volgende' or numbered pagination
                    next_btn = page.query_selector("a:has-text('Volgende'), a:has-text('Meer nieuws'), a.next")
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(3000)
                    else:
                        break
                except Exception: break
            elif hospital_name == 'Martini Ziekenhuis':
                try:
                    # Infinite Scroll: Scroll down and wait for more content
                    prev_height = page.evaluate("document.body.scrollHeight")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(4000)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height <= prev_height:
                        # Try one more time with a longer wait
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(3000)
                        if page.evaluate("document.body.scrollHeight") <= new_height:
                            break
                except Exception as e:
                    logger.warning(f"   ⚠️ Martini scroll error: {e}")
                    break
            else:
                break
                
        browser.close()
        
    logger.info(f"✅ Afgerond {hospital_name} via Playwright: {total_processed} nieuwe artikelen.")
    return total_processed


def run_hybrid_scrapers(specific_network=None):
    config = load_config()
    total = 0
    # Precies 50 dagen geleden (geoptimaliseerd op verzoek)
    cutoff = datetime.now() - timedelta(days=50)
    logger.info(f"🚀 Start Hybride Crawler. Zoekt terug tot uiterlijk: {cutoff.strftime('%Y-%m-%d')}")
    
    for network_name, network_data in config.get("networks", {}).items():
        if specific_network and network_name != specific_network:
            continue
            
        for hospital in network_data.get("hospitals", []):
            portal_url = hospital["url"]
            if hospital["name"] == "Anna Ziekenhuis":
                portal_url = "https://www.annaziekenhuis.nl/nieuws/"
            elif hospital["name"] == "Catharina Ziekenhuis":
                portal_url = "https://www.catharinaziekenhuis.nl/nieuws/"
            elif hospital["name"] == "Elkerliek Ziekenhuis":
                portal_url = "https://www.elkerliek.nl/nieuws-overzicht"
                
            logger.info(f"🔍 Inspecting {hospital['name']} ...")
            
            # 1: Probeer RSS feed
            rss_url, rss_content = try_fetch_rss(portal_url)
            if rss_url and rss_content:
                count, success = process_rss(hospital["name"], network_name, rss_content, cutoff)
                total += count
            elif hospital["name"] in ['Zuyderland', 'Máxima MC', 'Jeroen Bosch Ziekenhuis', 'St. Anna Ziekenhuis', 'SJG Weert', 
                                    'Amsterdam UMC', 'Erasmus MC', 'MUMC+', 'Radboudumc', 'UMCG',
                                    'CWZ', 'ETZ', 'Franciscus Gasthuis & Vlietland', 'Gelre Ziekenhuizen',
                                    'HMC', 'HagaZiekenhuis', 'Maasstad Ziekenhuis', 'Meander MC',
                                    'Amphia Ziekenhuis', 'Deventer Ziekenhuis', 'Martini Ziekenhuis', 'Isala']:
                # 2A: Headless Browser Fallback (Portal met AJAX / Anti-Bot)
                count = process_portal_playwright(hospital, network_name, portal_url, cutoff)
                total += count
            else:
                # 2B: Fallback Web Scraper HTML (Ondersteunt curl_cffi voor Isala)
                count = process_portal(hospital["name"], network_name, portal_url, cutoff)
                total += count
            
    logger.info(f"🎉 Crawler run compleet. Totaal {total} verse artikelen binnen de limiet van 6 maanden.")

if __name__ == "__main__":
    run_hybrid_scrapers()
