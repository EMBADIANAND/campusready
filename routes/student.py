import logging
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database import get_connection
from utils import validate_email, validate_cgpa, sanitize_str, server_error, student_required

logger    = logging.getLogger(__name__)
student_bp = Blueprint('student', __name__)
bcrypt     = Bcrypt()   # used only for check; hashing done via app-level bcrypt

# ─────────────────────────────────────────────────────────
# POST /api/student/register
# ─────────────────────────────────────────────────────────
@student_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    # ── Validate required fields ──────────────────────
    required = ['name', 'email', 'password', 'college', 'branch', 'year', 'cgpa']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # ── Validate email format ─────────────────────────
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    # ── Validate password strength ────────────────────
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # ── Validate CGPA ─────────────────────────────────
    cgpa, cgpa_err = validate_cgpa(data['cgpa'])
    if cgpa_err:
        return jsonify({'error': cgpa_err}), 400

    name    = sanitize_str(data['name'],    100)
    college = sanitize_str(data['college'], 200)
    branch  = sanitize_str(data['branch'],  50)
    year    = sanitize_str(data['year'],    20)
    email   = data['email'].strip().lower()

    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM students WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 409

            cursor.execute("""
                INSERT INTO students (name, email, password, college, branch, year, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, email, hashed_pw, college, branch, year, cgpa))
            conn.commit()

        return jsonify({'message': f'Welcome to CampusReady, {name}!'}), 201

    except Exception as e:
        conn.rollback()
        return server_error(e, 'student.register')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/student/login
# ─────────────────────────────────────────────────────────
@student_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # FIX: generic message — don't reveal whether email exists
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
            student = cursor.fetchone()

        if not student or not bcrypt.check_password_hash(student['password'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        # identity = plain int string (student)
        token = create_access_token(identity=str(student['id']))

        return jsonify({
            'message': f"Welcome back, {student['name']}!",
            'token'  : token,
            'student': {
                'id'     : student['id'],
                'name'   : student['name'],
                'email'  : student['email'],
                'college': student['college'],
                'branch' : student['branch'],
                'year'   : student['year'],
                'cgpa'   : str(student['cgpa']),
            }
        }), 200

    except Exception as e:
        return server_error(e, 'student.login')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/student/dashboard
# ─────────────────────────────────────────────────────────
@student_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@student_required
def dashboard():
    student_id = get_jwt_identity()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, college, branch, year, cgpa,
                       aptitude_score, reasoning_score, coding_score,
                       communication_score, readiness_score, quizzes_taken
                FROM students WHERE id = %s
            """, (student_id,))
            student = cursor.fetchone()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        return jsonify({'student': student}), 200

    except Exception as e:
        return server_error(e, 'student.dashboard')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/student/all  — for company portal (paginated)
# ─────────────────────────────────────────────────────────
@student_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_students():
    branch = sanitize_str(request.args.get('branch', ''), 50)
    year   = sanitize_str(request.args.get('year',   ''), 20)
    name   = sanitize_str(request.args.get('name',   ''), 100)

    # FIX: pagination — max 50 per page
    try:
        page     = max(1, int(request.args.get('page', 1)))
        per_page = min(50, int(request.args.get('per_page', 20)))
    except ValueError:
        page, per_page = 1, 20
    offset = (page - 1) * per_page

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query  = """
                SELECT id, name, college, branch, year, cgpa,
                       aptitude_score, coding_score, communication_score,
                       reasoning_score, readiness_score
                FROM students WHERE 1=1
            """
            params = []
            if branch:
                query += " AND branch = %s";  params.append(branch)
            if year:
                query += " AND year = %s";    params.append(year)
            if name:
                query += " AND name LIKE %s"; params.append(f"%{name}%")

            query += " ORDER BY readiness_score DESC LIMIT %s OFFSET %s"
            params += [per_page, offset]

            cursor.execute(query, params)
            students = cursor.fetchall()

            # total count for pagination info
            cursor.execute("SELECT COUNT(*) as total FROM students WHERE 1=1", [])
            total = cursor.fetchone()['total']

        return jsonify({
            'students' : students,
            'page'     : page,
            'per_page' : per_page,
            'total'    : total
        }), 200

    except Exception as e:
        return server_error(e, 'student.all')
    finally:
        conn.close()
