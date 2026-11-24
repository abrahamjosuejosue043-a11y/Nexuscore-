"""Persistência SQLite do Nexuscore. Configure DATABASE_PATH em disco persistente no Render."""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH") or os.getenv("DB_PATH") or str(Path(__file__).resolve().parent.parent / "data" / "nexuscore.db")

@contextmanager
def connection():
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=20)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()

def initialize():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL,
            agent TEXT NOT NULL, content TEXT NOT NULL, provider TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        db.execute("""CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            summary TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'media',
            status TEXT NOT NULL DEFAULT 'nova',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        db.execute("""CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, direction TEXT NOT NULL,
            sender TEXT, recipient TEXT, subject TEXT, body TEXT,
            status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

def save_message(role, agent, content, provider=None):
    with connection() as db:
        db.execute("INSERT INTO conversations(role,agent,content,provider) VALUES(?,?,?,?)",
                   (role, agent, content, provider))

def messages(limit=50):
    with connection() as db:
        rows = db.execute("SELECT * FROM conversations ORDER BY id DESC LIMIT ?",
                          (max(1, min(int(limit), 200)),)).fetchall()
    return [dict(row) for row in reversed(rows)]

def save_idea(title, summary, priority="media"):
    with connection() as db:
        cur = db.execute("INSERT INTO ideas(title,summary,priority) VALUES(?,?,?)",
                         (title, summary, priority))
        return cur.lastrowid

def ideas(limit=100):
    with connection() as db:
        rows = db.execute("SELECT * FROM ideas ORDER BY id DESC LIMIT ?",
                          (max(1, min(int(limit), 300)),)).fetchall()
    return [dict(row) for row in rows]
