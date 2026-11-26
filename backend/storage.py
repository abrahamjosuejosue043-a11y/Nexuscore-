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
_ID_TABLES = {"conversations", "ideas", "projects", "artifacts", "email_log", "shared_memory", "department_tasks"}


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
        match = re.match(r"INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", statement, re.I)
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


def _backfill_legacy_messages(db):
    """Agrupa mensagens preexistentes sem conversa em um histórico legado único."""
    count = db.execute(
        "SELECT COUNT(*) AS count FROM conversations WHERE conversation_id IS NULL"
    ).fetchone()["count"]
    if count:
        db.execute(
            """INSERT INTO chat_sessions(id, title, agent)
               VALUES('legacy', 'Histórico anterior', 'geral')
               ON CONFLICT(id) DO NOTHING"""
        )
        db.execute(
            "UPDATE conversations SET conversation_id='legacy' WHERE conversation_id IS NULL"
        )
        db.execute(
            "UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id='legacy'"
        )


def initialize():
    """Cria o esquema no mecanismo selecionado, sem migrar dados implicitamente."""
    if _database_url():
        statements = [
            """CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, agent TEXT NOT NULL DEFAULT 'geral',
                project_id BIGINT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS project_id BIGINT",
            """CREATE TABLE IF NOT EXISTS conversations (
                id BIGSERIAL PRIMARY KEY, role TEXT NOT NULL, agent TEXT NOT NULL,
                content TEXT NOT NULL, provider TEXT, conversation_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS conversation_id TEXT",
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
            """CREATE TABLE IF NOT EXISTS shared_memory (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'contexto',
                department TEXT NOT NULL DEFAULT 'todos',
                source_agent TEXT NOT NULL DEFAULT 'usuario',
                status TEXT NOT NULL DEFAULT 'active',
                project_id BIGINT,
                scope TEXT NOT NULL DEFAULT 'legacy',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            "ALTER TABLE shared_memory ADD COLUMN IF NOT EXISTS project_id BIGINT",
            "ALTER TABLE shared_memory ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'legacy'",
            """CREATE TABLE IF NOT EXISTS department_tasks (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                assigned_department TEXT NOT NULL, created_by TEXT NOT NULL DEFAULT 'diretoria',
                priority TEXT NOT NULL DEFAULT 'media',
                status TEXT NOT NULL DEFAULT 'pendente', result TEXT NOT NULL DEFAULT '',
                conversation_id TEXT, project_id BIGINT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ)""",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)",
            "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
            "CREATE INDEX IF NOT EXISTS idx_email_log_created_at ON email_log(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_shared_memory_status_department ON shared_memory(status, department, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_shared_memory_scope_project ON shared_memory(status, scope, project_id, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_department_tasks_queue ON department_tasks(assigned_department, status, priority, updated_at)",
        ]
        with connection() as db:
            for statement in statements:
                db.execute(statement)
            _backfill_legacy_messages(db)
        return

    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, agent TEXT NOT NULL DEFAULT 'geral',
            project_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        session_columns = {row["name"] for row in db.execute("PRAGMA table_info(chat_sessions)").fetchall()}
        if "project_id" not in session_columns:
            db.execute("ALTER TABLE chat_sessions ADD COLUMN project_id INTEGER")
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL,
            agent TEXT NOT NULL, content TEXT NOT NULL, provider TEXT,
            conversation_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(conversations)").fetchall()}
        if "conversation_id" not in columns:
            db.execute("ALTER TABLE conversations ADD COLUMN conversation_id TEXT")
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
        db.execute("""CREATE TABLE IF NOT EXISTS shared_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'contexto',
            department TEXT NOT NULL DEFAULT 'todos',
            source_agent TEXT NOT NULL DEFAULT 'usuario',
            status TEXT NOT NULL DEFAULT 'active',
            project_id INTEGER, scope TEXT NOT NULL DEFAULT 'legacy',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        memory_columns = {row["name"] for row in db.execute("PRAGMA table_info(shared_memory)").fetchall()}
        if "project_id" not in memory_columns:
            db.execute("ALTER TABLE shared_memory ADD COLUMN project_id INTEGER")
        if "scope" not in memory_columns:
            db.execute("ALTER TABLE shared_memory ADD COLUMN scope TEXT NOT NULL DEFAULT 'legacy'")
        db.execute("""CREATE TABLE IF NOT EXISTS department_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            description TEXT NOT NULL, assigned_department TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'diretoria',
            priority TEXT NOT NULL DEFAULT 'media',
            status TEXT NOT NULL DEFAULT 'pendente', result TEXT NOT NULL DEFAULT '',
            conversation_id TEXT, project_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(conversation_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)")
        _backfill_legacy_messages(db)
        db.execute("CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_email_log_created_at ON email_log(created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_shared_memory_status_department ON shared_memory(status, department, updated_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_shared_memory_scope_project ON shared_memory(status, scope, project_id, updated_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_department_tasks_queue ON department_tasks(assigned_department, status, priority, updated_at)")


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


def ensure_conversation(conversation_id, title, agent):
    """Cria uma conversa uma única vez; mensagens posteriores preservam seu vínculo."""
    with connection() as db:
        db.execute(
            """INSERT INTO chat_sessions(id, title, agent) VALUES(?,?,?)
               ON CONFLICT(id) DO NOTHING""",
            (str(conversation_id), str(title)[:100] or "Nova conversa", str(agent)[:40]),
        )
        row = db.execute(
            "SELECT * FROM chat_sessions WHERE id=?", (str(conversation_id),)
        ).fetchone()
    return dict(row) if row else None


def set_conversation_project(conversation_id, project_id):
    """Associa ou desassocia explicitamente uma conversa a um projeto existente."""
    value = int(project_id) if project_id is not None else None
    with connection() as db:
        if value is not None:
            exists = db.execute("SELECT id FROM projects WHERE id=?", (value,)).fetchone()
            if not exists:
                return False
        cur = db.execute(
            "UPDATE chat_sessions SET project_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (value, str(conversation_id)),
        )
        return cur.rowcount > 0


def save_message(role, agent, content, provider=None, conversation_id=None):
    with connection() as db:
        db.execute(
            """INSERT INTO conversations(role,agent,content,provider,conversation_id)
               VALUES(?,?,?,?,?)""",
            (role, agent, content, provider, conversation_id),
        )
        if conversation_id:
            db.execute(
                "UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (conversation_id,),
            )


def messages(limit=50):
    with connection() as db:
        rows = db.execute("SELECT * FROM conversations ORDER BY id DESC LIMIT ?",
                          (max(1, min(int(limit), 200)),)).fetchall()
    return [dict(row) for row in reversed(rows)]


def list_conversations(limit=100):
    with connection() as db:
        rows = db.execute(
            """SELECT s.id, s.title, s.agent, s.project_id, s.created_at, s.updated_at,
                      COUNT(m.id) AS message_count
               FROM chat_sessions s
               LEFT JOIN conversations m ON m.conversation_id=s.id
               GROUP BY s.id, s.title, s.agent, s.project_id, s.created_at, s.updated_at
               ORDER BY s.updated_at DESC
               LIMIT ?""",
            (max(1, min(int(limit), 200)),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM chat_sessions WHERE id=?", (str(conversation_id),)
        ).fetchone()
    return dict(row) if row else None


def conversation_messages(conversation_id, limit=500):
    with connection() as db:
        rows = db.execute(
            """SELECT * FROM (
                   SELECT * FROM conversations
                   WHERE conversation_id=?
                   ORDER BY id DESC
                   LIMIT ?
               ) AS recent_messages
               ORDER BY id ASC""",
            (str(conversation_id), max(1, min(int(limit), 1000))),
        ).fetchall()
    return [dict(row) for row in rows]


def rename_conversation(conversation_id, title):
    with connection() as db:
        cur = db.execute(
            """UPDATE chat_sessions SET title=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (str(title).strip()[:100], str(conversation_id)),
        )
        return cur.rowcount > 0


def create_department_task(
    title, description, assigned_department, priority="media",
    created_by="diretoria", conversation_id=None, project_id=None
):
    """Cria uma tarefa encaminhada a um departamento."""
    with connection() as db:
        cur = db.execute(
            """INSERT INTO department_tasks(
                   title, description, assigned_department, created_by, priority,
                   conversation_id, project_id
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                str(title).strip()[:160],
                str(description).strip()[:8000],
                str(assigned_department),
                str(created_by),
                str(priority),
                str(conversation_id) if conversation_id else None,
                int(project_id) if project_id is not None else None,
            ),
        )
        return cur.lastrowid


def list_department_tasks(
    limit=100, department=None, status=None, conversation_id=None, project_id=None
):
    """Lista tarefas com filtros opcionais de departamento, conversa e projeto.

    Quando conversation_id ou project_id é informado, a consulta fica restrita
    exatamente àquele vínculo; tarefas sem vínculo não são misturadas ao contexto.
    """
    conditions = []
    params = []
    if department:
        conditions.append("assigned_department=?")
        params.append(str(department))
    if status:
        conditions.append("status=?")
        params.append(str(status))
    if conversation_id is not None:
        conditions.append("conversation_id=?")
        params.append(str(conversation_id))
    if project_id is not None:
        conditions.append("project_id=?")
        params.append(int(project_id))
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(max(1, min(int(limit), 200)))
    query = (
        "SELECT * FROM department_tasks" + where
        + " ORDER BY CASE priority WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, "
          "updated_at DESC, id DESC LIMIT ?"
    )
    with connection() as db:
        rows = db.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def update_department_task(task_id, status, result=None):
    """Atualiza estado e resultado de uma tarefa, mantendo data de conclusão coerente."""
    allowed = {"pendente", "em_andamento", "bloqueada", "concluida"}
    if status not in allowed:
        raise ValueError("Status de tarefa inválido.")
    with connection() as db:
        cur = db.execute(
            """UPDATE department_tasks
               SET status=?,
                   result=COALESCE(?, result),
                   updated_at=CURRENT_TIMESTAMP,
                   completed_at=CASE WHEN ?='concluida'
                                     THEN COALESCE(completed_at, CURRENT_TIMESTAMP)
                                     ELSE NULL END
               WHERE id=?""",
            (status, result, status, int(task_id)),
        )
        return cur.rowcount > 0


def save_shared_memory(
    title, content, category="contexto", department="todos",
    source_agent="usuario", project_id=None
):
    """Salva memória global ou vinculada a um projeto existente."""
    value = int(project_id) if project_id is not None else None
    with connection() as db:
        if value is not None:
            exists = db.execute("SELECT id FROM projects WHERE id=?", (value,)).fetchone()
            if not exists:
                raise ValueError("Projeto não encontrado.")
        scope = "project" if value is not None else "global"
        cur = db.execute(
            """INSERT INTO shared_memory(
                   title, content, category, department, source_agent, status,
                   project_id, scope
               ) VALUES(?,?,?,?,?,'active',?,?)""",
            (
                str(title).strip()[:160],
                str(content).strip()[:8000],
                str(category).strip()[:30],
                str(department).strip()[:30],
                str(source_agent).strip()[:40],
                value,
                scope,
            ),
        )
        return cur.lastrowid


def shared_memories(
    limit=100, department=None, include_archived=False,
    project_id=None, prompt_context=False
):
    """Lista memórias; no prompt aplica escopo estrito para evitar vazamento entre projetos."""
    conditions = []
    params = []
    if not include_archived:
        conditions.append("status='active'")
    if department:
        conditions.append("(department='todos' OR department=?)")
        params.append(str(department))
    if prompt_context:
        if project_id is None:
            conditions.append("scope IN ('global', 'legacy')")
        else:
            conditions.append("(scope='global' OR (scope='project' AND project_id=?))")
            params.append(int(project_id))
    elif project_id is not None:
        conditions.append("project_id=?")
        params.append(int(project_id))
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(max(1, min(int(limit), 200)))
    query = (
        "SELECT id, title, content, category, department, source_agent, status, "
        "project_id, scope, created_at, updated_at "
        "FROM shared_memory" + where
        + " ORDER BY updated_at DESC, id DESC LIMIT ?"
    )
    with connection() as db:
        rows = db.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def archive_shared_memory(memory_id):
    """Arquiva sem excluir fisicamente, preservando rastreabilidade."""
    with connection() as db:
        cur = db.execute(
            "UPDATE shared_memory SET status='archived', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'",
            (int(memory_id),),
        )
        return cur.rowcount > 0


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
