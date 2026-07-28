import logging
from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

from config import Config
from routes.student import student_bp
from routes.company import company_bp
from routes.quiz import quiz_bp
from routes.admin import admin_bp

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(
    app,
    resources={r"/api/*": {"origins": Config.ALLOWED_ORIGINS}},
    supports_credentials=True
)

# Extensions
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(company_bp, url_prefix='/api/company')
app.register_blueprint(quiz_bp, url_prefix='/api/quiz')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# JWT error handlers
@jwt.unauthorized_loader
def missing_token(reason):
    return {'error': 'Login required'}, 401


@jwt.invalid_token_loader
def invalid_token(reason):
    return {'error': 'Invalid or expired token, please login again'}, 401


@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    return {'error': 'Session expired, please login again'}, 401


# Health check
@app.route('/')
def home():
    return {
        'message': 'CampusReady API is running ✅',
        'version': '2.0'
    }


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
