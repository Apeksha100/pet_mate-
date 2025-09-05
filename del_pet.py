"""import sqlite3

# Connect to the database
conn = sqlite3.connect("pets.db")
cursor = conn.cursor()
id = 5
cursor.execute("DELETE FROM pets WHERE id = ?", (id,))
conn.commit()
print(f"pet with {id} has been deleted ")
# Fetch all pets
cursor.execute("SELECT * FROM pets")
for row in cursor.fetchall():
    print(row)

# Close the connection
conn.close()
"""