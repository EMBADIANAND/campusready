import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_connection
from utils import server_error, student_required

logger  = logging.getLogger(__name__)
quiz_bp = Blueprint('quiz', __name__)

VALID_TOPICS = {'aptitude', 'reasoning', 'coding', 'communication'}
QUESTIONS_PER_QUIZ = 10

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
                LIMIT %s
            """, (topic, QUESTIONS_PER_QUIZ))
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

    # Each answer is 0-3, or null for a question left unanswered (counts as wrong)
    clean = {}
    for qid, sel in answers.items():
        if sel is None:
            clean[str(qid)] = None
            continue
        try:
            if int(sel) not in range(4):
                return jsonify({'error': 'Each answer must be 0, 1, 2, 3 or null'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Answer values must be integers or null'}), 400
        clean[str(qid)] = int(sel)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # ── Fetch correct answers from DB ──────────
            question_ids = list(clean.keys())
            fmt = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"""
                SELECT id, correct_answer, topic FROM quiz_questions
                WHERE id IN ({fmt}) AND topic = %s
            """, (*question_ids, topic))   # FIX: also check topic matches
            rows = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) AS n FROM quiz_questions WHERE topic = %s", (topic,))
            expected = min(QUESTIONS_PER_QUIZ, cursor.fetchone()['n'])

        if not rows:
            return jsonify({'error': 'No valid questions found'}), 400

        # Every question that was served must be submitted (answered or null)
        if len(rows) != len(clean) or len(clean) != expected:
            return jsonify({'error': f'Submit all {expected} questions of the quiz (use null for unanswered)'}), 400

        # ── Grade ──────────────────────────────────────
        correct_map = {str(r['id']): r['correct_answer'] for r in rows}
        total       = len(correct_map)
        correct     = sum(1 for qid, sel in clean.items() if sel is not None and correct_map[qid] == sel)
        percent     = round((correct / total) * 100) if total > 0 else 0

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

            # Readiness = average latest score of the topics the student has attempted
            # (taken from quiz_results, so a genuine 0% still counts as attempted)
            cursor.execute("""
                SELECT DISTINCT topic FROM quiz_results WHERE student_id = %s
            """, (student_id,))
            attempted = [r['topic'] for r in cursor.fetchall() if r['topic'] in VALID_TOPICS]
            cursor.execute("""
                SELECT aptitude_score, reasoning_score, coding_score, communication_score
                FROM students WHERE id = %s
            """, (student_id,))
            scores = cursor.fetchone()
            readiness = round(sum(scores[f"{t}_score"] for t in attempted) / len(attempted)) if attempted else 0
            cursor.execute("UPDATE students SET readiness_score = %s WHERE id = %s",
                           (readiness, student_id))

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
