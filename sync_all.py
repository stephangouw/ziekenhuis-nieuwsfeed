import os
import subprocess
import sys
import logging
import json
import sqlite3
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_script(script_path):
    """Runs a python script as a subprocess and streams output."""
    logger.info(f"STARTING: {script_path}")
    
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    # Stream output in real-time
    for line in process.stdout:
        print(line, end='', flush=True)
        # We don't log every line to sync.log to keep it clean, 
        # but the critical ones will be there from the scripts themselves if they log to file.
        
    process.wait()
    
    if process.returncode == 0:
        logger.info(f"FINISHED: {script_path}")
        return True
    else:
        logger.error(f"FAILED: {script_path} (Exit code: {process.returncode})")
        return False

def export_to_json():
    """Exports synchronized articles to data.json for the frontend."""
    logger.info("📤 Exporting database to data.json...")
    
    db_path = Path(__file__).parent / ".tmp" / "newsfeed.db"
    output_path = Path(__file__).parent / "frontend-design" / "data.json"
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get summarized articles from the last 50 days
        query = '''
            SELECT hospital_name, network, title, url, date_published, ai_summary, tags 
            FROM articles 
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
            AND date(date_published) >= date('now', '-50 days')
            ORDER BY date_published DESC
        '''
        cursor.execute(query)
        articles = [dict(row) for row in cursor.fetchall()]
        
        # Parse tags from string back to list
        for art in articles:
            if art['tags']:
                art['tags'] = json.loads(art['tags']) if art['tags'].startswith('[') else art['tags'].split(',')
        
        data = {"articles": articles}
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"✅ Exported {len(articles)} articles to {output_path}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to export: {e}")

def main():
    root_dir = Path(__file__).parent
    crawler_script = root_dir / "execution" / "advanced_crawler.py"
    ai_script = root_dir / "execution" / "ai_processor.py"
    
    logger.info("=== 🔄 STARTING FULL SYNC && AI UPDATE ===")
    
    # 1. Run Crawler
    if not run_script(crawler_script):
        logger.warning("Crawler had errors, but proceeding to AI processing...")
        
    # 2. Run AI Processor
    if not run_script(ai_script):
        logger.error("AI Processor failed. Skipping export.")
        return
        
    # 3. Export to JSON
    export_to_json()
    
    logger.info("=== ✨ FULL SYNC COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
