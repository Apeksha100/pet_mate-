from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
import sqlite3
import os
import requests as http_requests
from werkzeug.utils import secure_filename


app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ── Google Gemini API Key ──────────────────────────────────────────────────────
# Get your FREE key at: https://aistudio.google.com  →  "Get API Key"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
# ──────────────────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    with sqlite3.connect("pets.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, breed TEXT, location TEXT,
                age INTEGER, purpose TEXT, photo TEXT, category TEXT
            )
        ''')
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN category TEXT")
        except sqlite3.OperationalError:
            pass

    with sqlite3.connect("rescue.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lost_found_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT, animalType TEXT, location TEXT, date TEXT,
                description TEXT, contact TEXT, photo TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            conn.execute("ALTER TABLE lost_found_reports ADD COLUMN photo TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE lost_found_reports ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass


# ─── Page routes ──────────────────────────────────────────────────────────────

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
    pet = None
    if request.method == 'POST':
        name     = request.form.get('name')
        category = request.form.get('category')
        breed    = request.form.get('breed')
        location = request.form.get('location')
        age      = request.form.get('age')
        purpose  = request.form.get('purpose')
        try:
            age = int(age)
        except (ValueError, TypeError):
            age = None

        photo = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo = filename

        with sqlite3.connect("pets.db") as conn:
            conn.execute(
                "INSERT INTO pets (name, breed, location, age, purpose, photo, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, breed, location, age, purpose, photo, category)
            )
        pet = [None, name, breed, location, age, purpose, photo]
    return render_template('add_pet.html', pet=pet)

@app.route('/pets')
def list_pets():
    with sqlite3.connect("pets.db") as conn:
        pets = conn.execute("SELECT * FROM pets").fetchall()
    return render_template('pets.html', pets=pets)

@app.route('/buy')
def buy_pets():
    conn = sqlite3.connect("pets.db")
    conn.row_factory = sqlite3.Row
    pets = conn.execute("SELECT * FROM pets WHERE purpose IN ('Sale', 'Adoption')").fetchall()
    conn.close()
    return render_template('buy_pets.html', pets=pets)

@app.route('/buy/<int:pet_id>')
def buy_pet(pet_id):
    with sqlite3.connect("pets.db") as conn:
        conn.execute("UPDATE pets SET purpose = 'Sold' WHERE id = ?", (pet_id,))
    return redirect('/buy')

@app.route('/sell')
def sell_pet_redirect():
    return redirect('/add')

@app.route('/mate', methods=['GET', 'POST'])
def find_mate():
    pets = []
    selected_category = None
    selected_breed = None
    with sqlite3.connect("pets.db") as conn:
        categories = [row[0] for row in conn.execute("SELECT DISTINCT category FROM pets").fetchall()]
        breeds_per_category = {}
        for cat in categories:
            breeds_per_category[cat] = [
                row[0] for row in conn.execute(
                    "SELECT DISTINCT breed FROM pets WHERE category=?", (cat,)
                ).fetchall()
            ]
    if request.method == 'POST':
        selected_category = request.form.get('category')
        selected_breed    = request.form.get('breed')
        query  = "SELECT * FROM pets WHERE purpose='Mate'"
        params = []
        if selected_category:
            query += " AND category=?"; params.append(selected_category)
        if selected_breed:
            query += " AND breed=?"; params.append(selected_breed)
        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute(query, params).fetchall()
    return render_template('mate.html', pets=pets, categories=categories,
                           breeds_per_category=breeds_per_category,
                           selected_category=selected_category,
                           selected_breed=selected_breed)

@app.route('/search', methods=['GET', 'POST'])
def search_pets():
    pets = []
    if request.method == 'POST':
        breed    = request.form.get('breed')
        location = request.form.get('location')
        age      = request.form.get('age')
        purpose  = request.form.get('purpose')
        query  = "SELECT * FROM pets WHERE 1=1"
        params = []
        if breed:    query += " AND breed = ?";    params.append(breed)
        if location: query += " AND location = ?"; params.append(location)
        if age:      query += " AND age = ?";      params.append(age)
        if purpose:  query += " AND purpose = ?";  params.append(purpose)
        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute(query, params).fetchall()
    selected_purpose = request.form.get('purpose')
    return render_template('search.html', pets=pets, selected_purpose=selected_purpose)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/rescue")
def rescue():
    conn = sqlite3.connect("rescue.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lost_found_reports ORDER BY date DESC")
    reports = cursor.fetchall()
    conn.close()
    return render_template("rescue.html", reports=reports)

@app.route("/add_report", methods=["POST"])
def add_report():
    status      = request.form.get("status")
    animalType  = request.form.get("animalType")
    location    = request.form.get("location")
    date        = request.form.get("date")
    description = request.form.get("description")
    contact     = request.form.get("contact")
    photo = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo = filename
    conn = sqlite3.connect("rescue.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lost_found_reports (status, animalType, location, date, description, contact, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (status, animalType, location, date, description, contact, photo))
    conn.commit()
    conn.close()
    return jsonify({"message": "Report added successfully!"})

def generate_care_tips(category, age_group):
    tips = []
    animal_tips = {
        'Dog':     ['Schedule regular vet checkups every 6-12 months.',
                    'Provide daily walks and mental stimulation with puzzles.',
                    'Brush their coat weekly and check for ticks after outdoor time.'],
        'Cat':     ['Give fresh water daily and use multiple water stations.',
                    'Clean the litter box daily to reduce stress and prevent infection.',
                    'Add vertical spaces and play sessions to satisfy hunting instincts.'],
        'Bird':    ['Rotate toys weekly to keep them mentally active.',
                    'Offer a balanced diet: pellets, fresh fruits, and greens.',
                    'Ensure cage is cleaned and placed away from drafts.'],
        'Reptile': ['Maintain strict temperature and humidity gradients in the enclosure.',
                    'Use UVB lighting on a reliable timer for bone health.',
                    'Feed species-appropriate prey and avoid overfeeding.'],
        'Small':   ['Provide a spacious enclosure with hiding spots and chew toys.',
                    'Change bedding frequently and keep living area dry.',
                    'Introduce safe fresh vegetables gradually into their diet.']
    }
    tips.extend(animal_tips.get(category, [
        'Keep your pet comfortable with a safe, clean environment.',
        'Watch for behavior changes and seek veterinary advice if needed.',
        'Provide appropriate nutrition, exercise, and love daily.'
    ]))
    if age_group == 'Puppy/Kitten':
        tips.append('Start training early with short positive reinforcement sessions.')
        tips.append('Schedule vaccinations and deworming as recommended by your vet.')
    elif age_group == 'Adult':
        tips.append('Keep up with dental care and regular weight checks.')
        tips.append('Maintain a consistent feeding schedule to avoid weight gain.')
    elif age_group == 'Senior':
        tips.append('Monitor joint health and consider senior-specific diets.')
        tips.append('Offer softer bedding and easier access to water and food bowls.')
    return tips

@app.route('/care-tips', methods=['GET', 'POST'])
def care_tips():
    selected_category = ''
    selected_age      = ''
    pet_name          = ''
    tips              = []
    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_age      = request.form.get('age_group', '')
        pet_name          = request.form.get('pet_name', '').strip()
        tips              = generate_care_tips(selected_category, selected_age)
    return render_template('pet_care_tips.html',
                           pet_name=pet_name,
                           selected_category=selected_category,
                           selected_age=selected_age,
                           tips=tips)

@app.route('/vet')
def vet():
    return render_template('vet.html')


# ══════════════════════════════════════════════════════════════════════════════
#  PAWBOT CHATBOT — Google Gemini 1.5 Flash (FREE)
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are PawBot, the friendly AI assistant for PetNova — a complete pet platform. "
    "You help users find pets, understand the platform's services (buying, selling, rescue, "
    "finding mates for breeding, vet directory, pet shops directory, personalized care tips, "
    "and pet quizzes), and answer general pet-care questions. "
    "PetNova pages: / home, /pets browse all, /buy buy pets, /sell list a pet, "
    "/mate find breeding partner, /rescue lost & found, /vet vet directory, "
    "/petaccessories pet shops, /care-tips care tips, /quiz quizzes, /add add a pet. "
    "Keep answers concise, warm, and helpful. Use pet-related emojis occasionally. "
    "If asked about something unrelated to pets or PetNova, politely redirect back to pets."
)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data    = request.get_json(force=True)
        history = data.get("messages", [])

        # Build Gemini-format contents
        # Gemini requires alternating user/model turns, starting with user
        gemini_contents = []
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": gemini_contents,
            "generationConfig": {
                "maxOutputTokens": 512,
                "temperature": 0.7
            }
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        )

        print(f"[PawBot] Sending to Gemini — {len(gemini_contents)} turn(s)")

        resp = http_requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"[PawBot] Gemini status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"[PawBot] Gemini error body: {resp.text}")
            return jsonify({"reply": f"Gemini API error {resp.status_code}: {resp.json().get('error', {}).get('message', 'Unknown error')}"}), 500

        result = resp.json()
        reply  = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": reply})

    except http_requests.exceptions.Timeout:
        print("[PawBot] Request timed out")
        return jsonify({"reply": "Request timed out. Please try again! 🐾"}), 504

    except http_requests.exceptions.ConnectionError as e:
        print(f"[PawBot] Connection error: {e}")
        return jsonify({"reply": "Cannot connect to Gemini. Check your internet connection. 🐾"}), 503

    except KeyError as e:
        print(f"[PawBot] Unexpected response structure: {e} — {resp.text if 'resp' in dir() else 'no response'}")
        return jsonify({"reply": "Unexpected response from Gemini. Please try again. 🐾"}), 500

    except Exception as e:
        print(f"[PawBot] Unexpected error: {type(e).__name__}: {e}")
        return jsonify({"reply": f"Something went wrong: {str(e)}"}), 500

# ══════════════════════════════════════════════════════════════════════════════


if __name__ == '__main__':
    init_db()
    app.run(debug=True)