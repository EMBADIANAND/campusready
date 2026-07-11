import logging
from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

from config import Config
from routes.student import student_bp
from routes.company import company_bp
from routes.quiz    import quiz_bp
from routes.admin   import admin_bp

# ── Logging setup ──────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = Flask(__name__)
app.config.from_object(Config)

# ── Extensions ─────────────────────────────────────────
# FIX: CORS restricted to known origins only
CORS(app, origins=Config.ALLOWED_ORIGINS, supports_credentials=True)
bcrypt = Bcrypt(app)      # FIX: single shared instance (not per-blueprint)
jwt    = JWTManager(app)

# ── Blueprints ─────────────────────────────────────────
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(company_bp, url_prefix='/api/company')
app.register_blueprint(quiz_bp,    url_prefix='/api/quiz')
app.register_blueprint(admin_bp,   url_prefix='/api/admin')

# ── JWT error handlers ─────────────────────────────────
@jwt.unauthorized_loader
def missing_token(reason):
    return {'error': 'Login required'}, 401

@jwt.invalid_token_loader
def invalid_token(reason):
    return {'error': 'Invalid or expired token, please login again'}, 401

@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    return {'error': 'Session expired, please login again'}, 401

# ── Health check ───────────────────────────────────────
@app.route('/')
def home():
    return {'message': 'CampusReady API is running ✅', 'version': '2.0'}

if __name__ == '__main__':
    # FIX: debug mode driven by env variable
    app.run(debug=Config.DEBUG, port=5000)
