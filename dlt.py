import sqlite3

conn = sqlite3.connect("rescue.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM lost_found_reports;")
conn.commit()
conn.close()
print("✅ Cleared lost_found_reports table successfully.")
