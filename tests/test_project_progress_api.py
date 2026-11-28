"""API tests for hybrid project progress and Directorate validation."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend import storage
import main


class ProjectProgressApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        self.old_database_url = os.environ.pop("DATABASE_URL", None)
        self.old_admin_token = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = "test-progress-token"
        storage.DB_PATH = os.path.join(self.temp_dir.name, "progress-api.db")
        storage.initialize()
        self.client = TestClient(main.app)
        self.headers = {"X-Admin-Token": "test-progress-token"}
        self.project_id = storage.save_project(
            "Projeto API progresso",
            "Projeto para testar cálculo e validação pela Diretoria.",
        )
        storage.decide_project(self.project_id, "aprovado", actor="ceo")

    def tearDown(self):
        self.client.close()
        storage.DB_PATH = self.old_path
        if self.old_database_url is not None:
            os.environ["DATABASE_URL"] = self.old_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        if self.old_admin_token is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = self.old_admin_token
        self.temp_dir.cleanup()

    def test_progress_endpoint_requires_admin_token(self):
        response = self.client.get(
            f"/api/projetos/{self.project_id}/progresso"
        )
        self.assertEqual(response.status_code, 401)

    def test_progress_endpoint_returns_weighted_live_calculation(self):
        task_id = storage.create_department_task(
            "Entrega API",
            "Entregar e registrar evidências.",
            "programacao",
            "media",
            project_id=self.project_id,
            weight=5,
        )
        storage.update_department_task(
            task_id, "em_andamento", "Execução iniciada.", actor="engenharia"
        )
        storage.update_department_task(
            task_id, "em_revisao", "Evidência: teste concluído.", actor="engenharia"
        )
        storage.set_project_department_weights(
            self.project_id, {"programacao": 100}
        )

        before = self.client.get(
            f"/api/projetos/{self.project_id}/progresso",
            headers=self.headers,
        )
        self.assertEqual(before.status_code, 200)
        self.assertEqual(before.json()["progress_percent"], 0.0)
        self.assertEqual(before.json()["completed_tasks"], 0)

        validated = self.client.post(
            f"/api/tarefas/{task_id}/validar",
            headers=self.headers,
        )
        self.assertEqual(validated.status_code, 200)
        self.assertEqual(validated.json()["validada_por"], "diretoria")

        after = self.client.get(
            f"/api/projetos/{self.project_id}/progresso",
            headers=self.headers,
        )
        self.assertEqual(after.status_code, 200)
        self.assertEqual(after.json()["progress_percent"], 100.0)
        self.assertEqual(after.json()["completed_tasks"], 1)
        self.assertEqual(after.json()["departments"][0]["department"], "programacao")

    def test_validation_endpoint_rejects_task_not_in_review(self):
        task_id = storage.create_department_task(
            "Entrega ainda não revisada",
            "Não pode ser concluída sem passar por revisão.",
            "programacao",
            "media",
            project_id=self.project_id,
        )
        response = self.client.post(
            f"/api/tarefas/{task_id}/validar",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_unapproved_project_has_no_operational_progress(self):
        project_id = storage.save_project(
            "Projeto pendente",
            "Não deve ter progresso operacional.",
        )
        response = self.client.get(
            f"/api/projetos/{project_id}/progresso",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
