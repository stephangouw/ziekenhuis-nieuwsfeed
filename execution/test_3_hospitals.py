import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.append(str(Path(__file__).parent.parent))
from execution.advanced_crawler import process_portal, try_fetch_rss, process_rss, process_portal_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

cutoff = datetime.now() - timedelta(days=180)

def test_hospitals():
    # Zuyderland (Website - Playwright needed for Load More)
    logger.info("=== Testing Zuyderland ===")
    if not process_portal_playwright("Zuyderland", "mProve", "https://www.zuyderland.nl/nieuws/", cutoff):
        logger.warning("No articles found for Zuyderland fallback...")
        
    # Isala (Website - curl_cffi fallback needed for Cloudflare)
    logger.info("=== Testing Isala (Website) ===")
    process_portal("Isala", "mProve", "https://www.isala.nl/nieuws/", cutoff)
    
    # Elkerliek (Website - Filters)
    logger.info("=== Testing Elkerliek Ziekenhuis (Website) ===")
    process_portal("Elkerliek Ziekenhuis", "Brainport", "https://www.elkerliek.nl/nieuws-overzicht", cutoff)

if __name__ == "__main__":
    test_hospitals()
