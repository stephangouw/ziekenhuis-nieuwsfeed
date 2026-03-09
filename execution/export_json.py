import json
import logging
import sys
from pathlib import Path

# Add parent dir to path to import database
sys.path.append(str(Path(__file__).parent.parent))
from execution.database import get_recent_articles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FRONTEND_DATA_FILE = Path(__file__).parent.parent / "frontend-design" / "data.json"

def export_to_json():
    """Fetches articles from DB and exports them to a JSON file for the static frontend."""
    logger.info("Exporting database to JSON...")
    
    # We fetch all processed articles. In a real scenario we could paginate,
    # but for a simple static setup, downloading a few hundred KB json is instantaneous.
    articles = get_recent_articles(limit=500)
    
    # Ensure directory exists
    FRONTEND_DATA_FILE.parent.mkdir(exist_ok=True)
    
    try:
        with open(FRONTEND_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully exported {len(articles)} articles to {FRONTEND_DATA_FILE}")
    except IOError as e:
        logger.error(f"Failed to write JSON file: {e}")

if __name__ == "__main__":
    export_to_json()
