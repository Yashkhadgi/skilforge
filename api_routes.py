"""
api_routes.py — REST API Blueprint for SkillForge (v1).

All endpoints versioned under /api/v1/
All responses use standard envelope:
    { "success": bool, "message": str, "data": dict | list | None }

Auth:
    POST   /api/v1/login            -> returns api_key (stored in app_settings)

Courses API (public GET, admin POST/PUT/DELETE):
    GET    /api/v1/courses
    GET    /api/v1/courses/<id>
    POST   /api/v1/courses          [X-API-Key required]
    PUT    /api/v1/courses/<id>     [X-API-Key required]
    DELETE /api/v1/courses/<id>     [X-API-Key required]

Users API (admin-only):
    GET    /api/v1/users            [X-API-Key required]
    GET    /api/v1/users/<id>       [X-API-Key required]

Self:
    GET    /api/v1/me               [session or X-API-Key]
"""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from decorators import is_admin
import sqlite3
import secrets

api_bp = Blueprint('api', __name__)

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True,  "message": message, "data": data}), status

def _err(message="Error", status=400, data=None):
    return jsonify({"success": False, "message": message, "data": data}), status

def _get_setting(key, default=''):
    conn = _get_db()
    row  = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def _set_setting(key, value):
    conn = _get_db()
    conn.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

def _api_key_guard():
    """
    Allow access if:
    1. X-API-Key header matches stored api_key, OR
    2. Active admin session (fallback for browser-based testing)
    Returns None on success, error response otherwise.
    """
    api_key_header = request.headers.get('X-API-Key', '').strip()
    stored_key     = _get_setting('api_key', '')

    if api_key_header and stored_key and api_key_header == stored_key:
        return None  # valid API key

    # Fallback: session-based admin
    if 'user_id' in session and is_admin():
        return None

    if api_key_header:
        return _err("Invalid API key.", 401)
    return _err("Authentication required. Use X-API-Key header or log in as admin.", 401)

def _login_guard():
    """Allow any logged-in user (session-based)."""
    if 'user_id' not in session:
        return _err("Authentication required. Please log in.", 401)
    return None

# -----------------------------------------------------------------------
# AUTH
# -----------------------------------------------------------------------

@api_bp.route('/api/v1/login', methods=['POST'])
def api_login():
    """
    POST /api/v1/login
    Body: { "username": "...", "password": "..." }
    Returns api_key for admin users (store in app_settings).
    """
    body     = request.get_json(silent=True) or {}
    username = str(body.get('username', '')).strip()
    password = str(body.get('password', ''))

    if not username or not password:
        return _err("username and password are required.", 400)

    conn = _get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password'], password):
        return _err("Invalid credentials.", 401)

    if not user['is_admin']:
        return _err("API access requires admin privileges.", 403)

    # Generate and store API key
    new_key = secrets.token_hex(32)
    _set_setting('api_key', new_key)

    return _ok(
        data={"api_key": new_key, "username": username},
        message="Login successful. Include X-API-Key header in subsequent requests.",
        status=200
    )


# -----------------------------------------------------------------------
# SELF
# -----------------------------------------------------------------------

@api_bp.route('/api/v1/me', methods=['GET'])
def api_me():
    """
    GET /api/v1/me
    Returns profile and enrollments for the logged-in user (session-based).
    """
    guard = _login_guard()
    if guard:
        return guard

    user_id = session['user_id']
    conn    = _get_db()
    user    = conn.execute(
        "SELECT id,username,email,is_admin,role FROM users WHERE id=?", (user_id,)
    ).fetchone()
    enrolls = conn.execute("""
        SELECT c.id, c.title, c.instructor, c.category, e.progress, e.enrolled_at
        FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.user_id=?
        ORDER BY e.enrolled_at DESC
    """, (user_id,)).fetchall()
    conn.close()

    data = dict(user)
    data['enrollments'] = [dict(e) for e in enrolls]
    return _ok(data=data, message="Profile retrieved.")


# -----------------------------------------------------------------------
# COURSES API
# -----------------------------------------------------------------------

@api_bp.route('/api/v1/courses', methods=['GET'])
def api_get_courses():
    """
    GET /api/v1/courses
    Public. Query params: ?category=Web  ?q=python  ?sort=rating  ?page=1
    """
    category = request.args.get('category', '').strip()
    q        = request.args.get('q', '').strip()
    sort     = request.args.get('sort', '').strip()   # rating | students | title
    page     = max(1, request.args.get('page', 1, type=int))
    per_page = 10

    base = "SELECT * FROM courses WHERE 1=1"
    params = []

    if category:
        base += " AND category=?"
        params.append(category)
    if q:
        base += " AND (lower(title) LIKE ? OR lower(instructor) LIKE ?)"
        params += [f'%{q.lower()}%', f'%{q.lower()}%']

    sort_map = {'rating': 'rating DESC', 'students': 'students DESC', 'title': 'title ASC'}
    order    = sort_map.get(sort, 'id ASC')
    base    += f" ORDER BY {order}"

    # Pagination
    count_sql = base.replace("SELECT *", "SELECT COUNT(*)")
    conn      = _get_db()
    total     = conn.execute(count_sql, params).fetchone()[0]
    rows      = conn.execute(base + " LIMIT ? OFFSET ?", params + [per_page, (page-1)*per_page]).fetchall()
    conn.close()

    return _ok(
        data={
            "courses":     [dict(r) for r in rows],
            "total":       total,
            "page":        page,
            "per_page":    per_page,
            "total_pages": (total + per_page - 1) // per_page
        },
        message=f"{total} course(s) found."
    )


@api_bp.route('/api/v1/courses/<int:course_id>', methods=['GET'])
def api_get_course(course_id):
    """GET /api/v1/courses/<id> — Public."""
    conn   = _get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()

    if not course:
        conn.close()
        return _err("Course not found.", 404)

    avg_row = conn.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE course_id=?", (course_id,)
    ).fetchone()
    conn.close()

    data = dict(course)
    data['live_rating']  = round(avg_row[0], 2) if avg_row[0] else None
    data['review_count'] = avg_row[1]
    return _ok(data=data, message="Course retrieved.")


@api_bp.route('/api/v1/courses', methods=['POST'])
def api_create_course():
    """POST /api/v1/courses — Admin only (X-API-Key)."""
    guard = _api_key_guard()
    if guard:
        return guard

    body     = request.get_json(silent=True) or {}
    required = ['title','instructor','category','level','duration','rating','students','description','color']
    missing  = [f for f in required if f not in body]
    if missing:
        return _err(f"Missing fields: {', '.join(missing)}", 400)

    try:
        rating   = float(body['rating'])
        students = int(body['students'])
    except (ValueError, TypeError):
        return _err("'rating' must be float, 'students' must be int.", 400)

    if not (1.0 <= rating <= 5.0):
        return _err("'rating' must be between 1.0 and 5.0.", 400)
    if students < 0:
        return _err("'students' cannot be negative.", 400)

    conn = _get_db()
    cur  = conn.execute(
        """INSERT INTO courses (title,instructor,category,level,duration,
           rating,students,description,color,image_url) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (str(body['title']).strip(), str(body['instructor']).strip(),
         str(body['category']).strip(), str(body['level']).strip(),
         str(body['duration']).strip(), rating, students,
         str(body['description']).strip(), str(body['color']).strip(),
         str(body.get('image_url','')).strip())
    )
    conn.commit()
    new_course = dict(conn.execute("SELECT * FROM courses WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return _ok(data=new_course, message="Course created.", status=201)


@api_bp.route('/api/v1/courses/<int:course_id>', methods=['PUT'])
def api_update_course(course_id):
    """PUT /api/v1/courses/<id> — Admin only (X-API-Key). Partial update supported."""
    guard = _api_key_guard()
    if guard:
        return guard

    conn   = _get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return _err("Course not found.", 404)

    body = request.get_json(silent=True) or {}

    try:
        rating   = float(body.get('rating',   course['rating']))
        students = int(body.get('students', course['students']))
    except (ValueError, TypeError):
        conn.close()
        return _err("'rating' must be float, 'students' must be int.", 400)

    conn.execute(
        """UPDATE courses SET title=?,instructor=?,category=?,level=?,duration=?,
           rating=?,students=?,description=?,color=?,image_url=? WHERE id=?""",
        (str(body.get('title',       course['title'])).strip(),
         str(body.get('instructor',  course['instructor'])).strip(),
         str(body.get('category',    course['category'])).strip(),
         str(body.get('level',       course['level'])).strip(),
         str(body.get('duration',    course['duration'])).strip(),
         rating, students,
         str(body.get('description', course['description'])).strip(),
         str(body.get('color',       course['color'])).strip(),
         str(body.get('image_url',   course['image_url'] or '')).strip(),
         course_id)
    )
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())
    conn.close()
    return _ok(data=updated, message="Course updated.")


@api_bp.route('/api/v1/courses/<int:course_id>', methods=['DELETE'])
def api_delete_course(course_id):
    """DELETE /api/v1/courses/<id> — Admin only (X-API-Key)."""
    guard = _api_key_guard()
    if guard:
        return guard

    conn   = _get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return _err("Course not found.", 404)

    conn.execute("DELETE FROM enrollments WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM reviews     WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM courses     WHERE id=?",        (course_id,))
    conn.commit()
    conn.close()
    return _ok(data={"deleted_id": course_id}, message=f'Course "{course["title"]}" deleted.')


# -----------------------------------------------------------------------
# USERS API
# -----------------------------------------------------------------------

@api_bp.route('/api/v1/users', methods=['GET'])
def api_get_users():
    """GET /api/v1/users — Admin only (X-API-Key)."""
    guard = _api_key_guard()
    if guard:
        return guard

    conn = _get_db()
    rows = conn.execute(
        "SELECT id,username,email,is_admin,role FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return _ok(data=[dict(r) for r in rows], message=f"{len(rows)} user(s).")


@api_bp.route('/api/v1/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """GET /api/v1/users/<id> — Admin only (X-API-Key)."""
    guard = _api_key_guard()
    if guard:
        return guard

    conn = _get_db()
    user = conn.execute(
        "SELECT id,username,email,is_admin,role FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if not user:
        conn.close()
        return _err("User not found.", 404)

    count = conn.execute("SELECT COUNT(*) FROM enrollments WHERE user_id=?", (user_id,)).fetchone()[0]
    conn.close()

    data = dict(user)
    data['enrollment_count'] = count
    return _ok(data=data, message="User retrieved.")


# -----------------------------------------------------------------------
# Backward-compat aliases (old /api/ URLs still work)
# -----------------------------------------------------------------------
@api_bp.route('/api/courses',              methods=['GET'])
def _compat_courses():          return api_get_courses()

@api_bp.route('/api/courses/<int:cid>',   methods=['GET'])
def _compat_course(cid):        return api_get_course(cid)

@api_bp.route('/api/users',               methods=['GET'])
def _compat_users():            return api_get_users()

@api_bp.route('/api/users/<int:uid>',     methods=['GET'])
def _compat_user(uid):          return api_get_user(uid)
