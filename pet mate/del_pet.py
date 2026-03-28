import sqlite3

# Connect to the database

conn = sqlite3.connect("pets.db")
cursor = conn.cursor()
# Fetch all pets to check

cursor.execute("SELECT * FROM pets")
for row in cursor.fetchall():
    print(row)

"""
# Optional: Delete a pet by id (currently commented out)

#id = 2
cursor.execute("DELETE FROM pets")
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
"""

# Close the connection

conn.close()
import os
print(os.getcwd())
import os
print("DB PATH:", os.path.abspath("pets.db"))
#cursor.execute("SELECT * FROM pets WHERE user_id=?", (current_user.id,))

"""
import sqlite3

conn = sqlite3.connect("rescue.db")
for row in conn.execute("SELECT * FROM lost_found_reports"):
    print(row)
conn.close()
"""