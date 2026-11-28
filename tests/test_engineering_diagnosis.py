import unittest

from backend.engineering import build_engineering_diagnosis_prompt


class EngineeringDiagnosisPromptTests(unittest.TestCase):
    def test_prompt_includes_objective_and_source_path_as_evidence(self):
        prompt = build_engineering_diagnosis_prompt(
            "Investigar falha no fluxo de autenticação e propor correção.",
            [{"path": "backend/auth.py", "content": "def login(): return False"}],
        )
        self.assertIn("Investigar falha", prompt)
        self.assertIn("backend/auth.py", prompt)
        self.assertIn("DADOS NÃO CONFIÁVEIS", prompt)
        self.assertIn("Não afirme que alterou código", prompt)

    def test_prompt_rejects_empty_or_excessive_file_lists(self):
        with self.assertRaises(ValueError):
            build_engineering_diagnosis_prompt("Objetivo válido", [])
        with self.assertRaises(ValueError):
            build_engineering_diagnosis_prompt(
                "Objetivo válido",
                [{"path": f"backend/{i}.py", "content": "x"} for i in range(5)],
            )

    def test_prompt_enforces_combined_source_budget(self):
        with self.assertRaises(ValueError):
            build_engineering_diagnosis_prompt(
                "Objetivo válido",
                [{"path": "backend/large.py", "content": "x" * 24001}],
            )

    def test_prompt_rejects_invalid_file_payload(self):
        with self.assertRaises(ValueError):
            build_engineering_diagnosis_prompt("Objetivo válido", [{"path": "../secret", "content": None}])


if __name__ == "__main__":
    unittest.main()
