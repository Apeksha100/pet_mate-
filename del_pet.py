"""import sqlite3

# Connect to the database

conn = sqlite3.connect("pets.db")
cursor = conn.cursor()

# Optional: Delete a pet by id (currently commented out)

id = 16
cursor.execute("DELETE FROM pets WHERE id = ?", (id,))
conn.commit()
print(f"Pet with id {id} has been deleted")


# Update photo column for specific pets


pets_to_update = [
(1, "puppy.jpg"),
(6, "beagle2.png")
(8, "husky.jpg"),
(9, "persian_cat.jpg"),
(10, "beagle 1.jpg"),
(11, "parrot.jpg"),
(12, "turtle.jpg")
]

for pet_id, filename in pets_to_update:
    cursor.execute("UPDATE pets SET photo=? WHERE id=?", (filename, pet_id))

# Commit the updates

conn.commit()
print("Photos updated successfully!")

# Fetch all pets to check

cursor.execute("SELECT * FROM pets")
for row in cursor.fetchall():
    print(row)

# Close the connection

conn.close()

import sqlite3

conn = sqlite3.connect("rescue.db")
for row in conn.execute("SELECT * FROM lost_found_reports"):
    print(row)
conn.close()
"""