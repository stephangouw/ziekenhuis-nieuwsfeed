import sqlite3
import pprint
import os

db_path = os.path.join('.tmp', 'newsfeed.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

hospitals = ['HMC', 'HagaZiekenhuis', 'Maasstad Ziekenhuis', 'Martini Ziekenhuis', 'Meander MC']
results = {}

for h in hospitals:
    cursor.execute("SELECT COUNT(*) FROM articles WHERE hospital_name=?", (h,))
    results[h] = cursor.fetchone()[0]

pprint.pprint(results)

# Dump 1 example for each to confirm content
for h in hospitals:
    if results[h] > 0:
        cursor.execute("SELECT title, date_published FROM articles WHERE hospital_name=? ORDER BY date_published DESC LIMIT 1", (h,))
        print(f"\\n[{h}] -> {cursor.fetchone()}")

conn.close()
