"""Integration tests for work-plan generation and transactional persistence."""

import json
import logging
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend import storage
import main


VALID_PLAN = {
    "titulo": "Plano de validação de persistência",
    "resumo": "Plano de teste para verificar gravação e recuperação.",
    "tarefas": [
        {
            "titulo": "Levantar requisitos",
            "descricao": "Documentar requisitos e validar o resultado esperado.",
            "departamento": "diretoria",
            "prioridade": "media",
        },
        {
            "titulo": "Implementar estrutura",
            "descricao": "Preparar estrutura técnica e validar persistência.",
            "departamento": "programacao",
            "prioridade": "alta",
        },
        {
            "titulo": "Revisar documentação",
            "descricao": "Revisar documentação e confirmar critérios de aceitação.",
            "departamento": "geral",
            "prioridade": "baixa",
        },
    ],
}


class WorkPlanPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = storage.DB_PATH
        self.previous_database_url = os.environ.pop("DATABASE_URL", None)
        self.previous_admin_token = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = "test-admin-token"
        storage.DB_PATH = os.path.join(self.temp_dir.name, "nexuscore-test.db")
        storage.initialize()
        self.project_id = storage.save_project(
            "Projeto de teste de persistência",
            "Projeto isolado usado exclusivamente pelos testes automatizados.",
        )

    def tearDown(self):
        storage.DB_PATH = self.previous_db_path
        if self.previous_database_url is not None:
            os.environ["DATABASE_URL"] = self.previous_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        if self.previous_admin_token is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = self.previous_admin_token
        self.temp_dir.cleanup()

    def _client(self):
        return TestClient(main.app)

    def _mock_groq(self, payload=VALID_PLAN):
        return AsyncMock(return_value=(json.dumps(payload), "test-model"))

    def _request_payload(self):
        return {
            "objetivo": (
                "Validar a criação, persistência e recuperação de um plano "
                "de trabalho sem delegar tarefas antes da aprovação."
            ),
            "projeto_id": self.project_id,
        }

    def _counts(self):
        with storage.connection() as db:
            plans = db.execute("SELECT COUNT(*) AS total FROM work_plans").fetchone()["total"]
            items = db.execute("SELECT COUNT(*) AS total FROM work_plan_items").fetchone()["total"]
            tasks = db.execute("SELECT COUNT(*) AS total FROM department_tasks").fetchone()["total"]
        return plans, items, tasks

    def test_generate_persists_plan_items_and_returns_same_project(self):
        with patch("main.chamar_groq", new=self._mock_groq()):
            with self._client() as client:
                response = client.post(
                    "/api/planos/gerar",
                    json=self._request_payload(),
                    headers={"X-Admin-Token": "test-admin-token"},
                )
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                plan = body["plan"]
                plan_id = plan["id"]

                self.assertIsInstance(plan_id, int)
                self.assertGreater(plan_id, 0)
                self.assertEqual(plan["project_id"], self.project_id)
                self.assertEqual(plan["status"], "rascunho")
                self.assertEqual(len(plan["items"]), 3)
                self.assertEqual(body["status"], "rascunho_aguardando_aprovacao")

                listed = client.get(
                    f"/api/planos?projeto_id={self.project_id}",
                    headers={"X-Admin-Token": "test-admin-token"},
                )
                self.assertEqual(listed.status_code, 200, listed.text)
                matching = [item for item in listed.json()["items"] if item["id"] == plan_id]
                self.assertEqual(len(matching), 1)
                self.assertEqual([item["id"] for item in matching[0]["items"]],
                                 [item["id"] for item in plan["items"]])

                tasks = client.get(
                    "/api/tarefas",
                    headers={"X-Admin-Token": "test-admin-token"},
                )
                self.assertEqual(tasks.status_code, 200, tasks.text)
                self.assertEqual(tasks.json()["items"], [])

        self.assertEqual(self._counts(), (1, 3, 0))

    def test_invalid_model_response_does_not_create_records(self):
        with patch("main.chamar_groq", new=AsyncMock(return_value=("not-json", "test-model"))):
            with self._client() as client:
                response = client.post(
                    "/api/planos/gerar",
                    json=self._request_payload(),
                    headers={"X-Admin-Token": "test-admin-token"},
                )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self._counts(), (0, 0, 0))

    def test_persistence_exception_returns_safe_500_and_logs_error(self):
        with patch("main.chamar_groq", new=self._mock_groq()):
            with patch("main.storage.create_work_plan", side_effect=RuntimeError("database unavailable")):
                with self.assertLogs("nexuscore", level=logging.ERROR) as captured:
                    with TestClient(main.app, raise_server_exceptions=False) as client:
                        response = client.post(
                            "/api/planos/gerar",
                            json=self._request_payload(),
                            headers={"X-Admin-Token": "test-admin-token"},
                        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("Não foi possível persistir", response.json()["detail"])
        self.assertTrue(any("Falha ao persistir ou recuperar plano" in line
                            for line in captured.output))
        self.assertEqual(self._counts(), (0, 0, 0))

    def test_item_failure_rolls_back_plan_and_previous_items(self):
        items = [
            {
                "title": "Item válido",
                "description": "Descrição válida para o item.",
                "department": "programacao",
                "priority": "media",
            },
            {
                "title": "Item inválido",
                # Campo description omitido intencionalmente para provocar falha.
                "department": "programacao",
                "priority": "media",
            },
        ]
        with self.assertRaises(KeyError):
            storage.create_work_plan(
                "Plano transacional",
                "Objetivo de teste de rollback.",
                "Resumo de teste.",
                self.project_id,
                items,
            )
        self.assertEqual(self._counts(), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
