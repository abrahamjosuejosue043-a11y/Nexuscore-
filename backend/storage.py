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
        db.execute("""CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'planejado',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        db.execute("""CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            filename TEXT NOT NULL, format TEXT NOT NULL, mime_type TEXT NOT NULL,
            content BLOB NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
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

def save_project(title, summary, status="planejado"):
    with connection() as db:
        cur = db.execute("INSERT INTO projects(title,summary,status) VALUES(?,?,?)",
                         (title, summary, status))
        return cur.lastrowid

def projects(limit=100):
    with connection() as db:
        rows = db.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?",
                          (max(1, min(int(limit), 300)),)).fetchall()
    return [dict(row) for row in rows]

def update_project(project_id, status):
    with connection() as db:
        cur = db.execute("UPDATE projects SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (status, int(project_id)))
        return cur.rowcount > 0

def save_artifact(title, filename, fmt, mime_type, content):
    with connection() as db:
        cur = db.execute("INSERT INTO artifacts(title,filename,format,mime_type,content) VALUES(?,?,?,?,?)",
                         (title, filename, fmt, mime_type, sqlite3.Binary(content)))
        return cur.lastrowid

def artifacts(limit=50):
    with connection() as db:
        rows = db.execute("SELECT id,title,filename,format,mime_type,length(content) AS size,created_at FROM artifacts ORDER BY id DESC LIMIT ?",
                          (max(1, min(int(limit), 200)),)).fetchall()
    return [dict(row) for row in rows]

def artifact(artifact_id):
    with connection() as db:
        row = db.execute("SELECT * FROM artifacts WHERE id=?", (int(artifact_id),)).fetchone()
    return dict(row) if row else None
