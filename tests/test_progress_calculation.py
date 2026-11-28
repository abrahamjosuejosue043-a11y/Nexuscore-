import unittest

from backend.progress import calculate_project_progress


class HybridProjectProgressTests(unittest.TestCase):
    def test_empty_project_has_zero_progress(self):
        result = calculate_project_progress([])
        self.assertEqual(result["progress_percent"], 0)
        self.assertEqual(result["total_tasks"], 0)
        self.assertEqual(result["departments"], [])

    def test_completed_only_counts_after_directorate_validation(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida", "priority": "alta"},
            {"assigned_department": "programacao", "status": "em_revisao", "priority": "media"},
            {"assigned_department": "programacao", "status": "em_andamento", "priority": "baixa"},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 50.0)
        self.assertEqual(result["departments"][0]["progress_percent"], 50.0)
        self.assertEqual(result["completed_tasks"], 1)

    def test_department_weights_control_hybrid_project_progress(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida"},
            {"assigned_department": "publicidade", "status": "pendente"},
        ]
        result = calculate_project_progress(
            tasks, department_weights={"programacao": 60, "publicidade": 40}
        )
        self.assertEqual(result["progress_percent"], 60.0)

    def test_planned_department_without_tasks_counts_as_zero(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida"},
        ]
        result = calculate_project_progress(
            tasks, department_weights={"programacao": 60, "publicidade": 40}
        )
        self.assertEqual(result["progress_percent"], 60.0)
        marketing = next(
            item for item in result["departments"]
            if item["department"] == "publicidade"
        )
        self.assertEqual(marketing["progress_percent"], 0)
        self.assertEqual(marketing["total_tasks"], 0)

    def test_cancelled_tasks_are_excluded_from_denominator(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida"},
            {"assigned_department": "programacao", "status": "cancelada"},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 100.0)
        self.assertEqual(result["total_tasks"], 2)
        self.assertEqual(result["active_tasks"], 1)
        self.assertEqual(result["cancelled_tasks"], 1)
        self.assertEqual(result["departments"][0]["cancelled_tasks"], 1)

    def test_priority_is_used_as_default_task_weight(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida", "priority": "alta"},
            {"assigned_department": "programacao", "status": "pendente", "priority": "baixa"},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 75.0)

    def test_explicit_task_weight_overrides_priority(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida", "priority": "baixa", "weight": 9},
            {"assigned_department": "programacao", "status": "pendente", "priority": "alta", "weight": 1},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 90.0)

    def test_unknown_priority_uses_neutral_medium_weight(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida", "priority": "urgente"},
            {"assigned_department": "programacao", "status": "pendente", "priority": "media"},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 50.0)

    def test_invalid_task_status_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_project_progress([
                {"assigned_department": "programacao", "status": "desconhecido"}
            ])

    def test_invalid_task_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_project_progress([
                {"assigned_department": "programacao", "status": "pendente", "weight": 0}
            ])

    def test_invalid_department_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_project_progress([], department_weights={"programacao": -2})

    def test_missing_department_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_project_progress([{"status": "pendente"}])

    def test_unconfigured_departments_receive_equal_weight(self):
        tasks = [
            {"assigned_department": "programacao", "status": "concluida"},
            {"assigned_department": "publicidade", "status": "pendente"},
        ]
        result = calculate_project_progress(tasks)
        self.assertEqual(result["progress_percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
