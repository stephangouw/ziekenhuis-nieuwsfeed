import sqlite3
import pprint

conn = sqlite3.connect('d:/Stackstorage/antigravity/nieuwsfeed/.tmp/newsfeed.db')
c = conn.cursor()
c.execute("SELECT hospital_name, title, url FROM articles ORDER BY id DESC")
rows = c.fetchall()
print(f"Total rows: {len(rows)}")
for row in rows:
    print(f"{row[0]} | {row[1][:40]}... | {row[2]}")
