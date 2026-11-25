import os
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
