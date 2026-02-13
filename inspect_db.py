import sqlite3
from database import DATABASE

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(students)")
columns = cursor.fetchall()
for col in columns:
    print(col)

cursor.execute("SELECT * FROM students LIMIT 1")
row = cursor.fetchone()
if row:
    print("\nFirst row sample:")
    print(dict(zip([c[1] for c in columns], row)))
else:
    print("\nNo rows in students table.")
conn.close()
