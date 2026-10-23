import os
import pymysql
from config import Config


def _ssl_options():
    if os.getenv("DB_SSL", "false").lower() != "true":
        return None
    ca = os.getenv("DB_SSL_CA")
    if ca and os.path.exists(ca):
        return {"ca": ca}
    return {"check_hostname": False}


def get_connection(use_database=True):
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME if use_database else None,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        ssl=_ssl_options(),
        connect_timeout=15
    )
