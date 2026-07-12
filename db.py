"""SQLite access layer for Field Notes CMS.

One embedded database file (data/app.db). Connections are per-request via Flask's
`g`. Rows come back as dict-like sqlite3.Row objects.
"""
import os
import sqlite3
import secrets
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.environ.get("FN_DB_PATH", os.path.join(DATA_DIR, "app.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db():
    """Return the request-scoped connection, opening it on first use."""
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        g.db = conn
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _migrate_english_only(conn):
    """One-time migration from the old bilingual schema (title_th/title_en,
    caption_th/caption_en, summary_en) to single-language columns. English
    values win where they exist; Thai remains until re-edited. Idempotent."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(essays)").fetchall()}
    if "title_th" in cols:
        conn.execute("ALTER TABLE essays RENAME COLUMN title_th TO title")
        conn.execute("UPDATE essays SET title = CASE WHEN TRIM(COALESCE(title_en,''))<>'' "
                     "THEN title_en ELSE title END")
        conn.execute("ALTER TABLE essays DROP COLUMN title_en")
    if "summary_en" in cols:
        conn.execute("ALTER TABLE essays RENAME COLUMN summary_en TO summary")
    pcols = {r[1] for r in conn.execute("PRAGMA table_info(plates)").fetchall()}
    if "caption_th" in pcols:
        conn.execute("ALTER TABLE plates RENAME COLUMN caption_th TO caption")
        conn.execute("UPDATE plates SET caption = CASE WHEN TRIM(COALESCE(caption_en,''))<>'' "
                     "THEN caption_en ELSE caption END")
        conn.execute("ALTER TABLE plates DROP COLUMN caption_en")
    conn.execute("DROP TABLE IF EXISTS subscribers")
    conn.execute("DELETE FROM site_content WHERE key LIKE 'subscribe_%'")


def init_db():
    """Create tables if missing, then apply in-place migrations. Idempotent."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        _migrate_english_only(conn)
        conn.commit()
    finally:
        conn.close()


# ---- settings (key/value) -------------------------------------------------

def get_setting(key, default=None):
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_db()
    db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    db.commit()


def get_or_create_secret_key():
    """Persist a Flask secret key so sessions survive restarts.

    Read outside the request context (app startup), so use a throwaway connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT value FROM settings WHERE key='secret_key'").fetchone()
        if row:
            return row["value"]
        key = secrets.token_hex(32)
        conn.execute("INSERT INTO settings(key, value) VALUES('secret_key', ?)", (key,))
        conn.commit()
        return key
    finally:
        conn.close()
