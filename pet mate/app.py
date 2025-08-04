from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# DB init
def init_db():
    with sqlite3.connect("pets.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                breed TEXT,
                location TEXT,
                purpose TEXT
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
        purpose = request.form['purpose']
        with sqlite3.connect("pets.db") as conn:
            conn.execute("INSERT INTO pets (name, breed, location, purpose) VALUES (?, ?, ?, ?)",
                         (name, breed, location, purpose))
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
