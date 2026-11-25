"""Persistência do Nexuscore: SQLite local ou PostgreSQL por DATABASE_URL.

A aplicação mantém a API de armazenamento usada pelo main.py. A migração dos
dados existentes é uma operação separada e explícita: configurar DATABASE_URL
não copia nem apaga automaticamente o arquivo SQLite.
"""
import os
import re
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH") or os.getenv("DB_PATH") or str(
    Path(__file__).resolve().parent.parent / "data" / "nexuscore.db"
)
SQLITE_TIMEOUT_SECONDS = 30
_ID_TABLES = {"conversations", "ideas", "projects", "artifacts", "email_log"}


def _database_url():
    return os.getenv("DATABASE_URL", "").strip()


def _qmark_to_pyformat(sql):
    """Converte placeholders ? usados pelo código legado para %s do psycopg."""
    return sql.replace("?", "%s")


class _PostgresCursor:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = cursor.rowcount

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _PostgresConnection:
    """Adaptador pequeno para manter compatibilidade com db.execute(...)."""
    def __init__(self, raw_connection):
        self.raw = raw_connection

    def execute(self, sql, params=()):
        statement = sql.strip()
        match = re.match(r"INSERT\\s+INTO\\s+([a-zA-Z_][a-zA-Z0-9_]*)", statement, re.I)
        wants_id = bool(match and match.group(1).lower() in _ID_TABLES
                        and "RETURNING" not in statement.upper())
        if wants_id:
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
        cursor = self.raw.execute(_qmark_to_pyformat(statement), tuple(params or ()))
        inserted_id = None
        if wants_id:
            row = cursor.fetchone()
            inserted_id = row["id"] if row else None
        return _PostgresCursor(cursor, inserted_id)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def _open_connection():
    url = _database_url()
    if url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "DATABASE_URL está configurada, mas psycopg não está instalado."
            ) from exc
        raw = psycopg.connect(url, connect_timeout=15, row_factory=dict_row)
        return _PostgresConnection(raw)

    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=SQLITE_TIMEOUT_SECONDS)
    db.row_factory = sqlite3.Row
    db.execute(f"PRAGMA busy_timeout={SQLITE_TIMEOUT_SECONDS * 1000}")
    db.execute("PRAGMA foreign_keys=ON")
    return db


@contextmanager
def connection():
    """Abre conexão isolada e garante commit ou rollback."""
    db = _open_connection()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    """Cria o esquema no mecanismo selecionado, sem migrar dados implicitamente."""
    if _database_url():
        statements = [
            """CREATE TABLE IF NOT EXISTS conversations (
                id BIGSERIAL PRIMARY KEY, role TEXT NOT NULL, agent TEXT NOT NULL,
                content TEXT NOT NULL, provider TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS ideas (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'media', status TEXT NOT NULL DEFAULT 'nova',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS projects (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planejado',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS artifacts (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL,
                format TEXT NOT NULL, mime_type TEXT NOT NULL, content BYTEA NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS email_log (
                id BIGSERIAL PRIMARY KEY, direction TEXT NOT NULL, sender TEXT,
                recipient TEXT, subject TEXT, body TEXT, status TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)",
            "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
            "CREATE INDEX IF NOT EXISTS idx_email_log_created_at ON email_log(created_at)",
        ]
        with connection() as db:
            for statement in statements:
                db.execute(statement)
        return

    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
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
        db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_email_log_created_at ON email_log(created_at)")


def health():
    """Diagnóstico sem revelar URL, credenciais ou caminho absoluto."""
    if _database_url():
        with connection() as db:
            version = db.execute("SELECT version() AS version").fetchone()["version"]
            count = db.execute(
                "SELECT COUNT(*) AS count FROM information_schema.tables "
                "WHERE table_schema = current_schema()"
            ).fetchone()["count"]
        return {
            "engine": "postgresql",
            "database_configured": True,
            "database_reachable": True,
            "server_version": version.split(",")[0],
            "table_count": int(count),
        }

    path = Path(DB_PATH)
    with connection() as db:
        journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        version = db.execute("SELECT sqlite_version()").fetchone()[0]
        tables = db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    return {
        "engine": "sqlite",
        "database_file": path.name,
        "database_exists": path.is_file(),
        "database_size_bytes": path.stat().st_size if path.is_file() else 0,
        "journal_mode": str(journal_mode).lower(),
        "sqlite_version": version,
        "table_count": int(tables),
        "database_url_configured": False,
    }


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
    value = bytes(content)
    with connection() as db:
        cur = db.execute("INSERT INTO artifacts(title,filename,format,mime_type,content) VALUES(?,?,?,?,?)",
                         (title, filename, fmt, mime_type,
                          value if _database_url() else sqlite3.Binary(value)))
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
