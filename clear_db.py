import sqlite3
conn = sqlite3.connect('d:/Stackstorage/antigravity/nieuwsfeed/.tmp/newsfeed.db')
c = conn.cursor()
c.execute("DELETE FROM articles")
conn.commit()
print('DB Cleared:', c.rowcount)
