import os
import re
from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, session, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
import sqlite3
from dotenv import load_dotenv
import requests as http_requests
from flask_session import Session

# ─── Load env and app ─────────────────────────────
load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET", "THIS_IS_A_FIXED_SECRET_123456789"),
    SESSION_COOKIE_NAME="petnova_session",
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_PATH="/",
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR=os.path.join(os.path.dirname(__file__), ".flask_session"),
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

# ─── Google OAuth setup ──────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

print("client id     :", GOOGLE_CLIENT_ID)
print("client secret :", GOOGLE_CLIENT_SECRET)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account',
    }
)

# ─── User Model ──────────────────────────────────
class User(UserMixin):
    def __init__(self, id, name):
        self.id   = id
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("users.db") as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if user:
            return User(user[0], user[2])
    return None

# ─── Inject current_user into ALL templates ──────
@app.context_processor
def inject_user():
    return dict(current_user=current_user)


UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are PawBot, the friendly AI assistant for PetNova — a complete pet platform. "
    "You help users find pets, understand the platform's services (buying, selling, rescue, "
    "finding mates for breeding, vet directory, pet shops directory, personalized care tips, "
    "and pet quizzes), and answer general pet-care questions. "
    "Keep answers concise, warm, and helpful. Use pet-related emojis occasionally."
)


def init_db():
    with sqlite3.connect("pets.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, breed TEXT, location TEXT,
                age INTEGER, purpose TEXT, photo TEXT, category TEXT, user_id INTEGER
            )
        ''')
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN category TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN user_id INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN gender TEXT")
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

    with sqlite3.connect("users.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT
            )
        ''')

# ─── Page routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login/google")
def login():
    redirect_uri = url_for("callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/callback")
def callback():
    try:
        token     = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            resp      = google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
            user_info = resp.json()

        email = user_info['email']
        name  = user_info.get('name', email)
        photo = user_info.get('picture', '')

        with sqlite3.connect("users.db") as conn:
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user:
                conn.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        login_user(User(user[0], user[2]))
        session['user'] = {'name': name, 'email': email, 'photo': photo}
        print("✅ Login success, redirecting to dashboard")
        return redirect("/dashboard") 

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect("/?login_error=1")


@app.route("/dashboard")
@login_required
def dashboard():
    with sqlite3.connect("users.db") as conn:
        user_data = conn.execute(
            "SELECT * FROM users WHERE id=?", (current_user.id,)
        ).fetchone()

    with sqlite3.connect("pets.db") as conn:
        pet_count = conn.execute(
            "SELECT COUNT(*) FROM pets WHERE user_id=?", (current_user.id,)
        ).fetchone()[0]
        my_pets = conn.execute(
            "SELECT * FROM pets WHERE user_id=?", (current_user.id,)
        ).fetchall()

    with sqlite3.connect("rescue.db") as conn:
        rescue_count = conn.execute(
            "SELECT COUNT(*) FROM lost_found_reports"
        ).fetchone()[0]

    user = session.get('user', {})
    return render_template("dashboard.html",
                           user_data=user_data,
                           user=user,
                           pet_count=pet_count,
                           rescue_count=rescue_count,
                           my_pets=my_pets)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('user', None)   # ✅ Clear user from session on logout
    return redirect("/")

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
@login_required
def add_pet():
    pet = None
    if request.method == 'POST':
        name     = request.form.get('name')
        category = request.form.get('category')
        breed    = request.form.get('breed')
        location = request.form.get('location')
        gender   = request.form.get('gender')
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
                "INSERT INTO pets (name, breed, location, age, purpose, photo, category, user_id, gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, breed, location, age, purpose, photo, category, current_user.id, gender)
            )
        pet = [None, name, breed, location, age, purpose, photo]
    return render_template('add_pet.html', pet=pet)

@app.route('/delete_pet/<int:pet_id>', methods=['POST'])
@login_required
def delete_pet(pet_id):
    with sqlite3.connect("pets.db") as conn:
        conn.execute(
            "DELETE FROM pets WHERE id=? AND user_id=?",
            (pet_id, current_user.id)
        )
    return redirect('/dashboard')

    

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
    selected_breed    = None
    selected_gender   = None
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
        selected_gender   = request.form.get('my_gender')  # user's pet gender

        # opposite gender logic
        opposite = None
        if selected_gender == 'Male':
            opposite = 'Female'
        elif selected_gender == 'Female':
            opposite = 'Male'

        query  = "SELECT * FROM pets WHERE purpose='Mate'"
        params = []
        if selected_category:
            query += " AND category=?"; params.append(selected_category)
        if selected_breed:
            query += " AND breed=?"; params.append(selected_breed)
        if opposite:
            query += " AND gender=?"; params.append(opposite)

        with sqlite3.connect("pets.db") as conn:
            pets = conn.execute(query, params).fetchall()

    return render_template('mate.html', pets=pets, categories=categories,
                           breeds_per_category=breeds_per_category,
                           selected_category=selected_category,
                           selected_breed=selected_breed,
                           selected_gender=selected_gender)




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


# ══════════════════════════════════════════════════════════════════════════════
#  GROQ — Care Tips
# ══════════════════════════════════════════════════════════════════════════════

def get_groq_care_tips(selected_category, selected_age, pet_name):
    if not selected_category or not selected_age:
        raise ValueError("Pet type and age group are required")

    prompt = (
        f"You are an experienced Vet, a friendly pet care assistant for PetNova. "
        f"Generate 4-6 concise practical care tips for a {selected_age} {selected_category}. "
        f"Include breed-agnostic advice, nutrition, activity, grooming, and health checks. "
        f"If pet name is provided ({pet_name}), include it once in a warm tone. "
        "Return each tip on a new line, without numbering."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt}
    ]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0.7
    }

    resp = http_requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        },
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")

    text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    tips = []
    for line in text.splitlines():
        clean = re.sub(r'^\s*[-*\d\.\)\s]+', '', line).strip()
        if clean:
            tips.append(clean)
    if not tips:
        raise RuntimeError("No tips returned by Groq")
    return tips


@app.route('/care-tips', methods=['GET', 'POST'])
def care_tips():
    selected_category = ''
    selected_age      = ''
    pet_name          = ''
    tips              = []
    warning           = ''

    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_age      = request.form.get('age_group', '')
        pet_name          = request.form.get('pet_name', '').strip()

        try:
            tips = get_groq_care_tips(selected_category, selected_age, pet_name)
        except Exception as e:
            warning = f"Could not fetch tips: {e}"

    return render_template('pet_care_tips.html',
                           pet_name=pet_name,
                           selected_category=selected_category,
                           selected_age=selected_age,
                           tips=tips,
                           warning=warning)

@app.route('/vet')
def vet():
    return render_template('vet.html')


# ══════════════════════════════════════════════════════════════════════════════
#  PAWBOT — Dedicated chat page
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/pawbot')
def pawbot():
    return render_template('chatbot.html')


# ══════════════════════════════════════════════════════════════════════════════
#  PAWBOT — Chat API endpoint
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not GROQ_API_KEY:
            return jsonify({"reply": "⚠️ API key is missing. Check your .env file!"}), 500

        data    = request.get_json(force=True)
        history = data.get("messages", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7
        }

        resp = http_requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            timeout=30
        )

        if resp.status_code != 200:
            return jsonify({"reply": f"⚠️ API error: {resp.text}"}), 500

        reply = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ Error: {str(e)}"}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)