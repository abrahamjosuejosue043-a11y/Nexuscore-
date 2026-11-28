"""Tests for signed 48-hour administrative sessions."""

import os
import unittest
from unittest.mock import patch

import main


class AdminSessionTests(unittest.TestCase):
    def test_session_is_valid_until_its_48_hour_expiry(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": "unit-test-admin-secret"}):
            token, expires_at = main.create_admin_session_token(now=1_000)
            self.assertEqual(expires_at, 1_000 + 48 * 60 * 60)
            self.assertEqual(main.admin_session_expiry(token, now=1_001), expires_at)
            self.assertIsNone(main.admin_session_expiry(token, now=expires_at))

    def test_tampered_session_is_rejected(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": "unit-test-admin-secret"}):
            token, _ = main.create_admin_session_token(now=1_000)
            tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
            self.assertIsNone(main.admin_session_expiry(tampered, now=1_001))

    def test_session_is_invalidated_when_admin_secret_changes(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": "first-secret"}):
            token, _ = main.create_admin_session_token(now=1_000)
        with patch.dict(os.environ, {"ADMIN_TOKEN": "second-secret"}):
            self.assertIsNone(main.admin_session_expiry(token, now=1_001))

    def test_session_requires_configured_admin_secret(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": ""}):
            self.assertIsNone(main.admin_session_expiry("123.nonce.signature", now=1_001))


if __name__ == "__main__":
    unittest.main()
