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
                photo TEXT
            )
        ''')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
def add_pet():
    if request.method == 'POST':
        name = request.form['name']
        breed = request.form['breed']
        location = request.form['location']
        age = request.form['age']
        purpose = request.form['purpose']

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
            # Optional: show a flash message saying file type not allowed
                    print("Invalid file type")        

        with sqlite3.connect("pets.db") as conn:
            conn.execute(
                "INSERT INTO pets (name, breed, location, age, purpose, photo) VALUES (?, ?, ?, ?, ?, ?)",
                (name, breed, location, age, purpose, photo)
            )
        return redirect('/pets')
    return render_template('add_pet.html')

@app.route('/pets')
def list_pets():
    with sqlite3.connect("pets.db") as conn:
        pets = conn.execute("SELECT * FROM pets").fetchall()
    return render_template('pets.html', pets=pets)

@app.route('/buy')
def buy_pets():
    with sqlite3.connect("pets.db") as conn:
        pets = conn.execute("SELECT * FROM pets WHERE purpose = 'Sale'").fetchall()
    return render_template('buy_pets.html', pets=pets)

@app.route('/sell')
def sell_pet_redirect():
    return redirect('/add')  # Selling a pet is same as adding one

@app.route('/mate', methods=['GET', 'POST'])
def find_mate():
    pets = []
    if request.method == 'POST':
        breed = request.form['breed']  # user selects breed
        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute("SELECT * FROM pets WHERE breed = ? AND purpose = 'Mate'", (breed,)).fetchall()
    return render_template('mate.html', pets=pets)

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

    return render_template('search.html', pets=pets)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
