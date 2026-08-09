from pathlib import Path
import re
import unittest


NGINX_CONFIG = (Path(__file__).parents[1] / "nginx" / "nginx.conf").read_text(encoding="utf-8")
PROJECT_ROOT = Path(__file__).parents[1]
COMPOSE_CONFIG = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")


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

    def test_gateway_compresses_frontend_and_json_responses(self):
        fallback = (PROJECT_ROOT / "nginx" / "nginx.http-fallback.conf").read_text(
            encoding="utf-8"
        )
        for config in (NGINX_CONFIG, fallback):
            self.assertIn("gzip on;", config)
            self.assertIn("gzip_vary on;", config)
            self.assertIn("gzip_proxied any;", config)
            self.assertRegex(config, r"gzip_min_length\s+1024;")
            self.assertRegex(config, r"gzip_types[^;]*application/json")
            self.assertRegex(config, r"gzip_types[^;]*application/javascript")

    def test_app_shell_and_curriculum_catalog_do_not_stay_stale(self):
        fallback = (PROJECT_ROOT / "nginx" / "nginx.http-fallback.conf").read_text(
            encoding="utf-8"
        )
        for config in (NGINX_CONFIG, fallback):
            self.assertRegex(
                config,
                r"map \$uri \$edu_cache_control\s*\{[^}]*"
                r'/index\.html\s+"no-cache, must-revalidate";',
            )
            self.assertRegex(
                config,
                r"map \$uri \$edu_cache_control\s*\{[^}]*"
                r'\^/curriculum-units.*"no-store";',
            )
            self.assertIn(
                "add_header Cache-Control $edu_cache_control always;",
                config,
            )

    def test_old_index_backups_redirect_to_the_current_app(self):
        fallback = (PROJECT_ROOT / "nginx" / "nginx.http-fallback.conf").read_text(
            encoding="utf-8"
        )
        redirect_rule = r"location ~ ^/index\.html\.(?:bak|backup)(?:-|$)"
        for config in (NGINX_CONFIG, fallback):
            self.assertIn(redirect_rule, config)
            self.assertIn("return 302 /;", config)

    def test_private_and_generated_learning_data_is_never_cached(self):
        fallback = (PROJECT_ROOT / "nginx" / "nginx.http-fallback.conf").read_text(
            encoding="utf-8"
        )
        no_store_rule = (
            '~^/(upload|upload-batch|analyze|exams|wrong-questions|generate-practice|'
            'generate-knowledge-practice|generate-unit-worksheet|export-practice-pdf|'
            'family-review-report|api-info)(?:/|$) "no-store";'
        )
        for config in (NGINX_CONFIG, fallback):
            self.assertIn(no_store_rule, config)
            self.assertIn(
                "add_header Cache-Control $edu_cache_control always;",
                config,
            )

    def test_public_ip_uses_trusted_https_and_redirects_plain_http(self):
        self.assertIn("listen 443 ssl;", NGINX_CONFIG)
        self.assertIn("return 308 https://$host$request_uri;", NGINX_CONFIG)
        self.assertIn("location ^~ /.well-known/acme-challenge/", NGINX_CONFIG)
        self.assertIn(
            "ssl_certificate /etc/letsencrypt/live/43.128.141.25/fullchain.pem;",
            NGINX_CONFIG,
        )
        self.assertIn(
            "ssl_certificate_key /etc/letsencrypt/live/43.128.141.25/privkey.pem;",
            NGINX_CONFIG,
        )
        self.assertIn('add_header Strict-Transport-Security "max-age=31536000" always;', NGINX_CONFIG)
        self.assertIn('- "443:443"', COMPOSE_CONFIG)
        self.assertIn('./certbot/conf:/etc/letsencrypt:ro', COMPOSE_CONFIG)

    def test_expensive_and_private_endpoints_are_rate_limited_with_json_errors(self):
        self.assertRegex(NGINX_CONFIG, r"limit_req_zone\s+\$binary_remote_addr\s+zone=edu_ai:")
        self.assertRegex(NGINX_CONFIG, r"limit_req_zone\s+\$binary_remote_addr\s+zone=edu_private:")
        self.assertIn("limit_req zone=edu_ai", NGINX_CONFIG)
        self.assertIn("limit_req zone=edu_private", NGINX_CONFIG)
        self.assertIn("error_page 429 = @too_many_requests;", NGINX_CONFIG)
        self.assertIn('return 429 \'{"success":false,"error":"请求过于频繁，请稍后再试"}\';', NGINX_CONFIG)

    def test_short_lived_ip_certificate_has_automatic_renewal_assets(self):
        renew_script = PROJECT_ROOT / "deploy" / "renew-ip-certificate.sh"
        service_file = PROJECT_ROOT / "deploy" / "edu-certbot-renew.service"
        timer_file = PROJECT_ROOT / "deploy" / "edu-certbot-renew.timer"
        for path in (renew_script, service_file, timer_file):
            self.assertTrue(path.exists(), f"missing deployment asset: {path.name}")

        script = renew_script.read_text(encoding="utf-8")
        service = service_file.read_text(encoding="utf-8")
        timer = timer_file.read_text(encoding="utf-8")
        self.assertIn("--preferred-profile shortlived", script)
        self.assertIn("--ip-address 43.128.141.25", script)
        self.assertIn("docker exec edu-web nginx -s reload", script)
        self.assertIn("/opt/edu-mvp/deploy/renew-ip-certificate.sh", service)
        self.assertIn("OnCalendar=*-*-* 03,15:00:00", timer)

    def test_http_fallback_keeps_security_controls_while_port_443_is_closed(self):
        fallback_path = PROJECT_ROOT / "nginx" / "nginx.http-fallback.conf"
        self.assertTrue(fallback_path.exists(), "missing HTTP fallback gateway")
        fallback = fallback_path.read_text(encoding="utf-8")
        self.assertIn("listen 80;", fallback)
        self.assertNotIn("return 308 https://$host$request_uri;", fallback)
        self.assertIn("location ^~ /.well-known/acme-challenge/", fallback)
        self.assertIn("limit_req zone=edu_ai", fallback)
        self.assertIn("limit_req zone=edu_private", fallback)
        self.assertIn("Content-Security-Policy", fallback)
        self.assertNotIn("Strict-Transport-Security", fallback)


if __name__ == "__main__":
    unittest.main()
