import os
import tempfile
import unittest
from pathlib import Path

from main import build_conversation_title


class StorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(cls.temp_dir.name) / "test.db")
        from backend import storage
        cls.storage = storage
        cls.storage.initialize()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_save_and_read_conversation(self):
        self.storage.save_message("user", "geral", "Teste de persistência")
        items = self.storage.messages(10)
        self.assertTrue(any(item["content"] == "Teste de persistência" for item in items))

    def test_save_and_download_artifact(self):
        artifact_id = self.storage.save_artifact("Relatório", "relatorio.txt", "txt", "text/plain", b"conteudo")
        item = self.storage.artifact(artifact_id)
        self.assertEqual(item["content"], b"conteudo")
        self.assertEqual(item["filename"], "relatorio.txt")

    def test_list_artifacts_hides_binary_content(self):
        self.storage.save_artifact("Arquivo", "arquivo.md", "md", "text/markdown", b"# teste")
        items = self.storage.artifacts(10)
        self.assertTrue(any(item["filename"] == "arquivo.md" for item in items))
        self.assertNotIn("content", items[0])

    def test_save_and_read_idea(self):
        idea_id = self.storage.save_idea("Ideia de teste", "Resumo de teste", "alta")
        items = self.storage.ideas(10)
        self.assertTrue(any(item["id"] == idea_id for item in items))

    def test_database_health_reports_wal_and_existing_file(self):
        health = self.storage.health()
        self.assertEqual(health["engine"], "sqlite")
        self.assertTrue(health["database_exists"])
        self.assertEqual(health["journal_mode"], "wal")
        self.assertGreaterEqual(health["table_count"], 5)

    def test_postgres_insert_returns_created_id(self):
        class FakeCursor:
            rowcount = 1

            def fetchone(self):
                return {"id": 123}

        class FakeConnection:
            def __init__(self):
                self.statement = None
                self.params = None

            def execute(self, statement, params):
                self.statement = statement
                self.params = params
                return FakeCursor()

        raw = FakeConnection()
        db = self.storage._PostgresConnection(raw)
        cursor = db.execute(
            "INSERT INTO ideas(title, summary, priority) VALUES(?,?,?)",
            ("Ideia", "Resumo", "media"),
        )
        self.assertIn("RETURNING id", raw.statement)
        self.assertEqual(cursor.lastrowid, 123)
        self.assertEqual(raw.params, ("Ideia", "Resumo", "media"))

    def test_chat_conversation_groups_messages_and_can_be_renamed(self):
        conversation_id = "thread-test-001"
        created = self.storage.ensure_conversation(
            conversation_id, "Organizar projetos", "geral"
        )
        self.assertEqual(created["title"], "Organizar projetos")

        # A retomada da mesma conversa não pode substituir o título original.
        same = self.storage.ensure_conversation(
            conversation_id, "Outro assunto", "geral"
        )
        self.assertEqual(same["title"], "Organizar projetos")

        self.storage.save_message(
            "user", "geral", "Quero organizar meus projetos", conversation_id=conversation_id
        )
        self.storage.save_message(
            "assistant", "geral", "Vamos criar uma estrutura.", "Groq",
            conversation_id=conversation_id,
        )

        messages = self.storage.conversation_messages(conversation_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

        listed = self.storage.list_conversations(100)
        item = next(x for x in listed if x["id"] == conversation_id)
        self.assertEqual(item["message_count"], 2)
        self.assertTrue(self.storage.rename_conversation(conversation_id, "Projetos organizados"))
        self.assertEqual(
            self.storage.get_conversation(conversation_id)["title"],
            "Projetos organizados",
        )

    def test_legacy_messages_are_grouped_in_previous_history(self):
        self.storage.save_message("user", "geral", "Mensagem antiga sem sessão")
        with self.storage.connection() as db:
            self.storage._backfill_legacy_messages(db)
        legacy = self.storage.get_conversation("legacy")
        self.assertEqual(legacy["title"], "Histórico anterior")
        self.assertTrue(
            any(
                x["content"] == "Mensagem antiga sem sessão"
                for x in self.storage.conversation_messages("legacy")
            )
        )

    def test_postgres_placeholder_adapter_preserves_legacy_queries(self):
        self.assertEqual(
            self.storage._qmark_to_pyformat(
                "INSERT INTO email_log(direction, recipient) VALUES(?,?)"
            ),
            "INSERT INTO email_log(direction, recipient) VALUES(%s,%s)",
        )

    def test_connection_rolls_back_failed_transaction(self):
        with self.assertRaises(RuntimeError):
            with self.storage.connection() as db:
                db.execute(
                    "INSERT INTO ideas(title, summary, priority) VALUES(?,?,?)",
                    ("Não salvar", "transação de teste", "media"),
                )
                raise RuntimeError("forçar rollback")
        items = self.storage.ideas(300)
        self.assertFalse(any(item["title"] == "Não salvar" for item in items))


class ConversationTitleTests(unittest.TestCase):
    def test_title_is_derived_from_first_message(self):
        title = build_conversation_title(
            "Bom dia! Quero organizar conversas por assunto e agente no Nexuscore"
        )
        self.assertEqual(
            title,
            "Organizar conversas por assunto e agente no Nexuscore",
        )

    def test_empty_conversation_title_has_safe_fallback(self):
        self.assertEqual(build_conversation_title("  "), "Nova conversa")


if __name__ == "__main__":
    unittest.main()
