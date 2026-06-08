from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from datetime import timedelta
from functools import wraps
import sqlite3
import os
import re
import secrets
import math
import time

# -------------------------------------------------------------------
# CONFIGURATION & SETUP
# -------------------------------------------------------------------

load_dotenv()
app = Flask(__name__)

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    import warnings
    warnings.warn(
        "SECRET_KEY is not set. Using an insecure fallback. "
        "Set SECRET_KEY in your environment before deploying.",
        stacklevel=2
    )
    _secret = "fallback-dev-key-do-not-use-in-production"
app.secret_key = _secret

# #17 — Session timeout
app.permanent_session_lifetime = timedelta(hours=2)

# #15 — CSRF
app.config['WTF_CSRF_TIME_LIMIT'] = None

# #13 — Flask-Mail
app.config['MAIL_SERVER']         = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']           = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD']       = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@skillforge.com')

mail    = Mail(app)
csrf    = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[])

PER_PAGE = 6
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------

def get_db():
    """Establish and return a database connection with Row factory."""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema and seed initial data if empty."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        );

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
            color       TEXT NOT NULL,
            image_url   TEXT DEFAULT ''
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
        
        CREATE TABLE IF NOT EXISTS reviews (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            course_id  INTEGER NOT NULL,
            rating     INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment    TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, course_id),
            FOREIGN KEY (user_id)   REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
    """)
    conn.commit()

    # Migrations for existing databases
    for migration in [
        "ALTER TABLE courses ADD COLUMN image_url TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists — safe to ignore

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Seed admin if not exists
    if not conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
        conn.execute(
            "INSERT INTO users (username,email,password,is_admin) VALUES (?,?,?,?)",
            ("admin","admin@skillforge.com", generate_password_hash(admin_pw, method='pbkdf2:sha256'), 1)
        )
        conn.commit()

    # Seed courses
    if conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        courses = [
            ("Python Fundamentals",        "Arjun Mehta",   "Python","Beginner",    "14 hrs",4.8,12400,"Master Python from scratch. Variables, loops, functions, OOP and more.","#4f8ef7",""),
            ("Flask Web Development",      "Priya Sharma",  "Web",  "Intermediate", "18 hrs",4.7, 8900,"Build real web apps with Flask. Routing, templates, databases, auth.",  "#7c3aed",""),
            ("Machine Learning Basics",    "Rahul Verma",   "AI",   "Intermediate", "22 hrs",4.9, 6700,"Learn ML algorithms, data preprocessing, model training with scikit-learn.","#059669",""),
            ("Web Development Bootcamp",   "Sneha Iyer",    "Web",  "Beginner",     "30 hrs",4.6,15200,"HTML, CSS, JavaScript — build modern websites from scratch.",            "#db2777",""),
            ("AI Introduction",            "Vikram Nair",   "AI",   "Beginner",     "10 hrs",4.5, 9300,"Understand AI concepts, use cases, and how modern AI systems work.",    "#d97706",""),
            ("Data Structures & Algo",     "Ankit Gupta",   "Python","Advanced",    "25 hrs",4.9, 7800,"Master DSA with Python. Arrays, trees, graphs, dynamic programming.",   "#0891b2",""),
            ("React JS Complete Guide",    "Neha Kulkarni", "Web",  "Intermediate", "20 hrs",4.7,11000,"Build dynamic UIs with React. Hooks, state management, REST APIs.",     "#ea580c",""),
            ("Deep Learning with PyTorch", "Siddharth Rao", "AI",   "Advanced",     "28 hrs",4.8, 4200,"Neural networks, CNNs, RNNs — build and train deep learning models.",   "#16a34a",""),
        ]
        conn.executemany(
            "INSERT INTO courses (title,instructor,category,level,duration,rating,students,description,color,image_url) VALUES (?,?,?,?,?,?,?,?,?,?)",
            courses
        )
        conn.commit()
    conn.close()

with app.app_context():
    init_db()


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def validate_csrf():
    """Stub to prevent legacy routes from breaking. Global CSRF Protect is active."""
    return True

def login_required(f=None):
    """Decorator or inline check to require login for specific routes."""
    if f is None:
        if 'user_id' not in session:
            return redirect(f'/login?next={request.path}')
        return None
        
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(f'/login?next={request.path}')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require admin privileges for specific routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if not session.get('is_admin'):
            flash("Access denied. Admins only.", "danger")
            return redirect('/dashboard')
        return f(*args, **kwargs)
    return decorated


# -------------------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------------------

@app.route('/')
def home():
    """Render the landing page or redirect to dashboard if logged in."""
    if 'user_id' in session:
        return redirect('/dashboard')
    conn = get_db()
    featured = conn.execute("SELECT * FROM courses LIMIT 3").fetchall()
    conn.close()
    return render_template('landing.html', featured=featured)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration and welcome email dispatch."""
    if request.method == 'POST':
        username  = request.form['username'].strip()
        email     = request.form['email'].strip()
        password  = request.form['password']
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username,email,password,is_admin) VALUES (?,?,?,?)",
                (username, email, hashed_pw, 0)
            )
            conn.commit()
            
            # #13 — Send welcome email (silently fails if MAIL not configured)
            try:
                msg      = Message(subject='Welcome to SkillForge! 🎓', recipients=[email])
                msg.body = (
                    f"Hi {username},\n\n"
                    f"Welcome to SkillForge! Your account is ready.\n\n"
                    f"Start learning for free at: http://localhost:5000/courses\n\n"
                    f"Happy learning!\nThe SkillForge Team"
                )
                mail.send(msg)
            except Exception:
                pass
                
            flash("Account created! Please login.", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Username or email already taken.", "danger")
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Handle user authentication and session creation with rate limits."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.permanent = True          # #17
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('/dashboard')

        flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear session data and logout user."""
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')


# -------------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    """Render the user dashboard with current enrollments and recommendations."""
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

    total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    conn.close()

    total_enrolled = len(enrolled)
    avg_progress   = round(sum(c['progress'] for c in enrolled) / total_enrolled) if total_enrolled else 0

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return render_template('dashboard.html',
        enrolled=enrolled,
        recommended=recommended,
        total_enrolled=total_enrolled,
        avg_progress=avg_progress,
        total_courses=total_courses,
        greeting=greeting
    )


# -------------------------------------------------------------------
# COURSES  (Student side)
# -------------------------------------------------------------------

@app.route('/courses')
def courses():
    """List available courses with pagination, category filtering, and search."""
    guard = login_required()
    if guard: return guard
    
    category = request.args.get('category', 'All')
    q        = request.args.get('q', '').strip()
    
    try:
        page = max(1, int(request.args.get('page', 1) or 1))
    except ValueError:
        page = 1
        
    conn     = get_db()

    if category == 'All' and not q:
        all_courses = conn.execute("SELECT * FROM courses").fetchall()
    elif category == 'All' and q:
        all_courses = conn.execute(
            "SELECT * FROM courses WHERE lower(title) LIKE ? OR lower(instructor) LIKE ?",
            (f'%{q.lower()}%', f'%{q.lower()}%')
        ).fetchall()
    elif category != 'All' and not q:
        all_courses = conn.execute(
            "SELECT * FROM courses WHERE category = ?", (category,)
        ).fetchall()
    else:
        all_courses = conn.execute(
            "SELECT * FROM courses WHERE category=? AND (lower(title) LIKE ? OR lower(instructor) LIKE ?)",
            (category, f'%{q.lower()}%', f'%{q.lower()}%')
        ).fetchall()

    enrollments_raw = conn.execute(
        "SELECT id, course_id, progress FROM enrollments WHERE user_id = ?",
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    enrolled_ids      = [r['course_id'] for r in enrollments_raw]
    enrolled_progress = {r['course_id']: r['progress'] for r in enrollments_raw}
    enrollment_id_map = {r['course_id']: r['id']       for r in enrollments_raw}
    
    # Pagination
    total_courses = len(all_courses)
    total_pages   = max(1, math.ceil(total_courses / PER_PAGE))
    page          = min(page, total_pages)
    courses_page  = all_courses[(page-1)*PER_PAGE : page*PER_PAGE]
    
    return render_template('courses.html',
        courses=courses_page,
        total_courses=total_courses,
        enrolled_ids=enrolled_ids,
        enrolled_progress=enrolled_progress,
        enrollment_id_map=enrollment_id_map,
        categories=['All','Python','Web','AI'],
        active_category=category,
        search_query=q,
        page=page,
        total_pages=total_pages,
        per_page=PER_PAGE
    )


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """View details for a specific course including reviews and curriculum."""
    guard = login_required()
    if guard: return guard
    
    conn   = get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    
    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect('/courses')

    enrollment = conn.execute(
        "SELECT * FROM enrollments WHERE user_id=? AND course_id=?",
        (session['user_id'], course_id)
    ).fetchone()

    reviews = conn.execute("""
        SELECT r.*, u.username
        FROM reviews r
        JOIN users u ON u.id = r.user_id
        WHERE r.course_id = ?
        ORDER BY r.created_at DESC
    """, (course_id,)).fetchall()

    user_review = conn.execute(
        "SELECT * FROM reviews WHERE user_id=? AND course_id=?",
        (session['user_id'], course_id)
    ).fetchone()

    avg_row      = conn.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE course_id=?",
        (course_id,)
    ).fetchone()
    live_avg     = round(avg_row[0], 1) if avg_row[0] else None
    review_count = avg_row[1]
    
    distribution = {i: 0 for i in range(1, 6)}
    for r in reviews:
        distribution[r['rating']] += 1
        
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
        curriculum=curriculum,
        reviews=reviews,
        user_review=user_review,
        live_avg=live_avg,
        review_count=review_count,
        distribution=distribution
    )


@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    """Enroll the current user in a specific course."""
    if not validate_csrf():
        return redirect(f'/course/{course_id}')

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
@login_required
def my_learning():
    """List all courses the user is currently enrolled in."""
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


@app.route('/update-progress/<int:enrollment_id>', methods=['POST'])
@login_required
def update_progress(enrollment_id):
    """Update progress percentage for a specific enrollment."""
    if not validate_csrf():
        return redirect('/my-learning')

    try:
        progress = int(request.form['progress'])
        progress = max(0, min(100, progress))
    except ValueError:
        flash("Invalid progress value.", "danger")
        return redirect('/my-learning')

    conn = get_db()
    conn.execute(
        "UPDATE enrollments SET progress = ? WHERE id = ? AND user_id = ?",
        (progress, enrollment_id, session['user_id'])
    )
    conn.commit()
    conn.close()

    flash("Progress updated!", "success")
    return redirect('/my-learning')


# -------------------------------------------------------------------
# USER PROFILE & PASSWORD
# -------------------------------------------------------------------

@app.route('/profile')
@login_required
def profile():
    """View the current user's profile and progress summary."""
    conn = get_db()
    
    user = conn.execute(
        "SELECT id, username, email, is_admin FROM users WHERE id = ?",
        (session['user_id'],)
    ).fetchone()
    
    enrolled = conn.execute("""
        SELECT c.*, e.progress, e.enrolled_at, e.id as enrollment_id
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.user_id = ?
        ORDER BY e.enrolled_at DESC
    """, (session['user_id'],)).fetchall()
    
    conn.close()
    
    total     = len(enrolled)
    completed = sum(1 for c in enrolled if c['progress'] >= 100)
    in_prog   = sum(1 for c in enrolled if 0 < c['progress'] < 100)
    avg       = round(sum(c['progress'] for c in enrolled) / total) if total else 0
    
    return render_template('profile.html',
        user=user,
        enrolled=enrolled,
        total=total,
        completed=completed,
        in_progress=in_prog,
        avg_progress=avg
    )


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change for the current user."""
    if request.method == 'POST':
        if not validate_csrf():
            return redirect('/change-password')

        current_pw  = request.form['current_password']
        new_pw      = request.form['new_password'].strip()
        confirm_pw  = request.form['confirm_password'].strip()

        # Basic validation
        if not new_pw or len(new_pw) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return render_template('change_password.html')

        if new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
            return render_template('change_password.html')

        conn = get_db()
        user = conn.execute(
            "SELECT password FROM users WHERE id = ?", (session['user_id'],)
        ).fetchone()

        if not check_password_hash(user['password'], current_pw):
            conn.close()
            flash("Current password is incorrect.", "danger")
            return render_template('change_password.html')

        new_hash = generate_password_hash(new_pw, method='pbkdf2:sha256')
        conn.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (new_hash, session['user_id'])
        )
        conn.commit()
        conn.close()

        flash("Password changed successfully!", "success")
        return redirect('/profile')

    return render_template('change_password.html')


# -------------------------------------------------------------------
# USERS PAGE — Admin only
# -------------------------------------------------------------------

@app.route('/users')
@admin_required
def users():
    """Admin view of all registered users."""
    conn = get_db()
    all_users = conn.execute(
        "SELECT id, username, email, is_admin FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()

    return render_template('users.html', users=all_users)


@app.route('/admin/users/promote/<int:user_id>', methods=['POST'])
@admin_required
def admin_promote_user(user_id):
    """Toggle a user's admin status."""
    if not validate_csrf():
        return redirect('/users')

    if user_id == session['user_id']:
        flash("You cannot change your own admin status.", "warning")
        return redirect('/users')

    conn = get_db()
    user = conn.execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        flash("User not found.", "danger")
        return redirect('/users')

    if user['is_admin'] == 1:
        admin_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1"
        ).fetchone()[0]

        if admin_count <= 1:
            conn.close()
            flash("Cannot demote — at least one admin must remain.", "warning")
            return redirect('/users')

    new_role = 0 if user['is_admin'] == 1 else 1
    conn.execute(
        "UPDATE users SET is_admin = ? WHERE id = ?", (new_role, user_id)
    )
    conn.commit()
    conn.close()

    action = "demoted to Student" if new_role == 0 else "promoted to Admin"
    flash(f'"{user["username"]}" has been {action}.', "success")
    return redirect('/users')


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user account and their enrollments."""
    if not validate_csrf():
        return redirect('/users')

    if user_id == session['user_id']:
        flash("You cannot delete your own account.", "warning")
        return redirect('/users')

    conn = get_db()
    user = conn.execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        flash("User not found.", "danger")
        return redirect('/users')

    if user['is_admin'] == 1:
        admin_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1"
        ).fetchone()[0]

        if admin_count <= 1:
            conn.close()
            flash("Cannot delete — at least one admin must remain.", "warning")
            return redirect('/users')

    conn.execute("DELETE FROM enrollments WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash(f'User "{user["username"]}" and their enrollments have been deleted.', "success")
    return redirect('/users')


# -------------------------------------------------------------------
# ADMIN — COURSE CRUD
# -------------------------------------------------------------------

@app.route('/admin/courses')
@admin_required
def admin_courses():
    """Admin view of all courses."""
    conn = get_db()
    all_courses = conn.execute("SELECT * FROM courses ORDER BY id ASC").fetchall()
    conn.close()

    return render_template('admin_courses.html', courses=all_courses)


@app.route('/admin/courses/add', methods=['GET', 'POST'])
@admin_required
def admin_add_course():
    """Admin functionality to add a new course."""
    if request.method == 'POST':
        if not validate_csrf():
            return redirect('/admin/courses/add')

        title       = request.form['title'].strip()
        instructor  = request.form['instructor'].strip()
        category    = request.form['category']
        level       = request.form['level']
        duration    = request.form['duration'].strip()
        description = request.form['description'].strip()
        color       = request.form['color']
        image_url   = request.form.get('image_url', '').strip()

        # File upload takes priority over URL
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            filename  = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_url = f'/static/uploads/{filename}'

        if not title or not instructor or not duration or not description:
            flash("All text fields are required and cannot be blank.", "danger")
            return render_template('admin_add.html')

        try:
            rating   = float(request.form['rating'])
            students = int(request.form['students'])
        except ValueError:
            flash("Rating and Students must be valid numbers.", "danger")
            return render_template('admin_add.html')

        if not (1.0 <= rating <= 5.0):
            flash("Rating must be between 1.0 and 5.0.", "danger")
            return render_template('admin_add.html')

        if students < 0:
            flash("Students enrolled cannot be negative.", "danger")
            return render_template('admin_add.html')

        conn = get_db()
        conn.execute(
            """INSERT INTO courses
               (title,instructor,category,level,duration,rating,students,description,color,image_url)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (title, instructor, category, level, duration, rating, students, description, color, image_url)
        )
        conn.commit()
        conn.close()

        flash(f'Course "{title}" added successfully!', "success")
        return redirect('/admin/courses')

    return render_template('admin_add.html')


@app.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    """Admin functionality to edit an existing course."""
    conn   = get_db()
    course = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect('/admin/courses')

    if request.method == 'POST':
        if not validate_csrf():
            conn.close()
            return redirect(f'/admin/courses/edit/{course_id}')

        title       = request.form['title'].strip()
        instructor  = request.form['instructor'].strip()
        category    = request.form['category']
        level       = request.form['level']
        duration    = request.form['duration'].strip()
        description = request.form['description'].strip()
        color       = request.form['color']
        image_url   = request.form.get('image_url', '').strip()

        # File upload takes priority over URL
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            filename  = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_url = f'/static/uploads/{filename}'

        # If neither provided, keep the existing image
        if not image_url:
            image_url = course['image_url'] or ''

        if not title or not instructor or not duration or not description:
            flash("All text fields are required and cannot be blank.", "danger")
            conn.close()
            return render_template('admin_edit.html', course=course)

        try:
            rating   = float(request.form['rating'])
            students = int(request.form['students'])
        except ValueError:
            flash("Rating and Students must be valid numbers.", "danger")
            conn.close()
            return render_template('admin_edit.html', course=course)

        if not (1.0 <= rating <= 5.0):
            flash("Rating must be between 1.0 and 5.0.", "danger")
            conn.close()
            return render_template('admin_edit.html', course=course)

        if students < 0:
            flash("Students enrolled cannot be negative.", "danger")
            conn.close()
            return render_template('admin_edit.html', course=course)

        conn.execute(
            """UPDATE courses SET
               title=?,instructor=?,category=?,level=?,duration=?,
               rating=?,students=?,description=?,color=?,image_url=?
               WHERE id=?""",
            (title, instructor, category, level, duration,
             rating, students, description, color, image_url, course_id)
        )
        conn.commit()
        conn.close()

        flash(f'Course "{title}" updated successfully!', "success")
        return redirect('/admin/courses')

    conn.close()
    return render_template('admin_edit.html', course=course)


@app.route('/admin/courses/delete/<int:course_id>', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    """Admin functionality to permanently delete a course."""
    if not validate_csrf():
        return redirect('/admin/courses')

    conn   = get_db()
    course = conn.execute(
        "SELECT title FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if course:
        conn.execute("DELETE FROM enrollments WHERE course_id = ?", (course_id,))
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash(f'Course "{course["title"]}" deleted.', "success")
    else:
        flash("Course not found.", "danger")

    conn.close()
    return redirect('/admin/courses')


# -------------------------------------------------------------------
# REVIEWS (#11)
# -------------------------------------------------------------------

@app.route('/review/<int:course_id>', methods=['POST'])
def submit_review(course_id):
    """Submit a rating and comment for a course."""
    guard = login_required()
    if guard: return guard
    
    conn = get_db()
    
    if not conn.execute(
        "SELECT id FROM enrollments WHERE user_id=? AND course_id=?", 
        (session['user_id'], course_id)
    ).fetchone():
        conn.close()
        flash("You must be enrolled to leave a review.", "warning")
        return redirect(f'/course/{course_id}')
        
    try:
        rating = int(request.form['rating'])
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        conn.close()
        flash("Please select a rating between 1 and 5.", "danger")
        return redirect(f'/course/{course_id}')
        
    comment = request.form.get('comment', '').strip()[:500]
    
    conn.execute("""
        INSERT INTO reviews (user_id, course_id, rating, comment)
        VALUES (?,?,?,?)
        ON CONFLICT(user_id, course_id) DO UPDATE SET
            rating=excluded.rating,
            comment=excluded.comment,
            created_at=CURRENT_TIMESTAMP
    """, (session['user_id'], course_id, rating, comment))
    
    conn.commit()
    conn.close()
    
    flash("Your review has been submitted!", "success")
    return redirect(f'/course/{course_id}#reviews')


@app.route('/review/<int:course_id>/delete', methods=['POST'])
def delete_review(course_id):
    """Remove a previously submitted review."""
    guard = login_required()
    if guard: return guard
    
    conn = get_db()
    conn.execute(
        "DELETE FROM reviews WHERE user_id=? AND course_id=?", 
        (session['user_id'], course_id)
    )
    conn.commit()
    conn.close()
    
    flash("Your review has been removed.", "info")
    return redirect(f'/course/{course_id}#reviews')


# -------------------------------------------------------------------
# CERTIFICATE (#12)
# -------------------------------------------------------------------

@app.route('/certificate/<int:enrollment_id>')
def certificate(enrollment_id):
    """View certificate if course is completed 100%."""
    guard = login_required()
    if guard: return guard
    
    conn = get_db()
    row  = conn.execute("""
        SELECT e.*, c.title as course_title, c.instructor, c.category, c.duration, c.color, u.username
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        JOIN users u   ON u.id = e.user_id
        WHERE e.id=? AND e.user_id=?
    """, (enrollment_id, session['user_id'])).fetchone()
    conn.close()
    
    if not row:
        flash("Certificate not found.", "danger")
        return redirect('/my-learning')
        
    if row['progress'] < 100:
        flash("Complete the course 100% to earn your certificate.", "warning")
        return redirect('/my-learning')
        
    return render_template('certificate.html', e=row)


# -------------------------------------------------------------------
# REST API (#14)
# -------------------------------------------------------------------

@app.route('/api/courses')
@csrf.exempt
def api_courses():
    """Retrieve JSON dump of all courses."""
    conn    = get_db()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return jsonify([dict(c) for c in courses])


@app.route('/api/courses/<int:course_id>')
@csrf.exempt
def api_course_detail(course_id):
    """Retrieve detailed JSON dump for a specific course including reviews data."""
    conn   = get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    
    if not course:
        conn.close()
        return jsonify({"error": "Course not found"}), 404
        
    avg = conn.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE course_id=?", 
        (course_id,)
    ).fetchone()
    conn.close()
    
    data = dict(course)
    data['live_rating']  = round(avg[0], 2) if avg[0] else None
    data['review_count'] = avg[1]
    
    return jsonify(data)


# -------------------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------------------

@app.errorhandler(429)
def rate_limit_handler(e):
    """Render rate-limit exceeded flash message."""
    flash("Too many login attempts. Please wait a minute and try again.", "danger")
    return redirect('/login')

@app.errorhandler(404)
def page_not_found(e):
    """Render custom 404 page for missing endpoints."""
    return render_template('404.html'), 404


# -------------------------------------------------------------------
# MAIN EXECUTION
# -------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)