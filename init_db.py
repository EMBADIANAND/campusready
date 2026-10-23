import logging
import os
import re

from database import get_connection

log = logging.getLogger("init_db")

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def _statements():
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        sql = f.read()
    sql = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    parts = [p.strip() for p in sql.split(";\n")]
    parts = [re.sub(r";\s*$", "", p) for p in parts if p.strip()]
    tables, seeds = [], []
    for p in parts:
        head = p.lstrip().upper()
        if head.startswith("CREATE DATABASE") or head.startswith("USE "):
            continue
        (seeds if head.startswith("INSERT") else tables).append(p)
    return tables, seeds


def init_db():
    tables, seeds = _statements()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for stmt in tables:
                cur.execute(stmt)
            cur.execute("SELECT COUNT(*) AS n FROM quiz_questions")
            if cur.fetchone()["n"] == 0:
                for stmt in seeds:
                    cur.execute(stmt)
                log.info("Seeded default quiz questions")
        conn.commit()
        log.info("Database schema ready")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
