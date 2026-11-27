"""Tests for read-only database context injected into the Director chat."""

import os
import tempfile
import unittest
from unittest.mock import patch

from backend import storage
import main


class DirectorDatabaseContextTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = storage.DB_PATH
        self.previous_database_url = os.environ.pop("DATABASE_URL", None)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "director-context.db")
        storage.initialize()
        self.project_id = storage.save_project("Projeto A", "Projeto usado no teste.")
        self.other_project_id = storage.save_project("Projeto B", "Projeto separado.")
        self.items = [{
            "title": "Validar leitura",
            "description": "Verificar a recuperação dos dados do plano.",
            "department": "programacao",
            "priority": "media",
        }]
        self.plan_id = storage.create_work_plan(
            "Plano A", "Objetivo do plano A.", "Resumo do plano A.",
            self.project_id, self.items,
        )
        self.other_plan_id = storage.create_work_plan(
            "Plano B", "Objetivo do plano B.", "Resumo do plano B.",
            self.other_project_id, self.items,
        )
        storage.reject_work_plan(self.plan_id)

    def tearDown(self):
        storage.DB_PATH = self.previous_db_path
        if self.previous_database_url is not None:
            os.environ["DATABASE_URL"] = self.previous_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_director_context_reads_real_plan_status_and_items_count(self):
        context = main.build_director_data_context(self.project_id)
        self.assertIn("Projeto ativo: #", context)
        self.assertIn("Planos encontrados neste projeto: 1", context)
        self.assertIn("rejeitado=1", context)
        self.assertIn(f"Plano #{self.plan_id}", context)
        self.assertNotIn(f"Plano #{self.other_plan_id}", context)

    def test_unlinked_conversation_does_not_read_other_projects(self):
        with patch.object(storage, "projects") as projects:
            context = main.build_director_data_context(None)
        projects.assert_not_called()
        self.assertIn("nenhuma conversa/projeto está vinculado", context)

    def test_database_context_is_only_injected_for_director(self):
        context = main.build_director_data_context(self.project_id)
        director_prompt = main.build_prompt(
            "Quantos planos foram rejeitados?", "diretoria",
            director_data_context=context,
        )
        engineering_prompt = main.build_prompt(
            "Quantos planos foram rejeitados?", "programacao",
            director_data_context=context,
        )
        self.assertIn("DADOS OPERACIONAIS CONSULTADOS NO BANCO", director_prompt)
        self.assertNotIn("DADOS OPERACIONAIS CONSULTADOS NO BANCO", engineering_prompt)

    def test_database_read_failure_does_not_fabricate_a_count(self):
        with patch.object(storage, "list_work_plans", side_effect=RuntimeError("db unavailable")):
            context = main.build_director_data_context(self.project_id)
        self.assertIn("falha ao recuperar", context)
        self.assertNotIn("rejeitado=0", context)


if __name__ == "__main__":
    unittest.main()
