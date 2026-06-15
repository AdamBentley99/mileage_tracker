import sqlite3

conn = sqlite3.connect("data/mileage.db")
cursor = conn.cursor()

cursor.execute(
    "INSERT INTO stores (name, is_business) VALUES (?, ?)",
    ("Business", 1)
)

conn.commit()

rows = cursor.execute(
    "SELECT * FROM stores"
).fetchall()

for row in rows:
    print(row)

conn.close()