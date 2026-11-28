"""Integration tests for project progress and Directorate validation."""

import os
import tempfile
import unittest

from backend import storage
from backend.progress import calculate_project_progress


class ProjectProgressIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        self.old_database_url = os.environ.pop("DATABASE_URL", None)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "project-progress.db")
        storage.initialize()
        self.project_id = storage.save_project(
            "Projeto de progresso",
            "Projeto isolado para validar o cálculo automático.",
        )
        storage.decide_project(self.project_id, "aprovado", actor="ceo")

    def tearDown(self):
        storage.DB_PATH = self.old_path
        if self.old_database_url is not None:
            os.environ["DATABASE_URL"] = self.old_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def _create_task(self, title, weight):
        return storage.create_department_task(
            title,
            "Entrega com evidências para o teste de progresso.",
            "programacao",
            "media",
            project_id=self.project_id,
            weight=weight,
        )

    def test_progress_uses_persisted_weights_and_directorate_audit(self):
        accepted = self._create_task("Entrega validada", 3)
        pending_review = self._create_task("Entrega em revisão", 1)

        for task_id in (accepted, pending_review):
            self.assertTrue(storage.update_department_task(
                task_id, "em_andamento", "Execução iniciada.", actor="engenharia"
            ))
            self.assertTrue(storage.update_department_task(
                task_id, "em_revisao", "Evidência: resultado e testes anexados.", actor="engenharia"
            ))

        self.assertTrue(storage.update_department_task(
            accepted, "concluida", actor="diretoria"
        ))
        storage.set_project_department_weights(
            self.project_id, {"programacao": 100}
        )

        inputs = storage.project_progress_inputs(self.project_id)
        self.assertEqual(inputs["project"]["approval_status"], "aprovado")
        by_id = {task["id"]: task for task in inputs["tasks"]}
        self.assertEqual(by_id[accepted]["directorate_validated"], 1)
        self.assertEqual(by_id[pending_review]["directorate_validated"], 0)

        result = calculate_project_progress(
            inputs["tasks"], inputs["department_weights"]
        )
        self.assertEqual(result["progress_percent"], 75.0)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(result["active_tasks"], 2)

    def test_project_task_cannot_be_completed_by_owner(self):
        task_id = self._create_task("Entrega sem validação", 2)
        storage.update_department_task(
            task_id, "em_andamento", "Execução iniciada.", actor="engenharia"
        )
        storage.update_department_task(
            task_id, "em_revisao", "Evidência: relatório de execução.", actor="engenharia"
        )
        with self.assertRaisesRegex(ValueError, "validação da Diretoria"):
            storage.update_department_task(
                task_id, "concluida", actor="proprietario"
            )

    def test_project_task_requires_evidence_before_review(self):
        task_id = self._create_task("Entrega sem evidência", 2)
        storage.update_department_task(
            task_id, "em_andamento", "Execução iniciada.", actor="engenharia"
        )
        with self.assertRaisesRegex(ValueError, "evidências"):
            storage.update_department_task(
                task_id, "em_revisao", actor="engenharia"
            )

    def test_missing_project_returns_no_progress_inputs(self):
        self.assertIsNone(storage.project_progress_inputs(999999))


if __name__ == "__main__":
    unittest.main()
