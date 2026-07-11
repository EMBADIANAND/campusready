import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_connection
from utils import server_error, student_required

logger  = logging.getLogger(__name__)
quiz_bp = Blueprint('quiz', __name__)

VALID_TOPICS = {'aptitude', 'reasoning', 'coding', 'communication'}

# ─────────────────────────────────────────────────────────
# GET /api/quiz/questions?topic=aptitude
# ─────────────────────────────────────────────────────────
@quiz_bp.route('/questions', methods=['GET'])
@jwt_required()
@student_required          # FIX: only students can take quizzes
def get_questions():
    topic = (request.args.get('topic') or '').strip().lower()

    if topic not in VALID_TOPICS:
        return jsonify({'error': f'Topic must be one of: {", ".join(VALID_TOPICS)}'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, question, option1, option2, option3, option4
                FROM quiz_questions
                WHERE topic = %s
                ORDER BY RAND()
                LIMIT 10
            """, (topic,))
            rows = cursor.fetchall()

        if not rows:
            return jsonify({'error': 'No questions found for this topic'}), 404

        # FIX: correct_answer never sent to frontend — server grades only
        questions = [
            {
                'id'      : row['id'],
                'question': row['question'],
                'options' : [row['option1'], row['option2'], row['option3'], row['option4']]
            }
            for row in rows
        ]

        return jsonify({'questions': questions, 'topic': topic, 'total': len(questions)}), 200

    except Exception as e:
        return server_error(e, 'quiz.get_questions')
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/quiz/submit
# Body: { topic, answers: {"12": 2, "13": 0, ...} }
# ─────────────────────────────────────────────────────────
@quiz_bp.route('/submit', methods=['POST'])
@jwt_required()
@student_required          # FIX: only students can submit
def submit_quiz():
    student_id = get_jwt_identity()
    data       = request.get_json(silent=True) or {}

    topic   = (data.get('topic') or '').strip().lower()
    answers = data.get('answers') or {}

    if topic not in VALID_TOPICS:
        return jsonify({'error': 'Invalid topic'}), 400

    if not answers or not isinstance(answers, dict):
        return jsonify({'error': 'answers must be a non-empty object'}), 400

    # FIX: validate answer values are integers 0-3
    for qid, sel in answers.items():
        try:
            if int(sel) not in range(4):
                return jsonify({'error': 'Each answer must be 0, 1, 2, or 3'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Answer values must be integers'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # ── Fetch correct answers from DB ──────────
            question_ids = list(answers.keys())
            fmt = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"""
                SELECT id, correct_answer, topic FROM quiz_questions
                WHERE id IN ({fmt}) AND topic = %s
            """, (*question_ids, topic))   # FIX: also check topic matches

            rows = cursor.fetchall()

        if not rows:
            return jsonify({'error': 'No valid questions found'}), 400

        # ── Grade ──────────────────────────────────────
        correct_map = {str(r['id']): r['correct_answer'] for r in rows}
        total       = len(correct_map)
        correct     = sum(
            1 for qid, sel in answers.items()
            if str(qid) in correct_map and correct_map[str(qid)] == int(sel)
        )
        percent = round((correct / total) * 100) if total > 0 else 0

        # ── Persist ────────────────────────────────────
        score_col = f"{topic}_score"   # safe: topic validated against whitelist above

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO quiz_results (student_id, topic, score)
                VALUES (%s, %s, %s)
            """, (student_id, topic, percent))

            cursor.execute(f"""
                UPDATE students
                SET {score_col}    = %s,
                    quizzes_taken  = quizzes_taken + 1
                WHERE id = %s
            """, (percent, student_id))

            # FIX: only average topics the student has actually attempted
            cursor.execute("""
                UPDATE students
                SET readiness_score = (
                    (CASE WHEN aptitude_score      > 0 THEN aptitude_score      ELSE 0 END) +
                    (CASE WHEN reasoning_score     > 0 THEN reasoning_score     ELSE 0 END) +
                    (CASE WHEN coding_score        > 0 THEN coding_score        ELSE 0 END) +
                    (CASE WHEN communication_score > 0 THEN communication_score ELSE 0 END)
                ) / GREATEST(
                    (CASE WHEN aptitude_score      > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN reasoning_score     > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN coding_score        > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN communication_score > 0 THEN 1 ELSE 0 END),
                    1
                )
                WHERE id = %s
            """, (student_id,))

            conn.commit()

        if percent >= 80:
            msg = 'Excellent! You are placement ready! 🔥'
        elif percent >= 60:
            msg = 'Good job! Keep practicing! 💪'
        else:
            msg = 'Keep going! Practice makes perfect! 📚'

        return jsonify({
            'score'  : correct,
            'total'  : total,
            'percent': percent,
            'message': msg,
        }), 200

    except Exception as e:
        conn.rollback()
        return server_error(e, 'quiz.submit')
    finally:
        conn.close()
