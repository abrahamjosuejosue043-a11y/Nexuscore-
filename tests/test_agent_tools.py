import os
import unittest
from unittest.mock import patch

from backend.agent_tools import agent_tools_status, configured_groq_tools


class GroqAgentToolsTests(unittest.TestCase):
    def test_tools_are_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_groq_tools(), [])

    def test_only_explicitly_allowed_tools_are_returned(self):
        result = configured_groq_tools(
            raw="browser_search,code_interpreter,unknown_tool,browser_search"
        )
        self.assertEqual(
            result,
            [{"type": "browser_search"}, {"type": "code_interpreter"}],
        )

    def test_tools_are_not_sent_to_incompatible_models(self):
        self.assertEqual(
            configured_groq_tools(
                raw="browser_search,code_interpreter",
                model="qwen/qwen3.8-27b",
            ),
            [],
        )

    def test_status_does_not_expose_configuration_secrets(self):
        status = agent_tools_status(
            raw="browser_search",
            model="openai/gpt-oss-120b",
        )
        self.assertEqual(status["ferramentas_ativas"], ["browser_search"])
        self.assertTrue(status["disponivel"])
        self.assertNotIn("key", str(status).lower())
        self.assertNotIn("password", str(status).lower())


if __name__ == "__main__":
    unittest.main()
