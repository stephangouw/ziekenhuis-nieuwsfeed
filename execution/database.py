import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure database is stored in the correct location
DB_DIR = Path(__file__).parent.parent / ".tmp"
DB_PATH = DB_DIR / "newsfeed.db"

def get_connection():
    """Create a database connection to the SQLite database."""
    try:
        if not DB_DIR.exists():
            DB_DIR.mkdir(parents=True)
            
        conn = sqlite3.connect(DB_PATH)
        # Enable foreign keys and row factory
        conn.execute("PRAGMA foreign_keys = 1")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def init_db():
    """Initialize the database schema."""
    logger.info("Initializing database...")
    conn = get_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hospital_name TEXT NOT NULL,
                    network TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    date_published TEXT NOT NULL,
                    original_content TEXT,
                    ai_summary TEXT,
                    tags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create an index on url for faster lookups and duplicate prevention
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_url ON articles (url)')
            
            conn.commit()
            logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
        finally:
            conn.close()

def insert_article(hospital_name, network, title, url, date_published, original_content=""):
    """
    Insert a new article into the database. 
    Returns True if successful or already exists, False on error.
    """
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO articles (hospital_name, network, title, url, date_published, original_content)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (hospital_name, network, title, url, date_published, original_content))
        conn.commit()
        logger.debug(f"Inserted new article: {title}")
        return True
    except sqlite3.IntegrityError:
        # Article with this URL already exists, which is fine
        logger.debug(f"Article already exists in DB: {url}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error inserting article: {e}")
        return False
    finally:
        conn.close()

def get_unsummarized_articles(limit=50):
    """Retrieve articles that don't have an AI summary yet."""
    conn = get_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM articles 
            WHERE ai_summary IS NULL OR ai_summary = ''
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching unsummarized articles: {e}")
        return []
    finally:
        conn.close()

def update_article_ai_data(article_id, summary, tags):
    """Update an article with AI generated summary and tags."""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        # Check if tags is a list, if so convert to JSON string
        if isinstance(tags, list):
            tags_json = json.dumps(tags)
        else:
            tags_json = tags
            
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE articles 
            SET ai_summary = ?, tags = ?
            WHERE id = ?
        ''', (summary, tags_json, article_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating article AI data: {e}")
        return False
    finally:
        conn.close()

def get_recent_articles(networks=None, days=50, limit=100):
    """Get summarized recent articles, optionally filtered by network."""
    conn = get_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        
        query = '''
            SELECT hospital_name, network, title, url, date_published, ai_summary, tags 
            FROM articles 
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
            AND date(date_published) >= date('now', ?)
        '''
        params = [f'-{days} days']
        
        if networks and isinstance(networks, list):
            placeholders = ','.join(['?'] * len(networks))
            query += f' AND network IN ({placeholders})'
            params.extend(networks)
            
        query += ' ORDER BY date_published DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        articles = []
        for row in cursor.fetchall():
            article = dict(row)
            # Parse tags back from JSON
            try:
                if article['tags']:
                    article['tags'] = json.loads(article['tags'])
                else:
                    article['tags'] = []
            except json.JSONDecodeError:
                article['tags'] = []
            articles.append(article)
            
        return articles
    except sqlite3.Error as e:
        logger.error(f"Error fetching recent articles: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    # Test initialization
    init_db()
    print("Database module ready.")
