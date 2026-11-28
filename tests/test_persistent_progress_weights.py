"""Tests for persisted task and project-department progress weights."""

import os
import tempfile
import unittest

from backend import storage


class PersistentProgressWeightTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        self.old_database_url = os.environ.pop("DATABASE_URL", None)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "weights.db")
        storage.initialize()
        self.project_id = storage.save_project(
            "Projeto de pesos",
            "Projeto isolado para testar pesos persistentes.",
        )
        storage.decide_project(self.project_id, "aprovado", actor="ceo")

    def tearDown(self):
        storage.DB_PATH = self.old_path
        if self.old_database_url is not None:
            os.environ["DATABASE_URL"] = self.old_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_task_persists_explicit_weight(self):
        task_id = storage.create_department_task(
            "Tarefa ponderada",
            "Tarefa de teste com peso definido explicitamente.",
            "programacao",
            "media",
            project_id=self.project_id,
            weight=7.5,
        )
        task = next(
            item for item in storage.list_department_tasks(project_id=self.project_id)
            if item["id"] == task_id
        )
        self.assertEqual(float(task["weight"]), 7.5)

    def test_task_uses_priority_default_weight(self):
        task_id = storage.create_department_task(
            "Tarefa alta",
            "Tarefa de teste com peso padrão da prioridade.",
            "programacao",
            "alta",
            project_id=self.project_id,
        )
        task = next(
            item for item in storage.list_department_tasks(project_id=self.project_id)
            if item["id"] == task_id
        )
        self.assertEqual(float(task["weight"]), 3.0)

    def test_department_weights_must_sum_to_100_and_persist(self):
        with self.assertRaises(ValueError):
            storage.set_project_department_weights(
                self.project_id, {"programacao": 60, "publicidade": 30}
            )
        saved = storage.set_project_department_weights(
            self.project_id, {"programacao": 60, "publicidade": 40}
        )
        self.assertEqual(sum(float(item["weight"]) for item in saved), 100.0)
        recovered = storage.get_project_department_weights(self.project_id)
        self.assertEqual(
            {item["department"]: float(item["weight"]) for item in recovered},
            {"programacao": 60.0, "publicidade": 40.0},
        )

    def test_department_weights_reject_non_finite_values(self):
        with self.assertRaises(ValueError):
            storage.set_project_department_weights(
                self.project_id, {"programacao": float("nan"), "publicidade": 40}
            )

    def test_work_plan_item_weight_copies_to_delegated_task(self):
        plan_id = storage.create_work_plan(
            "Plano ponderado",
            "Objetivo de teste para persistir peso entre plano e tarefa.",
            "Plano de teste.",
            self.project_id,
            [{
                "title": "Entrega importante",
                "description": "Executar e comprovar a entrega de teste.",
                "department": "programacao",
                "priority": "alta",
                "weight": 8.25,
            }],
        )
        plan = storage.get_work_plan(plan_id)
        self.assertEqual(float(plan["items"][0]["weight"]), 8.25)
        task_ids = storage.approve_work_plan(plan_id)
        tasks = storage.list_department_tasks(project_id=self.project_id)
        task = next(item for item in tasks if item["id"] == task_ids[0])
        self.assertEqual(float(task["weight"]), 8.25)

    def test_existing_schema_has_weight_columns_after_initialize(self):
        with storage.connection() as db:
            task_columns = {row["name"] for row in db.execute(
                "PRAGMA table_info(department_tasks)"
            ).fetchall()}
            plan_item_columns = {row["name"] for row in db.execute(
                "PRAGMA table_info(work_plan_items)"
            ).fetchall()}
        self.assertIn("weight", task_columns)
        self.assertIn("weight", plan_item_columns)


if __name__ == "__main__":
    unittest.main()
