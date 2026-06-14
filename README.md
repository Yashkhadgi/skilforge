Then open it in VS Code (code README.md or just click it), and paste this:
markdown# SkillForge — Learning Management System

A full-stack LMS built with Python, Flask, and SQLite. Supports user authentication, course enrollment, progress tracking, role-based admin panel, REST API, and more.

## Features

### User Features
- User registration & login with hashed passwords (Werkzeug)
- Email format validation and strong password enforcement (min 8 chars, uppercase, lowercase, number, special character)
- Session-based authentication with timeout
- Browse, search, and filter courses by category
- Enroll in courses and track progress
- Submit course reviews and ratings
- Earn certificates on 100% course completion
- Forgot password via OTP (sent to email)

### Admin Features
- Role-Based Access Control (Admin / User)
- Admin dashboard with platform stats
- Full CRUD on courses (with image upload)
- Manage users — promote/demote, delete
- Audit log of all admin actions
- Analytics dashboard with charts (enrollments, ratings, user growth)
- SMTP settings panel (configure email for OTP — stored securely in DB)
- Export users/courses as CSV

### REST API (v1)
- `/api/v1/login` — Admin login, returns API key
- `/api/v1/me` — Current user profile + enrollments
- `/api/v1/courses` — CRUD with filtering, sorting, pagination
- `/api/v1/users` — Admin-only user list
- Authenticated via `X-API-Key` header

## Tech Stack
- **Backend:** Python 3, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, Bootstrap, Chart.js
- **Security:** Flask-WTF (CSRF), Flask-Limiter (rate limiting), Werkzeug (password hashing)
- **Email:** Flask-Mail / smtplib

## Setup & Installation

```bash
# Clone the repo
git clone 
cd skillforge

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

App runs at `http://127.0.0.1:5000`

## Default Admin Credentials
- Username: `admin`
- Password: `admin123` (set via `ADMIN_PASSWORD` env variable, change after first login)

## Environment Variables (optional)
Create a `.env` file:
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=your-admin-password

## Project Structure
skillforge/
├── app.py              # Main Flask app & routes
├── api_routes.py        # REST API blueprint (v1)
├── decorators.py         # Auth decorators (login_required, admin_required)
├── database.db           # SQLite database (gitignored)
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JS, uploaded images
└── requirements.txt

## API Testing
Use Postman or curl with `X-API-Key` header for admin endpoints:
```bash
curl -H "X-API-Key: <your-key>" http://127.0.0.1:5000/api/v1/courses
```

## License
This project was built as part of an internship assignment.
Save the file — done!