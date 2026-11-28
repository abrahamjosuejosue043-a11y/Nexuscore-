import unittest

from backend.engineering_patch import (
    build_patch_proposal_prompt,
    validate_unified_diff,
)


class EngineeringPatchProposalTests(unittest.TestCase):
    def test_validates_only_requested_existing_source_files(self):
        diff = "--- a/backend/example.py\n+++ b/backend/example.py\n@@ -1 +1 @@\n-old\n+new\n"
        result = validate_unified_diff(diff, ["backend/example.py"])
        self.assertEqual(result["files"], ["backend/example.py"])

    def test_rejects_unrequested_or_forbidden_paths(self):
        diff = "--- a/.github/workflows/ci.yml\n+++ b/.github/workflows/ci.yml\n@@ -1 +1 @@\n-a\n+b\n"
        with self.assertRaises(Exception):
            validate_unified_diff(diff, [".github/workflows/ci.yml"])

    def test_rejects_new_deleted_and_renamed_files(self):
        with self.assertRaises(ValueError):
            validate_unified_diff("--- /dev/null\n+++ b/backend/new.py\n@@ -0,0 +1 @@\n+x\n", ["backend/new.py"])
        with self.assertRaises(ValueError):
            validate_unified_diff("--- a/backend/old.py\n+++ b/backend/new.py\n@@ -1 +1 @@\n-a\n+b\n", ["backend/old.py"])

    def test_rejects_invalid_or_oversized_diff(self):
        with self.assertRaises(ValueError):
            validate_unified_diff("not a diff", ["backend/example.py"])
        with self.assertRaises(ValueError):
            validate_unified_diff("x" * 16001, ["backend/example.py"])

    def test_prompt_marks_repository_content_untrusted_and_never_executes(self):
        prompt = build_patch_proposal_prompt(
            "Corrigir o comportamento da função e preservar compatibilidade.",
            [{"path": "backend/example.py", "sha": "abc", "content": "def f(): pass"}],
        )
        self.assertIn("DADOS NÃO CONFIÁVEIS", prompt)
        self.assertIn("nunca execute comandos", prompt)
        self.assertIn("unified diff", prompt)

    def test_prompt_rejects_invalid_source_budget(self):
        with self.assertRaises(ValueError):
            build_patch_proposal_prompt(
                "Objetivo técnico suficientemente longo para a validação.",
                [{"path": "backend/large.py", "content": "x" * 24001}],
            )


if __name__ == "__main__":
    unittest.main()
