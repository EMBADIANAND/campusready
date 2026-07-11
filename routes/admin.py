import logging
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required
from config import Config
from database import get_connection
from utils import server_error, admin_required, sanitize_str, validate_email

logger   = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)
bcrypt   = Bcrypt()

# ─────────────────────────────────────────────────────────
# POST /api/admin/login
# FIX: admin now gets a real JWT — no more hardcoded check
# ─────────────────────────────────────────────────────────
@admin_bp.route('/login', methods=['POST'])
def login():
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''

    if not email or not pw:
        return jsonify({'error': 'Email and password required'}), 400

    # FIX: credentials from env (.env file), not hardcoded in source
    if email != Config.ADMIN_EMAIL.lower() or pw != Config.ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid admin credentials'}), 401

    # identity prefixed with 'admin_' so every route can verify role
    token = create_access_token(identity='admin_1')
    return jsonify({'message': 'Welcome, Admin!', 'token': token}), 200


# ─────────────────────────────────────────────────────────
# GET /api/admin/students
# FIX: now protected — requires valid admin JWT
# ─────────────────────────────────────────────────────────
@admin_bp.route('/students', methods=['GET'])
@jwt_required()
@admin_required
def get_students():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, branch, year, cgpa,
                       readiness_score, quizzes_taken, created_at
                FROM students
                ORDER BY readiness_score DESC
            """)
            students = cursor.fetchall()

        return jsonify({'students': students, 'total': len(students)}), 200

    except Exception as e:
        return server_error(e, 'admin.get_students')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/admin/companies
# ─────────────────────────────────────────────────────────
@admin_bp.route('/companies', methods=['GET'])
@jwt_required()
@admin_required
def get_companies():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, company_name, industry, email, contact_person, phone, created_at
                FROM companies
                ORDER BY created_at DESC
            """)
            companies = cursor.fetchall()

        return jsonify({'companies': companies, 'total': len(companies)}), 200

    except Exception as e:
        return server_error(e, 'admin.get_companies')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# PUT /api/admin/student/<id>
# ─────────────────────────────────────────────────────────
@admin_bp.route('/student/<int:student_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_student(student_id):
    data = request.get_json(silent=True) or {}

    required = ['name', 'branch', 'year', 'cgpa']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    from utils import validate_cgpa
    cgpa, err = validate_cgpa(data['cgpa'])
    if err:
        return jsonify({'error': err}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Student not found'}), 404

            cursor.execute("""
                UPDATE students
                SET name = %s, branch = %s, year = %s, cgpa = %s
                WHERE id = %s
            """, (
                sanitize_str(data['name'],   100),
                sanitize_str(data['branch'],  50),
                sanitize_str(data['year'],    20),
                cgpa,
                student_id
            ))
            conn.commit()

        return jsonify({'message': 'Student updated successfully!'}), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'admin.update_student')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# DELETE /api/admin/student/<id>
# ─────────────────────────────────────────────────────────
@admin_bp.route('/student/<int:student_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_student(student_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Student not found'}), 404

            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            conn.commit()

        return jsonify({'message': 'Student deleted successfully!'}), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'admin.delete_student')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# DELETE /api/admin/company/<id>
# ─────────────────────────────────────────────────────────
@admin_bp.route('/company/<int:company_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_company(company_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM companies WHERE id = %s", (company_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Company not found'}), 404

            cursor.execute("DELETE FROM companies WHERE id = %s", (company_id,))
            conn.commit()

        return jsonify({'message': 'Company deleted successfully!'}), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'admin.delete_company')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/admin/question
# ─────────────────────────────────────────────────────────
@admin_bp.route('/question', methods=['POST'])
@jwt_required()
@admin_required
def add_question():
    data = request.get_json(silent=True) or {}

    required = ['topic','question','option1','option2','option3','option4','correct_answer']
    for field in required:
        if data.get(field) is None:
            return jsonify({'error': f'{field} is required'}), 400

    valid_topics = {'aptitude','reasoning','coding','communication'}
    if data['topic'] not in valid_topics:
        return jsonify({'error': 'Invalid topic'}), 400

    try:
        correct = int(data['correct_answer'])
        if correct not in range(4):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'correct_answer must be 0, 1, 2, or 3'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO quiz_questions
                    (topic, question, option1, option2, option3, option4, correct_answer)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['topic'],
                sanitize_str(data['question'], 500),
                sanitize_str(data['option1'],  255),
                sanitize_str(data['option2'],  255),
                sanitize_str(data['option3'],  255),
                sanitize_str(data['option4'],  255),
                correct,
            ))
            conn.commit()

        return jsonify({'message': 'Question added successfully!'}), 201

    except Exception as e:
        conn.rollback()
        return server_error(e, 'admin.add_question')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# DELETE /api/admin/question/<id>
# ─────────────────────────────────────────────────────────
@admin_bp.route('/question/<int:question_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_question(question_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM quiz_questions WHERE id = %s", (question_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Question not found'}), 404

            cursor.execute("DELETE FROM quiz_questions WHERE id = %s", (question_id,))
            conn.commit()

        return jsonify({'message': 'Question deleted!'}), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'admin.delete_question')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/admin/questions?topic=aptitude
# ─────────────────────────────────────────────────────────
@admin_bp.route('/questions', methods=['GET'])
@jwt_required()
@admin_required
def get_questions():
    topic = (request.args.get('topic') or '').strip().lower()
    conn  = get_connection()
    try:
        with conn.cursor() as cursor:
            if topic:
                cursor.execute(
                    "SELECT * FROM quiz_questions WHERE topic = %s ORDER BY id",
                    (topic,)
                )
            else:
                cursor.execute("SELECT * FROM quiz_questions ORDER BY topic, id")
            questions = cursor.fetchall()

        return jsonify({'questions': questions, 'total': len(questions)}), 200

    except Exception as e:
        return server_error(e, 'admin.get_questions')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/admin/stats  — dashboard numbers
# ─────────────────────────────────────────────────────────
@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_stats():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM students")
            students = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM companies")
            companies = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM quiz_questions")
            questions = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM quiz_results")
            quizzes = cursor.fetchone()['total']

        return jsonify({
            'total_students' : students,
            'total_companies': companies,
            'total_questions': questions,
            'total_quizzes'  : quizzes,
        }), 200

    except Exception as e:
        return server_error(e, 'admin.stats')
    finally:
        conn.close()
