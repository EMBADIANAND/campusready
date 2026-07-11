# ── Shared utilities used by all routes ───────────────
import re
import logging
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

# ── Role guards ────────────────────────────────────────
def student_required(fn):
    """Allow only student JWT tokens."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if not identity or identity.startswith(('company_', 'admin_')):
            return jsonify({'error': 'Students only'}), 403
        return fn(*args, **kwargs)
    return wrapper

def company_required(fn):
    """Allow only company JWT tokens."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if not identity or not identity.startswith('company_'):
            return jsonify({'error': 'Companies only'}), 403
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    """Allow only admin JWT tokens."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if not identity or not identity.startswith('admin_'):
            return jsonify({'error': 'Admins only'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ── Input validators ───────────────────────────────────
EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
PHONE_RE = re.compile(r'^\+?[\d\s\-]{7,15}$')

def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ''))

def validate_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone or ''))

def validate_cgpa(value) -> tuple:
    """Returns (float, error_message). error_message is None if valid."""
    try:
        cgpa = float(value)
        if not (0 <= cgpa <= 10):
            return None, 'CGPA must be between 0 and 10'
        return cgpa, None
    except (TypeError, ValueError):
        return None, 'CGPA must be a number'

def sanitize_str(value: str, max_len: int = 200) -> str:
    """Strip whitespace and truncate."""
    return str(value or '').strip()[:max_len]

# ── Safe error response ────────────────────────────────
def server_error(e: Exception, context: str = ''):
    """Log the real error, return a safe generic message."""
    logger.error(f"[{context}] {type(e).__name__}: {e}")
    return jsonify({'error': 'An internal error occurred. Please try again.'}), 500
