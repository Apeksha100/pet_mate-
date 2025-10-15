from flask import Flask, render_template, request, redirect
import sqlite3
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # make sure folder exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#allows all the mentioned file formats 
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# DB init
def init_db():
    with sqlite3.connect("pets.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                breed TEXT,
                location TEXT,
                age INTEGER,
                purpose TEXT,
                photo TEXT,
                category TEXT 
            )
        ''')
    # Optional: Add 'category' column if it doesn't exist (existing DB)
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN category TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/breed_quiz')
def breed_quiz():
    return render_template('breed_quiz.html')

@app.route('/mate_quiz')
def mate_quiz():
    return render_template('mate_quiz.html')

@app.route('/pet_quiz')
def pet_quiz():
    return render_template('pet_quiz.html')

@app.route('/petaccessories')
def pet_accessories():
    return render_template('pet_accessories.html')

@app.route('/add-petshop')
def add_petshop():
    return render_template('add-petshop.html')

@app.route('/add', methods=['GET', 'POST'])
def add_pet():
    pet = None  # Initialize pet as None

    if request.method == 'POST':
        # 1️⃣ Get form data
        name = request.form.get('name')
        category = request.form.get('category')
        breed = request.form.get('breed')
        location = request.form.get('location')
        age = request.form.get('age')
        purpose = request.form.get('purpose')

        # Convert age to int safely
        try:
            age = int(age)
        except (ValueError, TypeError):
            age = None  # or handle error as needed

        # 2️⃣ Handle photo upload
        photo = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    photo = filename
                else:
                    print("Invalid file type")  # Or flash a message

        # 3️⃣ Save pet to database
        with sqlite3.connect("pets.db") as conn:
            conn.execute(
                "INSERT INTO pets (name, breed, location, age, purpose, photo, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, breed, location, age, purpose, photo, category)
            )

        # 4️⃣ Create a pet list to pass to template if needed
        pet = [None, name, breed, location, age, purpose, photo]  # index 1=name, index 6=photo

        # Optionally, redirect to pet list instead of showing the added pet page
        # return redirect('/pets')

    # Render the template, pet might be None (for GET) or filled (after POST)
    return render_template('add_pet.html', pet=pet)

@app.route('/pets')
def list_pets():
    with sqlite3.connect("pets.db") as conn:
        pets = conn.execute("SELECT * FROM pets").fetchall()
    return render_template('buy_pets.html', pets=pets)

@app.route('/buy')
def buy_pets():
    with sqlite3.connect("pets.db") as conn:
        pets = conn.execute(
            "SELECT * FROM pets WHERE purpose IN ('Sale', 'Adoption')"
        ).fetchall()
    return render_template('buy_pets.html', pets=pets)


# New route to handle buying a pet
@app.route('/buy/<int:pet_id>')
def buy_pet(pet_id):
    with sqlite3.connect("pets.db") as conn:
        conn.execute("UPDATE pets SET purpose = 'Sold' WHERE id = ?", (pet_id,))
    return redirect('/buy')  # reload the buy page

@app.route('/sell')
def sell_pet_redirect():
    return redirect('/add')  # Selling a pet is same as adding one

@app.route('/mate', methods=['GET', 'POST'])
def find_mate():
    pets = []
    selected_category = None
    selected_breed = None

    # Get all distinct categories from the database
    with sqlite3.connect("pets.db") as conn:
        categories = [row[0] for row in conn.execute("SELECT DISTINCT category FROM pets").fetchall()]

    if request.method == 'POST':
        selected_category = request.form.get('category')
        selected_breed = request.form.get('breed')

        query = "SELECT * FROM pets WHERE purpose='Mate'"
        params = []

        if selected_category:
            query += " AND category=?"
            params.append(selected_category)
        if selected_breed:
            query += " AND breed=?"
            params.append(selected_breed)

        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute(query, params).fetchall()

    return render_template('mate.html', pets=pets, categories=categories,
                           selected_category=selected_category,
                           selected_breed=selected_breed)

@app.route('/search', methods=['GET', 'POST'])
def search_pets():
    pets = []
    if request.method == 'POST':
        breed = request.form.get('breed')
        location = request.form.get('location')
        age = request.form.get('age')
        purpose = request.form.get('purpose')

        query = "SELECT * FROM pets WHERE 1=1"
        params = []

        if breed:
            query += " AND breed = ?"
            params.append(breed)
        if location:
            query += " AND location = ?"
            params.append(location)
        if age:
            query += " AND age = ?"
            params.append(age)
        if purpose:
            query += " AND purpose = ?"
            params.append(purpose)

        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute(query, params).fetchall()
    selected_purpose = request.form.get('purpose')
    return render_template('search.html', pets=pets, selected_purpose=selected_purpose)
# Route for rescue page
@app.route('/rescue')
def rescue():
    # Example: Fetch rescue reports from DB if you want
    # For now, just render the page
    return render_template('rescue.html')


# Route for vet directory page
@app.route('/vet')
def vet():
    # Example: Fetch vets from DB if you want
    # For now, just render the page
    return render_template('vet.html')




if __name__ == '__main__':
    init_db()
    app.run(debug=True)
