import base64
import os
import unittest
from unittest.mock import AsyncMock, patch

from backend.github_app import (
    GitHubAppConfig, GitHubAppReadOnlyClient, GitHubIntegrationError,
    validate_repository_path,
)

class GitHubAppConfigurationTests(unittest.TestCase):
    def test_missing_configuration_is_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(GitHubAppReadOnlyClient().configured)

    def test_configuration_requires_all_values_and_valid_identifiers(self):
        env = {
            "GITHUB_APP_ID": "12345", "GITHUB_APP_PRIVATE_KEY": "private-key",
            "GITHUB_INSTALLATION_ID": "67890", "GITHUB_REPOSITORY": "owner/repository",
        }
        with patch.dict(os.environ, env, clear=True):
            config = GitHubAppConfig.from_env()
        self.assertEqual(config.repository, "owner/repository")
        env["GITHUB_REPOSITORY"] = "https://github.com/owner/repository"
        with patch.dict(os.environ, env, clear=True):
            self.assertIsNone(GitHubAppConfig.from_env())

    def test_path_allowlist_rejects_traversal_and_secrets(self):
        self.assertEqual(validate_repository_path("backend/storage.py"), "backend/storage.py")
        self.assertEqual(validate_repository_path("tests/test_example.py"), "tests/test_example.py")
        for path in ("../.env", "/etc/passwd", "backend/.env.production",
                     "backend/private.key", "data/db.sqlite", "random.txt"):
            with self.subTest(path=path), self.assertRaises(GitHubIntegrationError):
                validate_repository_path(path)

class GitHubAppReadOnlyClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_file_returns_utf8_content_with_size_limit(self):
        config = GitHubAppConfig("123", "unused", "456", "owner/repo")
        client = GitHubAppReadOnlyClient(config=config)
        payload = b"print('safe')\n"
        with patch.object(client, "_get", new=AsyncMock(return_value={
            "type": "file", "size": len(payload), "encoding": "base64",
            "content": base64.b64encode(payload).decode("ascii"), "name": "sample.py",
            "sha": "abc123", "html_url": "https://github.com/owner/repo/blob/main/backend/sample.py",
        })):
            result = await client.read_file("backend/sample.py")
        self.assertEqual(result["content"], "print('safe')\n")
        self.assertEqual(result["size"], len(payload))

    async def test_read_file_rejects_oversized_file(self):
        client = GitHubAppReadOnlyClient(config=GitHubAppConfig("123", "unused", "456", "owner/repo"))
        with patch.object(client, "_get", new=AsyncMock(return_value={
            "type": "file", "size": 200000, "encoding": "base64", "content": "eA==",
        })):
            with self.assertRaises(GitHubIntegrationError):
                await client.read_file("backend/sample.py")

    async def test_read_file_rejects_non_file_content(self):
        client = GitHubAppReadOnlyClient(config=GitHubAppConfig("123", "unused", "456", "owner/repo"))
        with patch.object(client, "_get", new=AsyncMock(return_value={"type": "dir"})):
            with self.assertRaises(GitHubIntegrationError):
                await client.read_file("backend")

if __name__ == "__main__":
    unittest.main()
