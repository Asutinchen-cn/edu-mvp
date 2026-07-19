from pathlib import Path
import re
import unittest


NGINX_CONFIG = (Path(__file__).parents[1] / "nginx" / "nginx.conf").read_text(encoding="utf-8")


class NginxUploadAndPrivacyContractTest(unittest.TestCase):
    def test_gateway_accepts_backend_upload_limit_plus_multipart_overhead(self):
        self.assertRegex(NGINX_CONFIG, r"client_max_body_size\s+52m;")
        self.assertRegex(NGINX_CONFIG, r"client_body_timeout\s+120s;")
        self.assertIn("upload-batch", NGINX_CONFIG)

    def test_oversized_upload_returns_a_json_error(self):
        self.assertIn("error_page 413 = @payload_too_large;", NGINX_CONFIG)
        self.assertRegex(
            NGINX_CONFIG,
            r"location @payload_too_large\s*\{[^}]*default_type application/json;"
            r"[^}]*return 413 '\{\"success\":false,\"error\":\"多页试卷总大小不能超过50MB\"\}';",
        )

    def test_parent_data_pages_send_basic_privacy_headers(self):
        expected_headers = (
            'add_header X-Content-Type-Options "nosniff" always;',
            'add_header X-Frame-Options "DENY" always;',
            'add_header Referrer-Policy "no-referrer" always;',
            'add_header Permissions-Policy "microphone=(), geolocation=(), payment=()" always;',
        )
        for header in expected_headers:
            self.assertIn(header, NGINX_CONFIG)
        self.assertIn("server_tokens off;", NGINX_CONFIG)


if __name__ == "__main__":
    unittest.main()
