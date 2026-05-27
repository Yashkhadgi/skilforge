from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "skillforge-secret-2025"  # Required for session to work


# -------------------------------------------------------------------
# DATABASE SETUP
# -------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # Rows behave like dictionaries
    return conn


def init_db():
    conn = get_db()

    # [EXPLANATION] executescript: Ek saath multiple SQL statements run karne ka tarika
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()


# [EXPLANATION] app_context: Flask ka internal environment —
# DB operations app start hote hi iske andar hone chahiye
with app.app_context():
    init_db()


# Available courses — defined once, used in dashboard and enroll
COURSES = [
    "Python Fundamentals",
    "Flask Development",
    "Web Development",
    "Machine Learning Basics",
    "AI Introduction"
]


# -------------------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------------------

@app.route('/')
def home():
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']

        # pbkdf2:sha256 — Python 3.9 compatible hashing method
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_pw)
            )
            conn.commit()

            # [EXPLANATION] flash: Ek baar dikhne wala message —
            # next page load pe show hoga phir disappear
            flash("Account created! Please login.", "success")
            return redirect('/login')

        except sqlite3.IntegrityError:
            # IntegrityError — username ya email already exists in DB
            flash("Username or email already taken.", "danger")

        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        # [EXPLANATION] check_password_hash: DB ka hash aur user ka input —
        # dono compare karta hai bina decrypt kiye
        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')

        flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Clears entire session — user logged out
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')


# -------------------------------------------------------------------
# DASHBOARD & ENROLL ROUTES
# -------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():

    # [EXPLANATION] Protected Route: Session check — agar logged in nahi
    # toh dashboard dikhne se pehle hi login pe redirect
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    enrolled = conn.execute(
        "SELECT course_name FROM enrollments WHERE user_id = ?",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    # [EXPLANATION] List comprehension: Row objects se sirf
    # course_name ki plain string list bana rahe hain
    enrolled_names = [row['course_name'] for row in enrolled]

    return render_template(
        'dashboard.html',
        username=session['username'],
        courses=COURSES,
        enrolled=enrolled_names
    )


@app.route('/enroll/<course_name>')
def enroll(course_name):

    if 'user_id' not in session:
        return redirect('/login')

    # Reject invalid course names from URL tampering
    if course_name not in COURSES:
        flash("Invalid course.", "danger")
        return redirect('/dashboard')

    conn = get_db()

    already = conn.execute(
        "SELECT id FROM enrollments WHERE user_id = ? AND course_name = ?",
        (session['user_id'], course_name)
    ).fetchone()

    if already:
        flash(f"Already enrolled in {course_name}.", "warning")
    else:
        conn.execute(
            "INSERT INTO enrollments (user_id, course_name) VALUES (?, ?)",
            (session['user_id'], course_name)
        )
        conn.commit()
        flash(f"Enrolled in {course_name} successfully!", "success")

    conn.close()
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True)