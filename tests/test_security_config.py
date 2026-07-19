import os
import unittest
from unittest.mock import patch

from api.main import _configured_cors_origins


class CorsSecurityConfigTest(unittest.TestCase):
    def test_defaults_allow_local_development_without_opening_every_origin(self):
        with patch.dict(os.environ, {}, clear=True):
            origins = _configured_cors_origins()

        self.assertIn("http://127.0.0.1:8013", origins)
        self.assertIn("http://localhost:8013", origins)
        self.assertNotIn("*", origins)

    def test_deployment_origins_are_explicit_and_trimmed(self):
        with patch.dict(
            os.environ,
            {"ALLOWED_ORIGINS": "https://43.128.141.25, https://study.example.com "},
            clear=True,
        ):
            self.assertEqual(
                _configured_cors_origins(),
                ["https://43.128.141.25", "https://study.example.com"],
            )

    def test_wildcard_origin_is_rejected(self):
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"}, clear=True):
            with self.assertRaisesRegex(ValueError, "不能使用通配符"):
                _configured_cors_origins()


if __name__ == "__main__":
    unittest.main()
