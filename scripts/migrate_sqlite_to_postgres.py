"""Copia explícita e não destrutiva do SQLite do Nexuscore para PostgreSQL.

Uso:
  DIRECT_DATABASE_URL='postgresql://...' python scripts/migrate_sqlite_to_postgres.py /caminho/nexuscore.db

O destino precisa estar vazio. O script cria um backup SQLite antes de copiar,
não apaga o arquivo de origem e confirma as contagens no destino.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys

TABLES = ("chat_sessions", "conversations", "ideas", "projects", "artifacts", "email_log", "shared_memory")
OPTIONAL_TABLES = {"chat_sessions", "shared_memory"}
SERIAL_TABLES = ("conversations", "ideas", "projects", "artifacts", "email_log", "shared_memory")


def create_backup(source: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = source.with_name(f"{source.stem}.pre-postgres-{stamp}{source.suffix}")
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(backup)) as dst:
        src.backup(dst)
    return backup


def migrate(source: Path, database_url: str) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"Arquivo SQLite não encontrado: {source}")
    if not database_url:
        raise ValueError("Defina DIRECT_DATABASE_URL ou DATABASE_URL no ambiente.")

    try:
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Instale as dependências com: pip install -r requirements.txt") from exc

    backup = create_backup(source)

    # Inicializa o esquema PostgreSQL com o mesmo contrato usado pela aplicação.
    os.environ["DATABASE_URL"] = database_url
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend import storage
    storage.initialize()

    source_conn = sqlite3.connect(str(source))
    source_conn.row_factory = sqlite3.Row
    copied = {}

    try:
        with psycopg.connect(database_url, connect_timeout=20, row_factory=dict_row) as target:
            # A origem pode ser de uma versão anterior, sem chat_sessions/conversation_id.
            source_tables = {
                row["name"] for row in source_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required_tables = set(TABLES) - OPTIONAL_TABLES
            missing = required_tables - source_tables
            if missing:
                raise RuntimeError(
                    "Tabelas obrigatórias ausentes no SQLite: " + ", ".join(sorted(missing))
                )

            source_message_columns = {
                row["name"] for row in source_conn.execute(
                    "PRAGMA table_info(conversations)"
                ).fetchall()
            }
            source_message_count = source_conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            legacy_id = "legacy-import"
            needs_legacy_session = (
                "chat_sessions" not in source_tables
                and source_message_count > 0
            )

            # Confere todas as tabelas do destino antes de copiar.
            for table in TABLES:
                target_count = target.execute(
                    sql.SQL("SELECT COUNT(*) AS n FROM {}").format(sql.Identifier(table))
                ).fetchone()["n"]
                if target_count:
                    raise RuntimeError(
                        f"O destino não está vazio: '{table}' já contém {target_count} registros. "
                        "Nenhum registro foi copiado."
                    )

            with target.transaction():
                for table in TABLES:
                    if table == "chat_sessions" and table not in source_tables:
                        rows = (
                            [{"id": legacy_id, "title": "Histórico anterior", "agent": "geral"}]
                            if needs_legacy_session else []
                        )
                    elif table in OPTIONAL_TABLES and table not in source_tables:
                        rows = []
                    else:
                        rows = source_conn.execute(f"SELECT * FROM {table}").fetchall()

                    if table == "conversations" and "conversation_id" not in source_message_columns:
                        # A versão SQLite antiga não tinha agrupamento por conversa.
                        columns = list(rows[0].keys()) + ["conversation_id"] if rows else []
                        values = [tuple(row) + (legacy_id,) for row in rows]
                    elif rows:
                        columns = list(rows[0].keys())
                        values = [tuple(row) for row in rows]
                    else:
                        columns, values = [], []

                    if values:
                        insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                            sql.Identifier(table),
                            sql.SQL(", ").join(map(sql.Identifier, columns)),
                            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                        )
                        with target.cursor() as cursor:
                            cursor.executemany(insert, values)
                    copied[table] = len(rows)

                # Mantém os próximos IDs acima dos IDs que foram copiados.
                for table in SERIAL_TABLES:
                    target.execute(
                        sql.SQL(
                            "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                            "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {}"
                        ).format(sql.Identifier(table)),
                        (table,),
                    )

                for table in TABLES:
                    count = target.execute(
                        sql.SQL("SELECT COUNT(*) AS n FROM {}").format(sql.Identifier(table))
                    ).fetchone()["n"]
                    if count != copied[table]:
                        raise RuntimeError(
                            f"Verificação falhou em '{table}': origem={copied[table]}, destino={count}."
                        )
    finally:
        source_conn.close()

    return {"backup": str(backup), "copied": copied}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite_file", type=Path, help="Caminho do arquivo SQLite original")
    args = parser.parse_args()
    url = os.getenv("DIRECT_DATABASE_URL") or os.getenv("DATABASE_URL")
    try:
        result = migrate(args.sqlite_file.expanduser().resolve(), url or "")
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Backup criado: {result['backup']}")
    for table, count in result["copied"].items():
        print(f"{table}: {count} registros copiados e verificados")
    print("Migração concluída. O arquivo SQLite original foi mantido.")


if __name__ == "__main__":
    main()
