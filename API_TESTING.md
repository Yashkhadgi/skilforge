# SkillForge — API Testing Guide

All REST API endpoints return JSON in a standard envelope:

```json
{
  "success": true | false,
  "message": "Human-readable status",
  "data": { ... } | [ ... ] | null
}
```

**Base URL:** `http://localhost:5000`

---

## Authentication Notes

| Endpoint Type | Auth Required |
|---|---|
| `GET /api/courses` | None (public) |
| `GET /api/courses/<id>` | None (public) |
| `POST /api/courses` | Must be logged-in **admin** |
| `PUT /api/courses/<id>` | Must be logged-in **admin** |
| `DELETE /api/courses/<id>` | Must be logged-in **admin** |
| `GET /api/users` | Must be logged-in **admin** |
| `GET /api/users/<id>` | Must be logged-in **admin** |

Admin auth is **session-based** (cookie). See [Postman Setup](#postman-setup) below.

---

## Courses API

### `GET /api/courses`

List all courses. Supports optional query filters.

**Query Parameters (all optional):**
- `category` — e.g. `Python`, `Web`, `AI`
- `q` — search term matched against title and instructor

**Example Request:**
```
GET http://localhost:5000/api/courses
GET http://localhost:5000/api/courses?category=Python
GET http://localhost:5000/api/courses?q=flask
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "8 course(s) found.",
  "data": [
    {
      "id": 1,
      "title": "Python Fundamentals",
      "instructor": "Arjun Mehta",
      "category": "Python",
      "level": "Beginner",
      "duration": "14 hrs",
      "rating": 4.8,
      "students": 12400,
      "description": "Master Python from scratch...",
      "color": "#4f8ef7",
      "image_url": ""
    }
  ]
}
```

---

### `GET /api/courses/<id>`

Get a single course with live rating data.

**Example Request:**
```
GET http://localhost:5000/api/courses/1
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "Course retrieved successfully.",
  "data": {
    "id": 1,
    "title": "Python Fundamentals",
    "instructor": "Arjun Mehta",
    "category": "Python",
    "level": "Beginner",
    "duration": "14 hrs",
    "rating": 4.8,
    "students": 12400,
    "description": "Master Python from scratch...",
    "color": "#4f8ef7",
    "image_url": "",
    "live_rating": 4.75,
    "review_count": 12
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "message": "Course not found.",
  "data": null
}
```

---

### `POST /api/courses` *(Admin only)*

Create a new course.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "title":       "Django REST Framework",
  "instructor":  "Rahul Sharma",
  "category":    "Web",
  "level":       "Intermediate",
  "duration":    "16 hrs",
  "rating":      4.6,
  "students":    3200,
  "description": "Build powerful APIs with Django REST Framework. Serializers, ViewSets, auth.",
  "color":       "#0ea5e9",
  "image_url":   ""
}
```

**Required Fields:** `title`, `instructor`, `category`, `level`, `duration`, `rating`, `students`, `description`, `color`

**Example Response (201):**
```json
{
  "success": true,
  "message": "Course created successfully.",
  "data": {
    "id": 9,
    "title": "Django REST Framework",
    "instructor": "Rahul Sharma",
    "category": "Web",
    "level": "Intermediate",
    "duration": "16 hrs",
    "rating": 4.6,
    "students": 3200,
    "description": "Build powerful APIs with Django REST Framework...",
    "color": "#0ea5e9",
    "image_url": ""
  }
}
```

**Error Response — Not Admin (403):**
```json
{
  "success": false,
  "message": "Access denied. Admin privileges required.",
  "data": null
}
```

**Error Response — Missing Fields (400):**
```json
{
  "success": false,
  "message": "Missing required fields: rating, students",
  "data": null
}
```

---

### `PUT /api/courses/<id>` *(Admin only)*

Update an existing course. Only send the fields you want to change (partial update supported).

**Request Headers:**
```
Content-Type: application/json
```

**Request Body (partial update example):**
```json
{
  "rating": 4.9,
  "students": 14000
}
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "Course updated successfully.",
  "data": {
    "id": 1,
    "title": "Python Fundamentals",
    "instructor": "Arjun Mehta",
    "rating": 4.9,
    "students": 14000,
    ...
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "message": "Course not found.",
  "data": null
}
```

---

### `DELETE /api/courses/<id>` *(Admin only)*

Permanently delete a course and all its enrollments and reviews.

**Example Request:**
```
DELETE http://localhost:5000/api/courses/9
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "Course \"Django REST Framework\" deleted successfully.",
  "data": {
    "deleted_id": 9
  }
}
```

---

## Users API

### `GET /api/users` *(Admin only)*

List all registered users (passwords are never returned).

**Example Request:**
```
GET http://localhost:5000/api/users
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "3 user(s) found.",
  "data": [
    { "id": 1, "username": "admin", "email": "admin@skillforge.com", "is_admin": 1, "role": "admin" },
    { "id": 2, "username": "alice",  "email": "alice@example.com",   "is_admin": 0, "role": "user"  }
  ]
}
```

---

### `GET /api/users/<id>` *(Admin only)*

Get a single user with their enrollment count.

**Example Request:**
```
GET http://localhost:5000/api/users/2
```

**Example Response (200):**
```json
{
  "success": true,
  "message": "User retrieved successfully.",
  "data": {
    "id": 2,
    "username": "alice",
    "email": "alice@example.com",
    "is_admin": 0,
    "role": "user",
    "enrollment_count": 3
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "message": "User not found.",
  "data": null
}
```

---

## Error Reference

| Status | Meaning |
|---|---|
| `200` | Success |
| `201` | Resource created |
| `400` | Bad request / validation error |
| `401` | Not logged in |
| `403` | Logged in but not admin |
| `404` | Resource not found |
| `500` | Server error |

---

## Postman Setup

Since the API uses Flask session cookies for admin authentication, follow these steps:

### Step 1 — Log in via browser
1. Open `http://localhost:5000/login` in your browser.
2. Log in as `admin` / `admin123` (default credentials).
3. Your browser now holds a session cookie.

### Step 2 — Extract the session cookie
1. Open **DevTools → Application → Cookies** → `http://localhost:5000`.
2. Copy the value of the `session` cookie.

### Step 3 — Set cookie in Postman
1. In Postman, open **Cookies** (top-right) → Add domain `localhost`.
2. Add a cookie: **Name** = `session`, **Value** = `<paste value>`, **Domain** = `localhost`.

### Step 4 — Send API requests
All admin-protected requests (`POST`, `PUT`, `DELETE`) will now work with your session cookie attached.

> **Tip:** Alternatively, use the Postman built-in browser (New → Request → Launch Browser) and log in through `http://localhost:5000/login`. Postman will capture the session cookie automatically.

---

## Quick cURL Test Examples

```bash
# List all courses (public)
curl http://localhost:5000/api/courses

# Get course #1 (public)
curl http://localhost:5000/api/courses/1

# Create a course (admin — replace SESSION_VALUE)
curl -X POST http://localhost:5000/api/courses \
  -H "Content-Type: application/json" \
  -b "session=SESSION_VALUE" \
  -d '{
    "title": "Vue.js Masterclass",
    "instructor": "Kavya Reddy",
    "category": "Web",
    "level": "Intermediate",
    "duration": "18 hrs",
    "rating": 4.7,
    "students": 5500,
    "description": "Build reactive UIs with Vue 3 Composition API.",
    "color": "#10b981"
  }'

# Update course #1 rating (admin)
curl -X PUT http://localhost:5000/api/courses/1 \
  -H "Content-Type: application/json" \
  -b "session=SESSION_VALUE" \
  -d '{"rating": 4.95}'

# Delete course #9 (admin)
curl -X DELETE http://localhost:5000/api/courses/9 \
  -b "session=SESSION_VALUE"

# List all users (admin)
curl http://localhost:5000/api/users \
  -b "session=SESSION_VALUE"
```
