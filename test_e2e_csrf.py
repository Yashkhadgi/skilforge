import app as application
import json
import sqlite3
import re

application.app.config['TESTING'] = True
application.app.config['WTF_CSRF_ENABLED'] = False

client = application.app.test_client()

PASS = 0
FAIL = 0
BUGS = []

def check(label, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"✅ {label}")
    else:
        FAIL += 1
        BUGS.append(f"{label}: got {got}, expected {expected}")
        print(f"❌ {label}: got {got}, expected {expected}")

def check_in(label, substring, text):
    global PASS, FAIL
    if substring in text:
        PASS += 1
        print(f"✅ {label}")
    else:
        FAIL += 1
        BUGS.append(f"{label}: '{substring}' not found in response")
        print(f"❌ {label}: '{substring}' not found")

print("=========================================")
print("STEP 4: USER FLOW TESTING (NO CSRF)")
print("=========================================")
# Register
resp = client.post('/register', data={
    'username': 'e2e_user',
    'email': 'e2e@example.com',
    'password': 'password123'
}, follow_redirects=True)
check("Register User", resp.status_code, 200)
check_in("Register Success Flash", b"Account created! Please login.", resp.data)

# Login
resp = client.post('/login', data={
    'username': 'e2e_user',
    'password': 'password123'
}, follow_redirects=True)
check("Login User", resp.status_code, 200)
check_in("Dashboard rendered", b"Dashboard", resp.data)

# Enroll
resp = client.post('/enroll/1', follow_redirects=True)
check("Enroll in Course 1", resp.status_code, 200)

# Progress Update
conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
enrollment = conn.execute("SELECT id FROM enrollments WHERE user_id = (SELECT id FROM users WHERE username='e2e_user') AND course_id=1").fetchone()
conn.close()

if enrollment:
    resp = client.post(f'/update-progress/{enrollment["id"]}', data={'progress': '50'}, follow_redirects=True)
    check("Update Progress", resp.status_code, 200)
    check_in("Progress updated", b"Progress updated!", resp.data)

    # Review
    resp = client.post('/review/1', data={'rating': 4, 'comment': 'Great!'}, follow_redirects=True)
    check("Submit Review", resp.status_code, 200)
    check_in("Review submitted", b"Your review has been submitted!", resp.data)
else:
    print("❌ Could not find enrollment to test progress/review")
    FAIL += 1

# Logout
resp = client.get('/logout', follow_redirects=True)
check("Logout User", resp.status_code, 200)
check_in("Logout Flash", b"Logged out successfully.", resp.data)

print("\n=========================================")
print("STEP 5: ADMIN FLOW TESTING (NO CSRF)")
print("=========================================")
# Login as Admin
resp = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
check("Login Admin", resp.status_code, 200)

admin_routes = [
    ('/admin', 200),
    ('/users', 200),
    ('/admin/courses', 200),
    ('/admin/courses/add', 200),
]
for route, status in admin_routes:
    resp = client.get(route)
    check(f"ADMIN GET {route}", resp.status_code, status)

# Add Course
resp = client.post('/admin/courses/add', data={
    'title': 'E2E Course',
    'instructor': 'E2E Instructor',
    'category': 'Web',
    'level': 'Beginner',
    'duration': '10 hrs',
    'rating': '4.5',
    'students': '0',
    'description': 'E2E Description',
    'color': '#fff'
}, follow_redirects=True)
check("ADMIN POST /admin/courses/add", resp.status_code, 200)
check_in("Course Added Flash", b"added successfully!", resp.data)

# Get the newly added course ID
conn = sqlite3.connect('database.db')
course = conn.execute("SELECT id FROM courses WHERE title='E2E Course' ORDER BY id DESC LIMIT 1").fetchone()
conn.close()

if course:
    course_id = course[0]
    # Edit Course
    resp = client.post(f'/admin/courses/edit/{course_id}', data={
        'title': 'E2E Course Updated',
        'instructor': 'E2E Instructor',
        'category': 'Web',
        'level': 'Beginner',
        'duration': '10 hrs',
        'rating': '4.5',
        'students': '0',
        'description': 'E2E Description',
        'color': '#fff'
    }, follow_redirects=True)
    check(f"ADMIN POST /admin/courses/edit/{course_id}", resp.status_code, 200)
    check_in("Course Updated Flash", b"updated successfully!", resp.data)

    # Delete Course
    resp = client.post(f'/admin/courses/delete/{course_id}', follow_redirects=True)
    check(f"ADMIN POST /admin/courses/delete/{course_id}", resp.status_code, 200)
    check_in("Course Deleted Flash", b"deleted.", resp.data)
else:
    print("❌ Could not find added course to edit/delete")
    FAIL += 1

print("\n=========================================")
print("SUMMARY")
print("=========================================")
print(f"Total PASS: {PASS}")
print(f"Total FAIL: {FAIL}")
if BUGS:
    print("\nBUGS FOUND:")
    for b in BUGS:
        print(f"  - {b}")
