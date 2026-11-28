"""Tests for automatic work-plan dispatch from the central chat."""

import json
import os
import tempfile
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend import storage
import main


VALID_PLAN = {
    "titulo": "Plano automático de execução",
    "resumo": "Plano dividido em entregas por departamento.",
    "tarefas": [
        {
            "titulo": "Definir escopo",
            "descricao": "Documentar o escopo, resultado esperado e critérios de aceitação.",
            "departamento": "diretoria",
            "prioridade": "media",
        },
        {
            "titulo": "Preparar entrega técnica",
            "descricao": "Preparar a solução técnica e registrar evidências verificáveis.",
            "departamento": "programacao",
            "prioridade": "alta",
        },
        {
            "titulo": "Revisar comunicação",
            "descricao": "Revisar a comunicação e documentar o material final.",
            "departamento": "publicidade",
            "prioridade": "baixa",
        },
    ],
}


class AutomaticDirectorDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        self.old_database_url = os.environ.pop("DATABASE_URL", None)
        self.old_admin_token = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = "test-admin-token"
        storage.DB_PATH = os.path.join(self.temp_dir.name, "auto-dispatch.db")
        storage.initialize()
        self.project_id = storage.save_project(
            "Projeto automático",
            "Projeto isolado para testar delegação automática.",
        )
        storage.decide_project(self.project_id, "aprovado", actor="ceo")
        main._CHAT_REQUEST_TIMESTAMPS.clear()

    def tearDown(self):
        storage.DB_PATH = self.old_path
        if self.old_database_url is not None:
            os.environ["DATABASE_URL"] = self.old_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        if self.old_admin_token is not None:
            os.environ["ADMIN_TOKEN"] = self.old_admin_token
        else:
            os.environ.pop("ADMIN_TOKEN", None)
        self.temp_dir.cleanup()

    def _login(self, client):
        response = client.post(
            "/api/auth/login", json={"token": "test-admin-token"}
        )
        self.assertEqual(response.status_code, 200, response.text)

    def _plan_response(self):
        return AsyncMock(return_value=(json.dumps(VALID_PLAN), "test-model"))

    def _request(self, text, conversation_id=None):
        return {
            "texto": text,
            "tipo": "geral",
            "conversa_id": conversation_id or str(uuid.uuid4()),
        }

    def _counts(self):
        with storage.connection() as db:
            plans = db.execute("SELECT COUNT(*) AS n FROM work_plans").fetchone()["n"]
            tasks = db.execute("SELECT COUNT(*) AS n FROM department_tasks").fetchone()["n"]
        return plans, tasks

    def test_clear_execute_command_generates_and_dispatches_without_second_approval(self):
        objective = (
            f"Execute o trabalho no projeto #{self.project_id}: preparar uma melhoria "
            "com escopo, entrega técnica e revisão."
        )
        model = self._plan_response()
        with patch("main.chamar_groq", new=model):
            with TestClient(main.app) as client:
                self._login(client)
                response = client.post("/api/chat", json=self._request(objective), headers={"Origin": "http://testserver"})

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["delegado_automaticamente"])
        self.assertEqual(len(body["tarefas_criadas"]), 3)
        self.assertEqual(body["projeto_id"], self.project_id)
        self.assertIn("encaminhei", body["resposta"])
        self.assertEqual(self._counts(), (1, 3))
        plan = storage.get_work_plan(body["plano_id"])
        self.assertEqual(plan["status"], "aprovado")
        tasks = storage.list_department_tasks(limit=20, project_id=self.project_id)
        self.assertEqual({task["assigned_department"] for task in tasks},
                         {"diretoria", "programacao", "publicidade"})
        self.assertEqual(model.await_count, 1)

    def test_same_conversation_retry_reuses_plan_without_duplicate_tasks(self):
        objective = (
            f"Execute no projeto #{self.project_id}: organizar a entrega, "
            "implementar a melhoria e revisar os resultados."
        )
        conversation_id = str(uuid.uuid4())
        model = self._plan_response()
        with patch("main.chamar_groq", new=model):
            with TestClient(main.app) as client:
                self._login(client)
                first = client.post(
                    "/api/chat", json=self._request(objective, conversation_id),
                    headers={"Origin": "http://testserver"},
                )
                second = client.post(
                    "/api/chat", json=self._request(objective, conversation_id),
                    headers={"Origin": "http://testserver"},
                )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["plano_id"], second.json()["plano_id"])
        self.assertTrue(second.json()["reutilizado"])
        self.assertEqual(self._counts(), (1, 3))
        self.assertEqual(model.await_count, 1)

    def test_execute_without_project_asks_for_project_and_creates_nothing(self):
        model = self._plan_response()
        with patch("main.chamar_groq", new=model):
            with TestClient(main.app) as client:
                self._login(client)
                response = client.post(
                    "/api/chat",
                    json=self._request("Execute o trabalho e organize as próximas entregas."),
                    headers={"Origin": "http://testserver"},
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["delegado_automaticamente"])
        self.assertIn("projeto", response.json()["resposta"].lower())
        self.assertEqual(self._counts(), (0, 0))
        model.assert_not_awaited()

    def test_execute_command_requires_admin_session(self):
        objective = (
            f"Execute o trabalho no projeto #{self.project_id}: "
            "organize as próximas entregas."
        )
        model = self._plan_response()
        with patch("main.chamar_groq", new=model):
            with TestClient(main.app) as client:
                response = client.post("/api/chat", json=self._request(objective))

        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self._counts(), (0, 0))
        model.assert_not_awaited()

    def test_question_about_how_to_execute_does_not_auto_dispatch(self):
        model = AsyncMock(return_value=("Explique o procedimento em etapas.", "test-model"))
        with patch("main.chamar_groq", new=model):
            with TestClient(main.app) as client:
                response = client.post(
                    "/api/chat",
                    json=self._request("Como executar uma implantação com segurança?"),
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("delegado_automaticamente", response.json())
        self.assertEqual(self._counts(), (0, 0))
        model.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
