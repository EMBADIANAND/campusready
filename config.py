import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── MySQL ──────────────────────────────────────────
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME     = os.getenv("DB_NAME", "campusready")

    # ── Connection Pool ────────────────────────────────
    DB_POOL_SIZE    = 10   # max simultaneous connections
    DB_POOL_TIMEOUT = 30   # seconds before giving up

    # ── JWT ────────────────────────────────────────────
    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)   # FIX: tokens now expire

    # ── Flask ──────────────────────────────────────────
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"  # FIX: debug off by default

    # ── CORS ───────────────────────────────────────────
    # FIX: restrict to known origins only
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500"
    ).split(",")

    # ── Admin ──────────────────────────────────────────
    # FIX: admin credentials from env, not hardcoded
    ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@campusready.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe@123")
