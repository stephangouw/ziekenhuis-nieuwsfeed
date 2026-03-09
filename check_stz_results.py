import sqlite3
import os
from pathlib import Path

# Use the same path as database.py
db_path = Path('execution') / '.tmp' / 'newsfeed.db'
if not db_path.exists():
    # Fallback to current dir if needed for some reason
    db_path = Path('.tmp') / 'newsfeed.db'

print(f"Checking results in {db_path.absolute()}:")
if not db_path.exists():
    print("Database file NOT FOUND!")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

hospitals = ["Martini Ziekenhuis", "Meander MC", "HMC", "HagaZiekenhuis", "Maasstad Ziekenhuis"]

for h in hospitals:
    cursor.execute("SELECT COUNT(*) as count FROM articles WHERE hospital_name = ?", (h,))
    count = cursor.fetchone()['count']
    print(f"{h}: {count} articles")
    if count > 0:
        cursor.execute("SELECT date_published, title FROM articles WHERE hospital_name = ? ORDER BY date_published DESC LIMIT 3", (h,))
        for row in cursor.fetchall():
            print(f"  - [{row['date_published']}] {row['title']}")

conn.close()
