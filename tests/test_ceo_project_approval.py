"""Tests for CEO project approval and 24-hour rejection expiry."""

import os
import tempfile
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from backend import storage
import main


class CEOProjectApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = storage.DB_PATH
        self.previous_database_url = os.environ.pop("DATABASE_URL", None)
        self.previous_admin_token = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = "test-admin-token"
        storage.DB_PATH = os.path.join(self.temp_dir.name, "project-approval.db")
        storage.initialize()
        self.client = TestClient(main.app)
        self.headers = {"X-Admin-Token": "test-admin-token"}

    def tearDown(self):
        self.client.close()
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

    def _create_project(self):
        response = self.client.post(
            "/api/projetos",
            json={
                "titulo": "Projeto aguardando CEO",
                "resumo": "Projeto isolado para validar aprovação e rejeição.",
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["id"]

    def test_new_project_waits_for_ceo_and_is_not_in_approved_filter(self):
        project_id = self._create_project()
        self.assertFalse(storage.project_is_approved(project_id))
        pending = self.client.get(
            "/api/projetos?approval_status=aguardando_aprovacao",
            headers=self.headers,
        )
        approved = self.client.get(
            "/api/projetos?approval_status=aprovado",
            headers=self.headers,
        )
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(approved.status_code, 200)
        self.assertIn(project_id, [item["id"] for item in pending.json()["items"]])
        self.assertNotIn(project_id, [item["id"] for item in approved.json()["items"]])

    def test_only_approved_project_can_be_used_by_director_and_planning(self):
        project_id = self._create_project()
        self.assertFalse(storage.set_conversation_project("test-conversation", project_id))
        response = self.client.post(
            "/api/planos/gerar",
            json={
                "objetivo": "Validar que projetos pendentes não recebem planos de trabalho.",
                "projeto_id": project_id,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)

        approved = self.client.post(
            f"/api/projetos/{project_id}/aprovar", headers=self.headers
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "aprovado")
        self.assertTrue(storage.project_is_approved(project_id))
        self.assertEqual(
            self.client.post(
                f"/api/projetos/{project_id}/rejeitar", headers=self.headers
            ).status_code,
            409,
        )

    def test_rejection_sets_exactly_24_hours_and_expiry_deletes_project_but_keeps_audit(self):
        project_id = self._create_project()
        rejected = self.client.post(
            f"/api/projetos/{project_id}/rejeitar", headers=self.headers
        )
        self.assertEqual(rejected.status_code, 200)
        data = rejected.json()
        self.assertEqual(data["status"], "rejeitado")
        self.assertEqual(data["exclusao_automatica_em_horas"], 24)

        decided_at = datetime.strptime(data["decided_at"], "%Y-%m-%d %H:%M:%S")
        purge_after = datetime.strptime(data["purge_after"], "%Y-%m-%d %H:%M:%S")
        self.assertEqual((purge_after - decided_at).total_seconds(), 24 * 60 * 60)
        self.assertEqual(storage.purge_expired_rejected_projects(), [])
        self.assertIsNotNone(storage.projects(approval_status="rejeitado"))

        with storage.connection() as db:
            db.execute(
                "UPDATE projects SET purge_after='2000-01-01 00:00:00' WHERE id=?",
                (project_id,),
            )
        self.assertEqual(storage.purge_expired_rejected_projects(), [project_id])
        self.assertFalse(storage.project_exists(project_id))
        with storage.connection() as db:
            audit = db.execute(
                "SELECT * FROM project_decisions WHERE project_id=? AND decision='rejeitado'",
                (project_id,),
            ).fetchone()
        self.assertIsNotNone(audit)
        self.assertIsNotNone(audit["deleted_at"])
        self.assertEqual(audit["project_title"], "Projeto aguardando CEO")
        self.assertEqual(audit["actor"], "ceo")

    def test_cleanup_does_not_delete_approved_or_pending_projects(self):
        pending_id = self._create_project()
        approved_id = self._create_project()
        self.client.post(f"/api/projetos/{approved_id}/aprovar", headers=self.headers)
        with storage.connection() as db:
            db.execute(
                "UPDATE projects SET purge_after='2000-01-01 00:00:00' WHERE id IN (?,?)",
                (pending_id, approved_id),
            )
        self.assertEqual(storage.purge_expired_rejected_projects(), [])
        self.assertTrue(storage.project_exists(pending_id))
        self.assertTrue(storage.project_exists(approved_id))

    def test_project_decisions_require_admin_token(self):
        project_id = self._create_project()
        response = self.client.post(f"/api/projetos/{project_id}/rejeitar")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(storage.projects(approval_status="aguardando_aprovacao")[0]["id"], project_id)


if __name__ == "__main__":
    unittest.main()
