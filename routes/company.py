import logging
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database import get_connection
from utils import validate_email, validate_phone, sanitize_str, server_error, company_required

logger     = logging.getLogger(__name__)
company_bp = Blueprint('company', __name__)
bcrypt     = Bcrypt()

# ─────────────────────────────────────────────────────────
# POST /api/company/register
# ─────────────────────────────────────────────────────────
@company_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    required = ['company_name', 'industry', 'email', 'password', 'contact_person', 'phone']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # ── Validate ──────────────────────────────────────
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    if not validate_phone(data['phone']):
        return jsonify({'error': 'Invalid phone number'}), 400

    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    email        = data['email'].strip().lower()
    company_name = sanitize_str(data['company_name'],   150)
    industry     = sanitize_str(data['industry'],       100)
    contact      = sanitize_str(data['contact_person'], 100)
    phone        = sanitize_str(data['phone'],           20)
    website      = sanitize_str(data.get('website',''), 200)

    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM companies WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 409

            cursor.execute("""
                INSERT INTO companies
                    (company_name, industry, email, password, contact_person, phone, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (company_name, industry, email, hashed_pw, contact, phone, website))
            conn.commit()

        return jsonify({'message': f'Welcome to CampusReady, {company_name}!'}), 201

    except Exception as e:
        conn.rollback()
        return server_error(e, 'company.register')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/company/login
# ─────────────────────────────────────────────────────────
@company_bp.route('/login', methods=['POST'])
def login():
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''

    if not email or not pw:
        return jsonify({'error': 'Email and password are required'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM companies WHERE email = %s", (email,))
            company = cursor.fetchone()

        # FIX: generic message — don't reveal whether email exists
        if not company or not bcrypt.check_password_hash(company['password'], pw):
            return jsonify({'error': 'Invalid email or password'}), 401

        # identity prefixed with 'company_' so backend knows the role
        token = create_access_token(identity=f"company_{company['id']}")

        return jsonify({
            'message': f"Welcome, {company['company_name']}!",
            'token'  : token,
            'company': {
                'id'            : company['id'],
                'company_name'  : company['company_name'],
                'industry'      : company['industry'],
                'email'         : company['email'],
                'contact_person': company['contact_person'],
            }
        }), 200

    except Exception as e:
        return server_error(e, 'company.login')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/company/shortlist
# ─────────────────────────────────────────────────────────
@company_bp.route('/shortlist', methods=['POST'])
@jwt_required()
@company_required
def shortlist():
    identity   = get_jwt_identity()
    company_id = int(identity.replace('company_', ''))
    data       = request.get_json(silent=True) or {}
    student_id = data.get('student_id')

    if not student_id:
        return jsonify({'error': 'student_id is required'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Verify student exists
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Student not found'}), 404

            # Check duplicate
            cursor.execute("""
                SELECT id FROM shortlists
                WHERE company_id = %s AND student_id = %s
            """, (company_id, student_id))
            if cursor.fetchone():
                return jsonify({'error': 'Student already shortlisted'}), 409

            cursor.execute("""
                INSERT INTO shortlists (company_id, student_id)
                VALUES (%s, %s)
            """, (company_id, student_id))
            conn.commit()

        return jsonify({'message': 'Student shortlisted successfully!'}), 201

    except Exception as e:
        conn.rollback()
        return server_error(e, 'company.shortlist')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/company/shortlisted
# ─────────────────────────────────────────────────────────
@company_bp.route('/shortlisted', methods=['GET'])
@jwt_required()
@company_required
def get_shortlisted():
    identity   = get_jwt_identity()
    company_id = int(identity.replace('company_', ''))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.name, s.branch, s.cgpa, s.readiness_score,
                       sl.shortlisted_at
                FROM students s
                JOIN shortlists sl ON s.id = sl.student_id
                WHERE sl.company_id = %s
                ORDER BY sl.shortlisted_at DESC
            """, (company_id,))
            students = cursor.fetchall()

        return jsonify({'shortlisted': students}), 200

    except Exception as e:
        return server_error(e, 'company.shortlisted')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# DELETE /api/company/shortlist/<student_id>
# ─────────────────────────────────────────────────────────
@company_bp.route('/shortlist/<int:student_id>', methods=['DELETE'])
@jwt_required()
@company_required
def remove_shortlist(student_id):
    identity   = get_jwt_identity()
    company_id = int(identity.replace('company_', ''))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM shortlists
                WHERE company_id = %s AND student_id = %s
            """, (company_id, student_id))
            conn.commit()

        return jsonify({'message': 'Removed from shortlist'}), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'company.remove_shortlist')
    finally:
        conn.close()
