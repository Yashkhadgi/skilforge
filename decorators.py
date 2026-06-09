"""
decorators.py — Auth helpers and route decorators for SkillForge.

Provides:
    is_admin()        — True if the current session user has admin role.
    login_required    — Decorator that redirects to /login if unauthenticated.
    admin_required    — Decorator that returns 403 if not an admin.
"""

from functools import wraps
from flask import session, redirect, request, render_template


def is_admin():
    """Return True if the logged-in user has the 'admin' role."""
    return session.get('role') == 'admin'


def login_required(f):
    """
    Decorator: redirect to /login (with ?next=) if the user is not logged in.
    Preserves the originally requested URL so the user is sent back after login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(f'/login?next={request.path}')
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """
    Decorator: require admin role.
    - Unauthenticated users are redirected to /login.
    - Authenticated non-admins receive a 403 Forbidden page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if not is_admin():
            # Render proper 403 page instead of a flash+redirect
            return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated
