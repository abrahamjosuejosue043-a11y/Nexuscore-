"""Tests for safe conversation history clearing and deletion."""

import os
import tempfile
import unittest

from backend import storage


class ConversationManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = storage.DB_PATH
        self.previous_database_url = os.environ.pop("DATABASE_URL", None)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "conversation-management.db")
        storage.initialize()

        self.project_id = storage.save_project(
            "Projeto de conversas", "Projeto usado nos testes de gerenciamento de conversas."
        )
        self.conversation_id = "conversation-management-test"
        storage.ensure_conversation(
            self.conversation_id, "Conversa de teste", "diretoria"
        )
        storage.set_conversation_project(self.conversation_id, self.project_id)
        storage.save_message(
            "user", "diretoria", "Primeira mensagem.", conversation_id=self.conversation_id
        )
        storage.save_message(
            "assistant", "diretoria", "Resposta da Diretoria.", "Groq",
            conversation_id=self.conversation_id,
        )
        self.plan_id = storage.create_work_plan(
            "Plano preservado",
            "Objetivo preservado.",
            "Resumo preservado.",
            self.project_id,
            [{
                "title": "Item preservado",
                "description": "Descrição do item preservado.",
                "department": "programacao",
                "priority": "media",
            }],
            conversation_id=self.conversation_id,
        )
        self.task_id = storage.create_department_task(
            "Tarefa preservada",
            "A tarefa operacional deve sobreviver à exclusão da conversa.",
            "programacao",
            conversation_id=self.conversation_id,
            project_id=self.project_id,
            plan_id=self.plan_id,
        )

    def tearDown(self):
        storage.DB_PATH = self.previous_db_path
        if self.previous_database_url is not None:
            os.environ["DATABASE_URL"] = self.previous_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_clear_messages_preserves_conversation_project_tasks_and_plans(self):
        deleted_count = storage.clear_conversation_messages(self.conversation_id)

        self.assertEqual(deleted_count, 2)
        conversation = storage.get_conversation(self.conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(int(conversation["project_id"]), self.project_id)
        self.assertEqual(storage.conversation_messages(self.conversation_id), [])

        tasks = storage.list_department_tasks(limit=20, project_id=self.project_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(int(tasks[0]["id"]), self.task_id)
        self.assertEqual(tasks[0]["conversation_id"], self.conversation_id)

        plans = storage.list_work_plans(limit=20, project_id=self.project_id)
        self.assertEqual(len(plans), 1)
        self.assertEqual(int(plans[0]["id"]), self.plan_id)
        self.assertEqual(plans[0]["conversation_id"], self.conversation_id)
        self.assertEqual(plans[0]["items"][0]["title"], "Item preservado")

    def test_delete_conversation_preserves_operational_records_but_unlinks_origin(self):
        result = storage.delete_conversation(self.conversation_id)

        self.assertEqual(result, {
            "messages_deleted": 2,
            "tasks_preserved": 1,
            "plans_preserved": 1,
        })
        self.assertIsNone(storage.get_conversation(self.conversation_id))
        self.assertEqual(storage.conversation_messages(self.conversation_id), [])

        tasks = storage.list_department_tasks(limit=20, project_id=self.project_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(int(tasks[0]["id"]), self.task_id)
        self.assertIsNone(tasks[0]["conversation_id"])

        plans = storage.list_work_plans(limit=20, project_id=self.project_id)
        self.assertEqual(len(plans), 1)
        self.assertEqual(int(plans[0]["id"]), self.plan_id)
        self.assertIsNone(plans[0]["conversation_id"])
        self.assertEqual(plans[0]["items"][0]["title"], "Item preservado")

    def test_clear_and_delete_return_none_for_unknown_conversation(self):
        self.assertIsNone(storage.clear_conversation_messages("does-not-exist"))
        self.assertIsNone(storage.delete_conversation("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
