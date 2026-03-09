import sqlite3
from pathlib import Path

# Gebruik exact hetzelfde pad als database.py
db_path = Path('d:/Stackstorage/antigravity/nieuwsfeed/.tmp/newsfeed.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

hospitals = ["CWZ", "ETZ", "Franciscus Gasthuis & Vlietland", "Gelre Ziekenhuizen"]

print("--- DB Counts for STZ Batch 1 ---")
for h in hospitals:
    cursor.execute("SELECT COUNT(*) FROM articles WHERE hospital_name = ?", (h,))
    count = cursor.fetchone()[0]
    print(f"{h}: {count} articles")
    if count > 0:
        cursor.execute("SELECT title, date_published, url FROM articles WHERE hospital_name = ? ORDER BY date_published DESC LIMIT 1", (h,))
        title, date, url = cursor.fetchone()
        print(f"  Latest: [{date}] {title[:60]}...")
        print(f"  URL: {url}")

conn.close()
