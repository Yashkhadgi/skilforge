from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "skillforge-secret-2025"


# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row   # row ko dict ki tarah access kar sakte hain
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""

        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        );
        -- [EXPLANATION] is_admin column naya hai
        -- 0 = normal student, 1 = admin
        -- DEFAULT 0 matlab jab bhi naya user register kare, woh automatically student hoga

        CREATE TABLE IF NOT EXISTS courses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            instructor  TEXT NOT NULL,
            category    TEXT NOT NULL,
            level       TEXT NOT NULL,
            duration    TEXT NOT NULL,
            rating      REAL NOT NULL,
            students    INTEGER NOT NULL,
            description TEXT NOT NULL,
            color       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            course_id   INTEGER NOT NULL,
            progress    INTEGER DEFAULT 0,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)   REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

    """)
    conn.commit()

    # ------- Seed admin user -------
    # [EXPLANATION] Pehle check karo ki admin already exist karta hai ya nahi
    # Agar nahi karta toh ek fixed admin account bana do
    admin_exists = conn.execute(
        "SELECT id FROM users WHERE username = 'admin'"
    ).fetchone()

    if not admin_exists:
        hashed = generate_password_hash("admin123", method='pbkdf2:sha256')
        conn.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            ("admin", "admin@skillforge.com", hashed, 1)
            # [EXPLANATION] is_admin = 1 kyunki yeh admin hai
        )
        conn.commit()

    # ------- Seed courses -------
    count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if count == 0:
        courses = [
            ("Python Fundamentals",       "Arjun Mehta",    "Python", "Beginner",     "14 hrs", 4.8, 12400, "Master Python from scratch. Variables, loops, functions, OOP and more.",          "#4f8ef7"),
            ("Flask Web Development",     "Priya Sharma",   "Web",    "Intermediate", "18 hrs", 4.7,  8900, "Build real web apps with Flask. Routing, templates, databases, auth.",            "#7c3aed"),
            ("Machine Learning Basics",   "Rahul Verma",    "AI",     "Intermediate", "22 hrs", 4.9,  6700, "Learn ML algorithms, data preprocessing, model training with scikit-learn.",     "#059669"),
            ("Web Development Bootcamp",  "Sneha Iyer",     "Web",    "Beginner",     "30 hrs", 4.6, 15200, "HTML, CSS, JavaScript — build modern websites from scratch.",                    "#db2777"),
            ("AI Introduction",           "Vikram Nair",    "AI",     "Beginner",     "10 hrs", 4.5,  9300, "Understand AI concepts, use cases, and how modern AI systems work.",             "#d97706"),
            ("Data Structures & Algo",    "Ankit Gupta",    "Python", "Advanced",     "25 hrs", 4.9,  7800, "Master DSA with Python. Arrays, trees, graphs, dynamic programming.",            "#0891b2"),
            ("React JS Complete Guide",   "Neha Kulkarni",  "Web",    "Intermediate", "20 hrs", 4.7, 11000, "Build dynamic UIs with React. Hooks, state management, REST APIs.",              "#ea580c"),
            ("Deep Learning with PyTorch","Siddharth Rao",  "AI",     "Advanced",     "28 hrs", 4.8,  4200, "Neural networks, CNNs, RNNs — build and train deep learning models.",            "#16a34a"),
        ]
        conn.executemany(
            "INSERT INTO courses (title,instructor,category,level,duration,rating,students,description,color) VALUES (?,?,?,?,?,?,?,?,?)",
            courses
        )
        conn.commit()

    conn.close()


with app.app_context():
    init_db()


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def login_required():
    """Returns redirect if user is not logged in."""
    if 'user_id' not in session:
        return redirect('/login')
    return None


def admin_required():
    """Returns redirect if user is not logged in OR not an admin.
    [EXPLANATION] Yeh helper do cheezein check karta hai:
    1. User logged in hai ya nahi
    2. Logged in hai toh admin hai ya nahi
    Agar dono pass → None return karta hai (matlab sab theek hai)
    Agar fail → redirect kar deta hai
    """
    if 'user_id' not in session:
        return redirect('/login')
    if not session.get('is_admin'):
        # [EXPLANATION] session mein is_admin store kiya hoga login ke time
        # Agar 0 ya missing hai toh dashboard pe bhej do with error message
        flash("Access denied. Admins only.", "danger")
        return redirect('/dashboard')
    return None


# -------------------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------------------

@app.route('/')
def home():
    return redirect('/dashboard')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']

        # is_admin = 0 by default — normal student
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_pw, 0)
                # [EXPLANATION] Naya register karne wala always student hoga (0)
            )
            conn.commit()
            flash("Account created! Please login.", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
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

        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            # [EXPLANATION] Login ke time is_admin bhi session mein daal do
            # Taaki har route pe DB hit na karna pade — session se seedha pata chalega
            return redirect('/dashboard')

        flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')


# -------------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    guard = login_required()
    if guard: return guard

    conn = get_db()

    enrolled = conn.execute("""
        SELECT c.*, e.progress, e.enrolled_at
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.user_id = ?
        ORDER BY e.enrolled_at DESC
    """, (session['user_id'],)).fetchall()

    recommended = conn.execute("""
        SELECT * FROM courses
        WHERE id NOT IN (
            SELECT course_id FROM enrollments WHERE user_id = ?
        )
        LIMIT 4
    """, (session['user_id'],)).fetchall()

    conn.close()

    total_enrolled = len(enrolled)
    avg_progress   = round(sum(c['progress'] for c in enrolled) / total_enrolled) if total_enrolled else 0

    return render_template('dashboard.html',
        enrolled=enrolled,
        recommended=recommended,
        total_enrolled=total_enrolled,
        avg_progress=avg_progress
    )


# -------------------------------------------------------------------
# COURSES (Student side — unchanged)
# -------------------------------------------------------------------

@app.route('/courses')
def courses():
    guard = login_required()
    if guard: return guard

    category = request.args.get('category', 'All')
    conn     = get_db()

    if category == 'All':
        all_courses = conn.execute("SELECT * FROM courses").fetchall()
    else:
        all_courses = conn.execute(
            "SELECT * FROM courses WHERE category = ?", (category,)
        ).fetchall()

    enrolled_ids = [row['course_id'] for row in conn.execute(
        "SELECT course_id FROM enrollments WHERE user_id = ?",
        (session['user_id'],)
    ).fetchall()]

    conn.close()

    categories = ['All', 'Python', 'Web', 'AI']

    return render_template('courses.html',
        courses=all_courses,
        enrolled_ids=enrolled_ids,
        categories=categories,
        active_category=category
    )


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    guard = login_required()
    if guard: return guard

    conn   = get_db()
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect('/courses')

    enrollment = conn.execute(
        "SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?",
        (session['user_id'], course_id)
    ).fetchone()

    conn.close()

    curriculum = [
        {"module": "Module 1: Getting Started",      "lessons": 3},
        {"module": "Module 2: Core Concepts",         "lessons": 5},
        {"module": "Module 3: Hands-on Projects",     "lessons": 4},
        {"module": "Module 4: Advanced Topics",       "lessons": 6},
        {"module": "Module 5: Final Project & Quiz",  "lessons": 2},
    ]

    return render_template('course_detail.html',
        course=course,
        enrollment=enrollment,
        curriculum=curriculum
    )


@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    guard = login_required()
    if guard: return guard

    conn = get_db()

    already = conn.execute(
        "SELECT id FROM enrollments WHERE user_id = ? AND course_id = ?",
        (session['user_id'], course_id)
    ).fetchone()

    if not already:
        conn.execute(
            "INSERT INTO enrollments (user_id, course_id, progress) VALUES (?, ?, ?)",
            (session['user_id'], course_id, 0)
        )
        conn.commit()
        flash("Successfully enrolled!", "success")
    else:
        flash("Already enrolled in this course.", "warning")

    conn.close()
    return redirect(f'/course/{course_id}')


# -------------------------------------------------------------------
# MY LEARNING
# -------------------------------------------------------------------

@app.route('/my-learning')
def my_learning():
    guard = login_required()
    if guard: return guard

    conn = get_db()

    my_courses = conn.execute("""
        SELECT c.*, e.progress, e.enrolled_at, e.id as enrollment_id
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.user_id = ?
        ORDER BY e.enrolled_at DESC
    """, (session['user_id'],)).fetchall()

    conn.close()

    total     = len(my_courses)
    completed = sum(1 for c in my_courses if c['progress'] >= 100)
    avg       = round(sum(c['progress'] for c in my_courses) / total) if total else 0

    return render_template('my_learning.html',
        my_courses=my_courses,
        total=total,
        completed=completed,
        avg_progress=avg
    )


# -------------------------------------------------------------------
# USERS PAGE  (Task 1)
# -------------------------------------------------------------------

@app.route('/users')
def users():
    """Show all registered users — login required.
    [EXPLANATION] Yeh Task 1 ka route hai
    Sirf logged-in users dekh sakte hain — admin bhi, student bhi
    """
    guard = login_required()
    if guard: return guard

    conn = get_db()
    all_users = conn.execute(
        "SELECT id, username, email, is_admin FROM users ORDER BY id ASC"
        # [EXPLANATION] Password column SELECT nahi kiya — security best practice
        # Kabhi bhi password UI pe show mat karo, chahe hashed ho
    ).fetchall()
    conn.close()

    return render_template('users.html', users=all_users)


# -------------------------------------------------------------------
# ADMIN — COURSE CRUD  (Task 3)
# -------------------------------------------------------------------

@app.route('/admin/courses')
def admin_courses():
    """Admin dashboard — list all courses with edit/delete options."""
    guard = admin_required()
    if guard: return guard

    conn = get_db()
    all_courses = conn.execute("SELECT * FROM courses ORDER BY id ASC").fetchall()
    conn.close()

    return render_template('admin_courses.html', courses=all_courses)


@app.route('/admin/courses/add', methods=['GET', 'POST'])
def admin_add_course():
    """Add a new course — GET shows form, POST saves to DB.
    [EXPLANATION] methods=['GET', 'POST'] kyunki:
    GET  → form dikhao (browser se page open karna)
    POST → form submit hone pe data save karo
    """
    guard = admin_required()
    if guard: return guard

    if request.method == 'POST':
        # Form se saara data uthao
        title       = request.form['title'].strip()
        instructor  = request.form['instructor'].strip()
        category    = request.form['category']
        level       = request.form['level']
        duration    = request.form['duration'].strip()
        rating      = float(request.form['rating'])
        students    = int(request.form['students'])
        description = request.form['description'].strip()
        color       = request.form['color']

        conn = get_db()
        conn.execute(
            """INSERT INTO courses
               (title, instructor, category, level, duration, rating, students, description, color)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, instructor, category, level, duration, rating, students, description, color)
        )
        conn.commit()
        conn.close()

        flash(f'Course "{title}" added successfully!', "success")
        return redirect('/admin/courses')

    # GET request — sirf form dikhao
    return render_template('admin_add.html')


@app.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    """Edit existing course.
    [EXPLANATION] GET pe: DB se existing data uthao, form mein pre-fill karo
                  POST pe: updated data DB mein save karo
    """
    guard = admin_required()
    if guard: return guard

    conn = get_db()
    course = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect('/admin/courses')

    if request.method == 'POST':
        title       = request.form['title'].strip()
        instructor  = request.form['instructor'].strip()
        category    = request.form['category']
        level       = request.form['level']
        duration    = request.form['duration'].strip()
        rating      = float(request.form['rating'])
        students    = int(request.form['students'])
        description = request.form['description'].strip()
        color       = request.form['color']

        conn.execute(
            """UPDATE courses SET
               title=?, instructor=?, category=?, level=?,
               duration=?, rating=?, students=?, description=?, color=?
               WHERE id=?""",
            (title, instructor, category, level, duration, rating, students, description, color, course_id)
            # [EXPLANATION] UPDATE query mein WHERE id=? bahut zaroori hai
            # Bina WHERE ke saare courses update ho jayenge!
        )
        conn.commit()
        conn.close()

        flash(f'Course "{title}" updated successfully!', "success")
        return redirect('/admin/courses')

    conn.close()
    return render_template('admin_edit.html', course=course)


@app.route('/admin/courses/delete/<int:course_id>')
def admin_delete_course(course_id):
    """Delete a course by ID.
    [EXPLANATION] Delete ke liye alag template nahi chahiye
    Seedha link click → course delete → admin page pe wapas
    """
    guard = admin_required()
    if guard: return guard

    conn = get_db()
    course = conn.execute(
        "SELECT title FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if course:
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash(f'Course "{course["title"]}" deleted.', "success")
    else:
        flash("Course not found.", "danger")

    conn.close()
    return redirect('/admin/courses')


# -------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)