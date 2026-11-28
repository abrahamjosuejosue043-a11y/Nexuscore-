"""Persistência do Nexuscore: SQLite local ou PostgreSQL por DATABASE_URL.

A aplicação mantém a API de armazenamento usada pelo main.py. A migração dos
dados existentes é uma operação separada e explícita: configurar DATABASE_URL
não copia nem apaga automaticamente o arquivo SQLite.
"""
import os
import math
import re
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH") or os.getenv("DB_PATH") or str(
    Path(__file__).resolve().parent.parent / "data" / "nexuscore.db"
)
SQLITE_TIMEOUT_SECONDS = 30
_ID_TABLES = {"conversations", "ideas", "projects", "artifacts", "email_log", "shared_memory", "department_tasks", "work_plans", "work_plan_items"}


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
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'aprovado'",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMPTZ",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS purge_after TIMESTAMPTZ",
            """CREATE TABLE IF NOT EXISTS project_decisions (
                id BIGSERIAL PRIMARY KEY, project_id BIGINT NOT NULL,
                project_title TEXT NOT NULL, project_summary TEXT NOT NULL,
                decision TEXT NOT NULL, actor TEXT NOT NULL,
                decided_at TIMESTAMPTZ NOT NULL, purge_after TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ)""",
            "CREATE INDEX IF NOT EXISTS idx_projects_approval_status ON projects(approval_status, purge_after)",
            "CREATE INDEX IF NOT EXISTS idx_project_decisions_project ON project_decisions(project_id, decided_at)",
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
                conversation_id TEXT, project_id BIGINT, plan_id BIGINT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ)""",
            "ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS plan_id BIGINT",
            "ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION NOT NULL DEFAULT 2",
            """CREATE TABLE IF NOT EXISTS project_department_weights (
                project_id BIGINT NOT NULL REFERENCES projects(id),
                department TEXT NOT NULL, weight DOUBLE PRECISION NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(project_id, department))""",
            """CREATE TABLE IF NOT EXISTS task_events (
                id BIGSERIAL PRIMARY KEY, task_id BIGINT NOT NULL REFERENCES department_tasks(id),
                event_type TEXT NOT NULL, from_status TEXT, to_status TEXT,
                actor TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
            "CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, created_at, id)",
            """CREATE TABLE IF NOT EXISTS work_plans (
                id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
                summary TEXT NOT NULL, project_id BIGINT NOT NULL,
                status TEXT NOT NULL DEFAULT 'rascunho', created_by TEXT NOT NULL DEFAULT 'diretoria',
                conversation_id TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMPTZ, rejected_at TIMESTAMPTZ)""",
            """CREATE TABLE IF NOT EXISTS work_plan_items (
                id BIGSERIAL PRIMARY KEY, plan_id BIGINT NOT NULL REFERENCES work_plans(id),
                title TEXT NOT NULL, description TEXT NOT NULL,
                assigned_department TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'media',
                position INTEGER NOT NULL DEFAULT 0)""",
            "ALTER TABLE work_plan_items ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION NOT NULL DEFAULT 2",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)",
            "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
            "CREATE INDEX IF NOT EXISTS idx_email_log_created_at ON email_log(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_shared_memory_status_department ON shared_memory(status, department, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_shared_memory_scope_project ON shared_memory(status, scope, project_id, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_department_tasks_queue ON department_tasks(assigned_department, status, priority, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_department_tasks_plan ON department_tasks(plan_id)",
            "CREATE INDEX IF NOT EXISTS idx_work_plans_project_status ON work_plans(project_id, status, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_work_plan_items_plan ON work_plan_items(plan_id, position)",
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
        project_columns = {row["name"] for row in db.execute("PRAGMA table_info(projects)").fetchall()}
        if "approval_status" not in project_columns:
            db.execute("ALTER TABLE projects ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'aprovado'")
        if "approved_at" not in project_columns:
            db.execute("ALTER TABLE projects ADD COLUMN approved_at TEXT")
        if "rejected_at" not in project_columns:
            db.execute("ALTER TABLE projects ADD COLUMN rejected_at TEXT")
        if "canceled_at" not in project_columns:
            db.execute("ALTER TABLE projects ADD COLUMN canceled_at TEXT")
        if "purge_after" not in project_columns:
            db.execute("ALTER TABLE projects ADD COLUMN purge_after TEXT")
        db.execute("""CREATE TABLE IF NOT EXISTS project_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
            project_title TEXT NOT NULL, project_summary TEXT NOT NULL,
            decision TEXT NOT NULL, actor TEXT NOT NULL,
            decided_at TEXT NOT NULL, purge_after TEXT, deleted_at TEXT)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_projects_approval_status ON projects(approval_status, purge_after)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_project_decisions_project ON project_decisions(project_id, decided_at)")
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
            conversation_id TEXT, project_id INTEGER, plan_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT)""")
        task_columns = {row["name"] for row in db.execute("PRAGMA table_info(department_tasks)").fetchall()}
        if "plan_id" not in task_columns:
            db.execute("ALTER TABLE department_tasks ADD COLUMN plan_id INTEGER")
        if "weight" not in task_columns:
            db.execute("ALTER TABLE department_tasks ADD COLUMN weight REAL NOT NULL DEFAULT 2")
        db.execute("""CREATE TABLE IF NOT EXISTS task_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL,
            event_type TEXT NOT NULL, from_status TEXT, to_status TEXT,
            actor TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES department_tasks(id))""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, created_at, id)")
        db.execute("""CREATE TABLE IF NOT EXISTS work_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            objective TEXT NOT NULL, summary TEXT NOT NULL, project_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'rascunho',
            created_by TEXT NOT NULL DEFAULT 'diretoria', conversation_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            approved_at TEXT, rejected_at TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS work_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL,
            assigned_department TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'media',
            position INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(plan_id) REFERENCES work_plans(id))""")
        plan_item_columns = {row["name"] for row in db.execute("PRAGMA table_info(work_plan_items)").fetchall()}
        if "weight" not in plan_item_columns:
            db.execute("ALTER TABLE work_plan_items ADD COLUMN weight REAL NOT NULL DEFAULT 2")
        db.execute("""CREATE TABLE IF NOT EXISTS project_department_weights (
            project_id INTEGER NOT NULL, department TEXT NOT NULL,
            weight REAL NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(project_id, department),
            FOREIGN KEY(project_id) REFERENCES projects(id))""")
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
        db.execute("CREATE INDEX IF NOT EXISTS idx_department_tasks_plan ON department_tasks(plan_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_work_plans_project_status ON work_plans(project_id, status, updated_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_work_plan_items_plan ON work_plan_items(plan_id, position)")


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
            exists = db.execute(
                "SELECT id FROM projects WHERE id=? AND approval_status='aprovado'", (value,)
            ).fetchone()
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


def clear_conversation_messages(conversation_id):
    """Apaga somente as mensagens; mantém a conversa, projeto, tarefas e planos."""
    conversation_id = str(conversation_id)
    with connection() as db:
        exists = db.execute(
            "SELECT id FROM chat_sessions WHERE id=?", (conversation_id,)
        ).fetchone()
        if not exists:
            return None
        cur = db.execute(
            "DELETE FROM conversations WHERE conversation_id=?", (conversation_id,)
        )
        deleted_count = max(0, int(cur.rowcount or 0))
        db.execute(
            "UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (conversation_id,),
        )
        return deleted_count


def delete_conversation(conversation_id):
    """Apaga mensagens e cabeçalho da conversa, preservando tarefas e planos."""
    conversation_id = str(conversation_id)
    with connection() as db:
        exists = db.execute(
            "SELECT id FROM chat_sessions WHERE id=?", (conversation_id,)
        ).fetchone()
        if not exists:
            return None
        message_count = db.execute(
            "SELECT COUNT(*) AS total FROM conversations WHERE conversation_id=?",
            (conversation_id,),
        ).fetchone()["total"]
        task_count = db.execute(
            "SELECT COUNT(*) AS total FROM department_tasks WHERE conversation_id=?",
            (conversation_id,),
        ).fetchone()["total"]
        plan_count = db.execute(
            "SELECT COUNT(*) AS total FROM work_plans WHERE conversation_id=?",
            (conversation_id,),
        ).fetchone()["total"]

        # Operações e histórico operacional são preservados; somente se remove
        # o vínculo com a conversa que será excluída.
        db.execute(
            "UPDATE department_tasks SET conversation_id=NULL WHERE conversation_id=?",
            (conversation_id,),
        )
        db.execute(
            "UPDATE work_plans SET conversation_id=NULL WHERE conversation_id=?",
            (conversation_id,),
        )
        db.execute(
            "DELETE FROM conversations WHERE conversation_id=?", (conversation_id,)
        )
        db.execute("DELETE FROM chat_sessions WHERE id=?", (conversation_id,))
        return {
            "messages_deleted": int(message_count or 0),
            "tasks_preserved": int(task_count or 0),
            "plans_preserved": int(plan_count or 0),
        }


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
    created_by="diretoria", conversation_id=None, project_id=None, plan_id=None, weight=None
):
    """Cria uma tarefa encaminhada a um departamento."""
    task_weight = float(weight) if weight is not None else {"alta": 3.0, "media": 2.0, "baixa": 1.0}.get(str(priority).lower(), 2.0)
    if not math.isfinite(task_weight) or task_weight <= 0 or task_weight > 10000:
        raise ValueError("O peso da tarefa deve estar entre 0 e 10000.")
    with connection() as db:
        if project_id is not None:
            project = db.execute(
                "SELECT id,approval_status FROM projects WHERE id=?", (int(project_id),)
            ).fetchone()
            if not project:
                raise ValueError("Projeto não encontrado.")
            if project["approval_status"] != "aprovado":
                raise ValueError("O projeto precisa ser aprovado pelo CEO antes de receber tarefas.")
        cur = db.execute(
            """INSERT INTO department_tasks(
                   title, description, assigned_department, created_by, priority,
                   conversation_id, project_id, plan_id, weight
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                str(title).strip()[:160],
                str(description).strip()[:8000],
                str(assigned_department),
                str(created_by),
                str(priority),
                str(conversation_id) if conversation_id else None,
                int(project_id) if project_id is not None else None,
                int(plan_id) if plan_id is not None else None,
                task_weight,
            ),
        )
        task_id = cur.lastrowid
        _insert_task_event(db, task_id, "created", None, "pendente", str(created_by or "sistema"), "Tarefa criada.")
        return task_id


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
    if conversation_id is not None and project_id is not None:
        conditions.append(
            "((conversation_id=? AND project_id=?) OR (project_id=? AND conversation_id IS NULL))"
        )
        params.extend([str(conversation_id), int(project_id), int(project_id)])
    elif conversation_id is not None:
        conditions.append("conversation_id=? AND project_id IS NULL")
        params.append(str(conversation_id))
    elif project_id is not None:
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




def set_project_department_weights(project_id, weights):
    """Define pesos departamentais do projeto em uma única transação."""
    value = int(project_id)
    normalized = {}
    for department, weight in weights.items():
        name = str(department).strip().lower()
        number = float(weight)
        if not name or not math.isfinite(number) or not 0 < number <= 10000:
            raise ValueError("Departamento ou peso inválido.")
        normalized[name] = number
    if not normalized or abs(sum(normalized.values()) - 100.0) > 0.01:
        raise ValueError("Os pesos dos departamentos devem somar 100.")
    with connection() as db:
        project = db.execute(
            "SELECT id, approval_status FROM projects WHERE id=?", (value,)
        ).fetchone()
        if not project:
            raise ValueError("Projeto não encontrado.")
        if project["approval_status"] != "aprovado":
            raise ValueError("O projeto precisa estar aprovado pelo CEO.")
        # A configuração recebida substitui integralmente a anterior.
        # Isso impede que departamentos omitidos permaneçam somando no projeto.
        db.execute("DELETE FROM project_department_weights WHERE project_id=?", (value,))
        for department, weight in normalized.items():
            db.execute(
                """INSERT INTO project_department_weights(project_id, department, weight)
                   VALUES(?,?,?)""",
                (value, department, weight),
            )
        rows = db.execute(
            """SELECT department, weight FROM project_department_weights
               WHERE project_id=? ORDER BY department""", (value,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_department_weights(project_id):
    with connection() as db:
        rows = db.execute(
            """SELECT department, weight, updated_at FROM project_department_weights
               WHERE project_id=? ORDER BY department""", (int(project_id),)
        ).fetchall()
    return [dict(row) for row in rows]


def project_progress_inputs(project_id):
    """Retorna projeto, tarefas e pesos com validação derivada do histórico auditável."""
    value = int(project_id)
    with connection() as db:
        project = db.execute(
            "SELECT id, title, approval_status FROM projects WHERE id=?", (value,)
        ).fetchone()
        if not project:
            return None
        tasks = db.execute(
            """SELECT task.*,
                      CASE WHEN EXISTS (
                          SELECT 1 FROM task_events audit_event
                          WHERE audit_event.task_id=task.id
                            AND audit_event.event_type='status_changed'
                            AND audit_event.to_status='concluida'
                            AND audit_event.actor='diretoria'
                      ) THEN 1 ELSE 0 END AS directorate_validated
               FROM department_tasks task
               WHERE task.project_id=?
               ORDER BY task.id""",
            (value,),
        ).fetchall()
        weights = db.execute(
            """SELECT department, weight FROM project_department_weights
               WHERE project_id=? ORDER BY department""",
            (value,),
        ).fetchall()
    return {
        "project": dict(project),
        "tasks": [dict(row) for row in tasks],
        "department_weights": {
            str(row["department"]): float(row["weight"]) for row in weights
        },
    }


def project_exists(project_id):
    with connection() as db:
        return db.execute("SELECT id FROM projects WHERE id=?", (int(project_id),)).fetchone() is not None


def create_work_plan(title, objective, summary, project_id, items, conversation_id=None):
    """Cria um plano em rascunho e seus itens; nada é delegado antes da aprovação."""
    value = int(project_id)
    with connection() as db:
        project = db.execute(
            "SELECT id,approval_status FROM projects WHERE id=?", (value,)
        ).fetchone()
        if not project:
            raise ValueError("Projeto não encontrado.")
        if project["approval_status"] != "aprovado":
            raise ValueError("O projeto precisa ser aprovado pelo CEO antes de receber planos.")
        cur = db.execute(
            """INSERT INTO work_plans(title, objective, summary, project_id, status, conversation_id)
               VALUES(?,?,?,?, 'rascunho', ?)""",
            (
                str(title).strip()[:160],
                str(objective).strip()[:8000],
                str(summary).strip()[:8000],
                value,
                str(conversation_id) if conversation_id else None,
            ),
        )
        plan_id = cur.lastrowid
        for position, item in enumerate(items):
            raw_weight = item.get("weight")
            item_weight = (
                float(raw_weight) if raw_weight is not None
                else {"alta": 3.0, "media": 2.0, "baixa": 1.0}.get(str(item["priority"]).lower(), 2.0)
            )
            if not math.isfinite(item_weight) or item_weight <= 0 or item_weight > 10000:
                raise ValueError("O peso do item do plano deve estar entre 0 e 10000.")
            db.execute(
                """INSERT INTO work_plan_items(
                       plan_id, title, description, assigned_department, priority, position, weight
                   ) VALUES(?,?,?,?,?,?,?)""",
                (
                    plan_id,
                    str(item["title"]).strip()[:160],
                    str(item["description"]).strip()[:8000],
                    str(item["department"]),
                    str(item["priority"]),
                    position,
                    item_weight,
                ),
            )
    return plan_id


def get_work_plan(plan_id):
    with connection() as db:
        row = db.execute("SELECT * FROM work_plans WHERE id=?", (int(plan_id),)).fetchone()
        if not row:
            return None
        plan = dict(row)
        items = db.execute(
            "SELECT * FROM work_plan_items WHERE plan_id=? ORDER BY position, id",
            (int(plan_id),),
        ).fetchall()
    plan["items"] = [dict(item) for item in items]
    return plan


def list_work_plans(limit=50, project_id=None, status=None):
    conditions = []
    params = []
    if project_id is not None:
        conditions.append("project_id=?")
        params.append(int(project_id))
    if status:
        conditions.append("status=?")
        params.append(str(status))
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(max(1, min(int(limit), 200)))
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM work_plans" + where + " ORDER BY updated_at DESC, id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        plans = [dict(row) for row in rows]
        for plan in plans:
            items = db.execute(
                "SELECT * FROM work_plan_items WHERE plan_id=? ORDER BY position, id",
                (plan["id"],),
            ).fetchall()
            plan["items"] = [dict(item) for item in items]
    return plans


def work_plan_status_counts(project_id):
    """Conta todos os planos por estado em um projeto, sem limite de paginação."""
    with connection() as db:
        rows = db.execute(
            """SELECT status, COUNT(*) AS total
               FROM work_plans WHERE project_id=? GROUP BY status""",
            (int(project_id),),
        ).fetchall()
    return {str(row["status"]): int(row["total"]) for row in rows}


def approve_work_plan(plan_id):
    """Aprova um plano uma única vez e cria as tarefas delegadas atomicamente."""
    with connection() as db:
        claimed = db.execute(
            "UPDATE work_plans SET status='aprovando' WHERE id=? AND status='rascunho'",
            (int(plan_id),),
        )
        if claimed.rowcount == 0:
            return None
        plan_row = db.execute(
            "SELECT * FROM work_plans WHERE id=?", (int(plan_id),)
        ).fetchone()
        plan = dict(plan_row)
        items = db.execute(
            "SELECT * FROM work_plan_items WHERE plan_id=? ORDER BY position, id",
            (int(plan_id),),
        ).fetchall()
        if not items:
            raise ValueError("Plano sem tarefas não pode ser aprovado.")
        task_ids = []
        for item in items:
            cur = db.execute(
                """INSERT INTO department_tasks(
                       title, description, assigned_department, created_by, priority,
                       conversation_id, project_id, plan_id, status, result, weight
                   ) VALUES(?,?,?,?,?,?,?,?, 'pendente', '', ?)""",
                (
                    item["title"], item["description"], item["assigned_department"],
                    "diretoria", item["priority"], plan.get("conversation_id"),
                    plan["project_id"], int(plan_id), item["weight"],
                ),
            )
            task_ids.append(cur.lastrowid)
            _insert_task_event(db, cur.lastrowid, "delegated", None, "pendente", "diretoria", f"Tarefa delegada pelo plano #{int(plan_id)}.")
        db.execute(
            """UPDATE work_plans SET status='aprovado', approved_at=CURRENT_TIMESTAMP,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='aprovando'""",
            (int(plan_id),),
        )
    return task_ids


def reject_work_plan(plan_id):
    with connection() as db:
        cur = db.execute(
            """UPDATE work_plans SET status='rejeitado', rejected_at=CURRENT_TIMESTAMP,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='rascunho'""",
            (int(plan_id),),
        )
        return cur.rowcount > 0

def _insert_task_event(db, task_id, event_type, from_status, to_status, actor, details=""):
    db.execute(
        """INSERT INTO task_events(task_id, event_type, from_status, to_status, actor, details)
           VALUES(?,?,?,?,?,?)""",
        (int(task_id), str(event_type)[:40],
         str(from_status) if from_status is not None else None,
         str(to_status) if to_status is not None else None,
         str(actor or "sistema")[:80], str(details or "")[:8000]),
    )


def list_task_events(task_id, limit=100):
    with connection() as db:
        exists = db.execute("SELECT id FROM department_tasks WHERE id=?", (int(task_id),)).fetchone()
        if not exists:
            return None
        rows = db.execute(
            """SELECT * FROM task_events WHERE task_id=?
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (int(task_id), max(1, min(int(limit), 200))),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def update_department_task(task_id, status, result=None, actor="usuario"):
    """Atualiza tarefa e registra evento auditável na mesma transação."""
    allowed = {"pendente", "em_andamento", "em_revisao", "bloqueada", "concluida", "cancelada"}
    transitions = {
        "pendente": {"em_andamento", "bloqueada", "cancelada"},
        "em_andamento": {"em_revisao", "bloqueada", "concluida", "cancelada"},
        "em_revisao": {"em_andamento", "concluida", "bloqueada"},
        "bloqueada": {"pendente", "em_andamento", "cancelada"},
        "concluida": set(), "cancelada": set(),
    }
    if status not in allowed:
        raise ValueError("Status de tarefa inválido.")
    with connection() as db:
        row = db.execute(
            "SELECT status, result, project_id FROM department_tasks WHERE id=?",
            (int(task_id),),
        ).fetchone()
        if not row:
            return False
        previous = row["status"]
        project_linked = row["project_id"] is not None
        next_result = result if result is not None else row["result"]
        if (
            project_linked
            and status == "em_revisao"
            and status != previous
            and not str(result or "").strip()
        ):
            raise ValueError("Registre as evidências da entrega nesta atualização antes de enviá-la para revisão.")
        if project_linked and status == "concluida":
            if actor != "diretoria":
                raise ValueError("Tarefas de projeto só podem ser concluídas após validação da Diretoria.")
            if previous != "em_revisao":
                raise ValueError("A tarefa precisa estar em revisão para validação da Diretoria.")
        if status != previous and status not in transitions.get(previous, set()):
            raise ValueError(f"Transição não permitida: {previous} -> {status}.")
        cur = db.execute(
            """UPDATE department_tasks SET status=?, result=?, updated_at=CURRENT_TIMESTAMP,
               completed_at=CASE WHEN ?='concluida'
                                 THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END
               WHERE id=?""",
            (status, next_result, status, int(task_id)),
        )
        if cur.rowcount:
            event_type = "status_changed" if status != previous else "result_updated"
            _insert_task_event(db, task_id, event_type, previous, status, actor, result or "")
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
        cur = db.execute(
            """INSERT INTO projects(title,summary,status,approval_status)
               VALUES(?,?,?,'aguardando_aprovacao')""",
            (title, summary, status),
        )
        return cur.lastrowid


def projects(limit=100, approval_status=None):
    with connection() as db:
        if approval_status:
            rows = db.execute(
                "SELECT * FROM projects WHERE approval_status=? ORDER BY id DESC LIMIT ?",
                (approval_status, max(1, min(int(limit), 300))),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM projects ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 300)),),
            ).fetchall()
    return [dict(row) for row in rows]


def project_is_approved(project_id):
    with connection() as db:
        row = db.execute(
            "SELECT 1 FROM projects WHERE id=? AND approval_status='aprovado'",
            (int(project_id),),
        ).fetchone()
    return row is not None


def decide_project(project_id, decision, actor="ceo"):
    if decision not in {"aprovado", "rejeitado"}:
        raise ValueError("Decisão de projeto inválida.")
    with connection() as db:
        project = db.execute(
            "SELECT id,title,summary,approval_status FROM projects WHERE id=?",
            (int(project_id),),
        ).fetchone()
        if not project:
            return None
        if project["approval_status"] != "aguardando_aprovacao":
            return False
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(microsecond=0)
        decided_at = now if _database_url() else now.strftime("%Y-%m-%d %H:%M:%S")
        purge_time = now + timedelta(hours=24) if decision == "rejeitado" else None
        purge_after = (
            purge_time if _database_url()
            else purge_time.strftime("%Y-%m-%d %H:%M:%S") if purge_time else None
        )
        updated = db.execute(
            """UPDATE projects
               SET approval_status=?, approved_at=?, rejected_at=?, canceled_at=NULL, purge_after=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND approval_status='aguardando_aprovacao'""",
            (
                decision,
                decided_at if decision == "aprovado" else None,
                decided_at if decision == "rejeitado" else None,
                purge_after,
                int(project_id),
            ),
        )
        if updated.rowcount != 1:
            return False
        db.execute(
            """INSERT INTO project_decisions
               (project_id,project_title,project_summary,decision,actor,decided_at,purge_after)
               VALUES(?,?,?,?,?,?,?)""",
            (
                int(project_id), project["title"], project["summary"],
                decision, actor, decided_at, purge_after,
            ),
        )
        return {
            "id": int(project_id),
            "status": decision,
            "decided_at": decided_at,
            "purge_after": purge_after,
        }


def cancel_approved_project(project_id, actor="ceo"):
    """Retira um projeto aprovado da operação e agenda exclusão recuperável em 24h."""
    with connection() as db:
        project = db.execute(
            "SELECT id,title,summary FROM projects WHERE id=? AND approval_status='aprovado'",
            (int(project_id),),
        ).fetchone()
        if not project:
            exists = db.execute("SELECT 1 FROM projects WHERE id=?", (int(project_id),)).fetchone()
            return False if exists else None
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(microsecond=0)
        decided_at = now if _database_url() else now.strftime("%Y-%m-%d %H:%M:%S")
        purge_time = now + timedelta(hours=24)
        purge_after = purge_time if _database_url() else purge_time.strftime("%Y-%m-%d %H:%M:%S")
        updated = db.execute(
            """UPDATE projects SET approval_status='cancelado', canceled_at=?,
                   purge_after=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND approval_status='aprovado'""",
            (decided_at, purge_after, int(project_id)),
        )
        if updated.rowcount != 1:
            return False
        db.execute(
            """INSERT INTO project_decisions
               (project_id,project_title,project_summary,decision,actor,decided_at,purge_after)
               VALUES(?,?,?,?,?,?,?)""",
            (int(project_id), project["title"], project["summary"],
             "cancelado", actor, decided_at, purge_after),
        )
        return {"id": int(project_id), "status": "cancelado",
                "decided_at": decided_at, "purge_after": purge_after}


def restore_rejected_project(project_id, actor="ceo"):
    """Restaura rejeitados à fila ou cancelados à operação antes do prazo de 24h."""
    with connection() as db:
        project = db.execute(
            """SELECT id,title,summary,approval_status FROM projects
               WHERE id=? AND approval_status IN ('rejeitado','cancelado')
                 AND purge_after IS NOT NULL AND purge_after > CURRENT_TIMESTAMP""",
            (int(project_id),),
        ).fetchone()
        if not project:
            return False
        from datetime import datetime, timezone
        decided_at = datetime.now(timezone.utc).replace(microsecond=0)
        decided_value = decided_at if _database_url() else decided_at.strftime("%Y-%m-%d %H:%M:%S")
        was_canceled = project["approval_status"] == "cancelado"
        restored_status = "aprovado" if was_canceled else "aguardando_aprovacao"
        updated = db.execute(
            """UPDATE projects SET approval_status=?, rejected_at=NULL,
                   canceled_at=NULL,purge_after=NULL,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND approval_status IN ('rejeitado','cancelado')
                 AND purge_after > CURRENT_TIMESTAMP""",
            (restored_status, int(project_id)),
        )
        if updated.rowcount != 1:
            return False
        db.execute(
            """INSERT INTO project_decisions
               (project_id,project_title,project_summary,decision,actor,decided_at)
               VALUES(?,?,?,?,?,?)""",
            (int(project_id), project["title"], project["summary"],
             "cancelamento_revertido" if was_canceled else "rejeicao_revertida",
             actor, decided_value),
        )
        return {"id": int(project_id), "status": restored_status}


def purge_expired_rejected_projects():
    """Exclui projetos rejeitados/cancelados após 24h e conserva o histórico."""
    with connection() as db:
        expired = db.execute(
            """SELECT id,approval_status FROM projects
               WHERE approval_status IN ('rejeitado','cancelado')
                 AND purge_after IS NOT NULL
                 AND purge_after <= CURRENT_TIMESTAMP
               ORDER BY id"""
        ).fetchall()
        deleted_ids = [int(row["id"]) for row in expired]
        for row in expired:
            project_id = int(row["id"])
            decision = "cancelado" if row["approval_status"] == "cancelado" else "rejeitado"
            db.execute(
                """UPDATE project_decisions SET deleted_at=CURRENT_TIMESTAMP
                   WHERE project_id=? AND decision=? AND deleted_at IS NULL""",
                (project_id, decision),
            )
            db.execute(
                "DELETE FROM projects WHERE id=? AND approval_status=?",
                (project_id, row["approval_status"]),
            )
    return deleted_ids


def update_project(project_id, status):
    with connection() as db:
        cur = db.execute(
            """UPDATE projects SET status=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND approval_status='aprovado'""",
            (status, int(project_id)),
        )
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
