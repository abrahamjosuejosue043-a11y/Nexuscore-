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
        self.assertIn("Projeto identificado: #", context)
        self.assertIn("Planos encontrados neste projeto: 1", context)
        self.assertIn("rejeitado=1", context)
        self.assertIn(f"Plano #{self.plan_id}", context)
        self.assertIn("Objetivo do plano A.", context)
        self.assertIn("Resumo do plano A.", context)
        self.assertIn("Motivo da rejeição: não registrado no banco de dados.", context)
        self.assertNotIn(f"Plano #{self.other_plan_id}", context)
        self.assertNotIn("Objetivo do plano B.", context)

    def test_status_counts_include_all_plans_without_list_limit(self):
        counts = storage.work_plan_status_counts(self.project_id)
        self.assertEqual(counts, {"rejeitado": 1})
        self.assertEqual(sum(counts.values()), 1)

    def test_unlinked_conversation_does_not_read_other_projects(self):
        context = main.build_director_data_context(None)
        self.assertIn("nenhum projeto foi identificado", context)
        self.assertIn("Projeto A", context)
        self.assertIn("Projeto B", context)

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

    def test_director_resolves_project_by_id(self):
        project_id, note, projects = main.resolve_director_project(
            f"Consulte o projeto #{self.project_id}"
        )
        self.assertEqual(project_id, self.project_id)
        self.assertIsNone(note)

    def test_director_resolves_project_by_full_or_short_name(self):
        project_id, note, _ = main.resolve_director_project("Analise o Projeto A")
        self.assertEqual(project_id, self.project_id)
        self.assertIsNone(note)

    def test_director_uses_existing_project_when_no_new_reference_is_given(self):
        project_id, note, _ = main.resolve_director_project(
            "Quantos planos existem?", current_project_id=self.project_id
        )
        self.assertEqual(project_id, self.project_id)
        self.assertIsNone(note)

    def test_director_asks_when_project_name_is_ambiguous(self):
        storage.save_project("Projeto A", "Segundo projeto com nome duplicado.")
        project_id, note, _ = main.resolve_director_project("Analise Projeto A")
        self.assertIsNone(project_id)
        self.assertIn("mais de um projeto", note)

    def test_director_does_not_guess_unknown_project_id(self):
        project_id, note, _ = main.resolve_director_project("Consulte o projeto #9999")
        self.assertIsNone(project_id)
        self.assertIn("não encontrei projeto", note.lower())
    def test_director_resolves_project_by_name_prefix(self):
        storage.save_project("Teste de Persistência de Planos no PostgreSQL", "Projeto de teste.")
        project_id, note, _ = main.resolve_director_project(
            "Consulte o projeto Teste de Persistência e conte os planos."
        )
        self.assertIsNotNone(project_id)
        self.assertIsNone(note)

    def test_plan_number_does_not_get_mistaken_for_project_number(self):
        project_id, note, _ = main.resolve_director_project(
            "Consulte o plano #2", current_project_id=self.project_id
        )
        self.assertEqual(project_id, self.project_id)
        self.assertIsNone(note)
    def test_director_does_not_fall_back_to_current_project_for_unknown_name(self):
        project_id, note, _ = main.resolve_director_project(
            "Consulte o projeto que ainda não foi cadastrado.", current_project_id=self.project_id
        )
        self.assertIsNone(project_id)
        self.assertIn("não encontrei um projeto cadastrado", note.lower())
    def test_director_recovers_current_project_from_same_conversation_history(self):
        conversation_id = "test-director-project-continuity"
        storage.ensure_conversation(conversation_id, "Teste de continuidade", "diretoria")
        storage.save_message(
            "user", "diretoria",
            "Localize o projeto pelo nome Projeto A e consulte os planos.",
            conversation_id=conversation_id,
        )
        history = storage.conversation_messages(conversation_id, limit=20)
        project_id, note, _ = main.resolve_director_project_with_history(
            "Detalhe o plano #2 do projeto atual.",
            current_project_id=None,
            history=history,
        )
        self.assertEqual(project_id, self.project_id)
        self.assertIsNone(note)

    def test_director_does_not_recover_project_from_assistant_only_history(self):
        history = [{
            "role": "assistant",
            "content": "O projeto Projeto A tem ID 1.",
        }]
        project_id, note, _ = main.resolve_director_project_with_history(
            "Consulte o projeto atual.",
            current_project_id=None,
            history=history,
        )
        self.assertIsNone(project_id)
        self.assertIsNone(note)

    def test_database_read_failure_does_not_fabricate_a_count(self):
        with patch.object(storage, "list_work_plans", side_effect=RuntimeError("db unavailable")):
            context = main.build_director_data_context(self.project_id)
        self.assertIn("falha ao recuperar", context)
        self.assertNotIn("rejeitado=0", context)


if __name__ == "__main__":
    unittest.main()
