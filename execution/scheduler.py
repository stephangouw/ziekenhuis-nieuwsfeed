import time
import schedule
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add parent dir to path to import components
sys.path.append(str(Path(__file__).parent.parent))
from execution.scraper_engine import run_scrapers
from execution.ai_processor import process_articles

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def job():
    """The main job that fetches news and then processes it with AI."""
    logger.info("Starting scheduled newsfeed update cycle.")
    try:
        # Step 1: Scrape all hospitals based on config
        run_scrapers()
        
        # Step 2: Use AI to summarize and tag new articles
        process_articles()
        
        logger.info("Completed scheduled newsfeed update cycle successfully.")
    except Exception as e:
        logger.error(f"Error during scheduled job: {e}")

def main():
    logger.info("Newsfeed Scheduler Started. Running 4 times a day (every 6 hours).")
    
    # Run once immediately on startup
    logger.info("Executing initial run...")
    job()
    
    # Schedule to run every 6 hours
    schedule.every(6).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Wait one minute before checking schedule again

if __name__ == "__main__":
    main()
