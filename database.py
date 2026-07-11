import pymysql
from pymysql import pool
from config import Config
import logging

logger = logging.getLogger(__name__)

# ── Connection Pool ────────────────────────────────────
# FIX: one shared pool instead of new connection per request
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            maxconnections = Config.DB_POOL_SIZE,
            mincached      = 2,
            maxcached      = Config.DB_POOL_SIZE,
            host           = Config.DB_HOST,
            user           = Config.DB_USER,
            password       = Config.DB_PASSWORD,
            database       = Config.DB_NAME,
            cursorclass    = pymysql.cursors.DictCursor,
            autocommit     = False,
        )
    return _pool

def get_connection():
    """Get a connection from the pool."""
    try:
        return get_pool().connection()
    except Exception:
        # Fallback: direct connection if pool fails
        logger.warning("Pool unavailable, using direct connection")
        return pymysql.connect(
            host        = Config.DB_HOST,
            user        = Config.DB_USER,
            password    = Config.DB_PASSWORD,
            database    = Config.DB_NAME,
            cursorclass = pymysql.cursors.DictCursor,
        )
