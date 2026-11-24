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

    def test_save_and_read_idea(self):
        idea_id = self.storage.save_idea("Ideia de teste", "Resumo de teste", "alta")
        items = self.storage.ideas(10)
        self.assertTrue(any(item["id"] == idea_id for item in items))


if __name__ == "__main__":
    unittest.main()
