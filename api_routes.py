"""
api_routes.py — REST API Blueprint for SkillForge.

Registers all JSON API endpoints under the 'api' blueprint.
All responses use a standard envelope:
    { "success": bool, "message": str, "data": dict | list | None }

Courses API (public GET, admin-only POST/PUT/DELETE):
    GET    /api/courses
    GET    /api/courses/<id>
    POST   /api/courses
    PUT    /api/courses/<id>
    DELETE /api/courses/<id>

Users API (admin-only):
    GET    /api/users
    GET    /api/users/<id>
"""

from flask import Blueprint, jsonify, request, session
from decorators import is_admin
import sqlite3

api_bp = Blueprint('api', __name__)

# -----------------------------------------------------------------------
# Database helper (local to blueprint — avoids circular import)
# -----------------------------------------------------------------------

def _get_db():
    """Open and return a SQLite connection with Row factory."""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def _ok(data=None, message="OK", status=200):
    """Build a standard success response envelope."""
    return jsonify({"success": True, "message": message, "data": data}), status


def _err(message="Error", status=400, data=None):
    """Build a standard error response envelope."""
    return jsonify({"success": False, "message": message, "data": data}), status


def _admin_guard():
    """
    Return an error response if the caller is not an authenticated admin.
    Returns None if access is allowed.
    """
    if 'user_id' not in session:
        return _err("Authentication required. Please log in.", 401)
    if not is_admin():
        return _err("Access denied. Admin privileges required.", 403)
    return None  # access granted


# -----------------------------------------------------------------------
# COURSES API
# -----------------------------------------------------------------------

@api_bp.route('/api/courses', methods=['GET'])
def api_get_courses():
    """
    GET /api/courses
    Public. Returns all courses.
    Optional query params: ?category=Web  ?q=python
    """
    category = request.args.get('category', '').strip()
    q        = request.args.get('q', '').strip()

    conn = _get_db()
    if category and q:
        rows = conn.execute(
            "SELECT * FROM courses WHERE category=? AND (lower(title) LIKE ? OR lower(instructor) LIKE ?)",
            (category, f'%{q.lower()}%', f'%{q.lower()}%')
        ).fetchall()
    elif category:
        rows = conn.execute(
            "SELECT * FROM courses WHERE category=?", (category,)
        ).fetchall()
    elif q:
        rows = conn.execute(
            "SELECT * FROM courses WHERE lower(title) LIKE ? OR lower(instructor) LIKE ?",
            (f'%{q.lower()}%', f'%{q.lower()}%')
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()

    return _ok(data=[dict(r) for r in rows], message=f"{len(rows)} course(s) found.")


@api_bp.route('/api/courses/<int:course_id>', methods=['GET'])
def api_get_course(course_id):
    """
    GET /api/courses/<id>
    Public. Returns a single course including live rating data.
    """
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

    return _ok(data=data, message="Course retrieved successfully.")


@api_bp.route('/api/courses', methods=['POST'])
def api_create_course():
    """
    POST /api/courses
    Admin only. Creates a new course from JSON body.

    Required fields: title, instructor, category, level, duration,
                     rating (float 1-5), students (int >=0), description, color
    Optional fields: image_url
    """
    guard = _admin_guard()
    if guard:
        return guard

    body = request.get_json(silent=True) or {}

    # --- Validate required fields ---
    required = ['title', 'instructor', 'category', 'level',
                'duration', 'rating', 'students', 'description', 'color']
    missing  = [f for f in required if not body.get(f) and body.get(f) != 0]
    if missing:
        return _err(f"Missing required fields: {', '.join(missing)}", 400)

    title       = str(body['title']).strip()
    instructor  = str(body['instructor']).strip()
    category    = str(body['category']).strip()
    level       = str(body['level']).strip()
    duration    = str(body['duration']).strip()
    description = str(body['description']).strip()
    color       = str(body['color']).strip()
    image_url   = str(body.get('image_url', '')).strip()

    if not all([title, instructor, category, level, duration, description, color]):
        return _err("Fields cannot be empty or whitespace only.", 400)

    try:
        rating   = float(body['rating'])
        students = int(body['students'])
    except (ValueError, TypeError):
        return _err("'rating' must be a float and 'students' must be an integer.", 400)

    if not (1.0 <= rating <= 5.0):
        return _err("'rating' must be between 1.0 and 5.0.", 400)

    if students < 0:
        return _err("'students' cannot be negative.", 400)

    conn = _get_db()
    cur  = conn.execute(
        """INSERT INTO courses (title, instructor, category, level, duration,
           rating, students, description, color, image_url)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (title, instructor, category, level, duration,
         rating, students, description, color, image_url)
    )
    conn.commit()
    new_id = cur.lastrowid
    new_course = dict(conn.execute("SELECT * FROM courses WHERE id=?", (new_id,)).fetchone())
    conn.close()

    return _ok(data=new_course, message="Course created successfully.", status=201)


@api_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
def api_update_course(course_id):
    """
    PUT /api/courses/<id>
    Admin only. Updates an existing course (full or partial update).
    Unspecified fields retain their current values.
    """
    guard = _admin_guard()
    if guard:
        return guard

    conn   = _get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return _err("Course not found.", 404)

    body = request.get_json(silent=True) or {}

    # Merge: use provided value, fall back to existing
    title       = str(body.get('title',       course['title'])).strip()
    instructor  = str(body.get('instructor',  course['instructor'])).strip()
    category    = str(body.get('category',    course['category'])).strip()
    level       = str(body.get('level',       course['level'])).strip()
    duration    = str(body.get('duration',    course['duration'])).strip()
    description = str(body.get('description', course['description'])).strip()
    color       = str(body.get('color',       course['color'])).strip()
    image_url   = str(body.get('image_url',   course['image_url'] or '')).strip()

    try:
        rating   = float(body.get('rating',   course['rating']))
        students = int(body.get('students',   course['students']))
    except (ValueError, TypeError):
        conn.close()
        return _err("'rating' must be a float and 'students' must be an integer.", 400)

    if not (1.0 <= rating <= 5.0):
        conn.close()
        return _err("'rating' must be between 1.0 and 5.0.", 400)

    if students < 0:
        conn.close()
        return _err("'students' cannot be negative.", 400)

    conn.execute(
        """UPDATE courses SET title=?, instructor=?, category=?, level=?,
           duration=?, rating=?, students=?, description=?, color=?, image_url=?
           WHERE id=?""",
        (title, instructor, category, level, duration,
         rating, students, description, color, image_url, course_id)
    )
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())
    conn.close()

    return _ok(data=updated, message="Course updated successfully.")


@api_bp.route('/api/courses/<int:course_id>', methods=['DELETE'])
def api_delete_course(course_id):
    """
    DELETE /api/courses/<id>
    Admin only. Permanently deletes a course and its enrollments/reviews.
    """
    guard = _admin_guard()
    if guard:
        return guard

    conn   = _get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return _err("Course not found.", 404)

    title = course['title']
    conn.execute("DELETE FROM enrollments WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM reviews     WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM courses     WHERE id=?",        (course_id,))
    conn.commit()
    conn.close()

    return _ok(data={"deleted_id": course_id}, message=f'Course "{title}" deleted successfully.')


# -----------------------------------------------------------------------
# USERS API
# -----------------------------------------------------------------------

@api_bp.route('/api/users', methods=['GET'])
def api_get_users():
    """
    GET /api/users
    Admin only. Returns all registered users (passwords excluded).
    """
    guard = _admin_guard()
    if guard:
        return guard

    conn  = _get_db()
    rows  = conn.execute(
        "SELECT id, username, email, is_admin, role FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()

    return _ok(data=[dict(r) for r in rows], message=f"{len(rows)} user(s) found.")


@api_bp.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """
    GET /api/users/<id>
    Admin only. Returns a single user with their enrollment count.
    """
    guard = _admin_guard()
    if guard:
        return guard

    conn = _get_db()
    user = conn.execute(
        "SELECT id, username, email, is_admin, role FROM users WHERE id=?", (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return _err("User not found.", 404)

    enroll_count = conn.execute(
        "SELECT COUNT(*) FROM enrollments WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    conn.close()

    data = dict(user)
    data['enrollment_count'] = enroll_count

    return _ok(data=data, message="User retrieved successfully.")
