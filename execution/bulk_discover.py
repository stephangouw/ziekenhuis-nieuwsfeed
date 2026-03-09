import time
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from execution.auto_discover import discover_news_url, analyze_with_ai
from execution.auto_discover import discover_news_url, analyze_with_ai
from execution.config import load_config, save_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# A subset of hospitals to bulk-onboard as a demonstration for the user
HOSPITALS_TO_ADD = [
    {
        "network": "NFU",
        "name": "Amsterdam UMC",
        "url": "https://www.amsterdamumc.org"
    },
    {
        "network": "NFU",
        "name": "Erasmus MC",
        "url": "https://www.erasmusmc.nl"
    },
    {
        "network": "STZ",
        "name": "Deventer Ziekenhuis",
        "url": "https://www.dz.nl"
    },
    {
        "network": "STZ",
        "name": "Sint Antonius Ziekenhuis",
        "url": "https://www.antoniusziekenhuis.nl"
    }
]

def main():
    config = load_config()
    
    for hospital in HOSPITALS_TO_ADD:
        network = hospital["network"]
        name = hospital["name"]
        base_url = hospital["url"]
        
        # Check if already exists to prevent duplicates
        if network in config["networks"]:
            existing = [h["name"] for h in config["networks"][network].get("hospitals", [])]
            if name in existing:
                logger.info(f"Skipping {name}, already in config.")
                continue
                
        logger.info(f"--- Bulk Processing: {name} ({network}) ---")
        
        news_url = discover_news_url(base_url)
        if not news_url:
            logger.warning(f"Could not discover news URL for {name}. Skipping.")
            continue
            
        time.sleep(2) # rate limit prevention for Gemini/Sites
        new_entry = analyze_with_ai(name, news_url)
        
        if new_entry:
            # Enforce network container
            if network not in config["networks"]:
                config["networks"][network] = {"hospitals": []}
            if "hospitals" not in config["networks"][network]:
                config["networks"][network]["hospitals"] = []
                
            config["networks"][network]["hospitals"].append(new_entry)
            save_config(config)
            logger.info(f"Successfully added {name} to {network} config.")
        else:
            logger.error(f"Failed to analyze {name}.")
            
        time.sleep(5) # Give Gemini a breather between requests

    logger.info("Bulk discovery completed.")

if __name__ == "__main__":
    main()
