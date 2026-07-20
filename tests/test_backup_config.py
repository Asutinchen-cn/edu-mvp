from pathlib import Path
import stat
import unittest


PROJECT_ROOT = Path(__file__).parents[1]


class WrongBankBackupContractTest(unittest.TestCase):
    def test_backup_assets_exist_and_script_is_executable(self):
        script = PROJECT_ROOT / "deploy" / "backup-edu-data.sh"
        service = PROJECT_ROOT / "deploy" / "edu-data-backup.service"
        timer = PROJECT_ROOT / "deploy" / "edu-data-backup.timer"

        for path in (script, service, timer):
            self.assertTrue(path.exists(), f"missing deployment asset: {path.name}")

        self.assertTrue(script.stat().st_mode & stat.S_IXUSR)

    def test_backup_is_private_complete_and_self_checked(self):
        script = (PROJECT_ROOT / "deploy" / "backup-edu-data.sh").read_text(encoding="utf-8")

        self.assertIn("umask 077", script)
        self.assertIn('RETENTION_DAYS="${RETENTION_DAYS:-7}"', script)
        self.assertIn("docker exec -i edu-api python", script)
        self.assertIn("source_db.backup(target_db)", script)
        self.assertIn('PRAGMA quick_check', script)
        self.assertIn('tar -cf "$STAGING_DIR/uploads.tar"', script)
        self.assertIn('sha256sum exam.db uploads.tar > SHA256SUMS', script)
        self.assertIn('-name "20??????T??????Z"', script)
        self.assertNotIn('-name "20????????T??????Z"', script)
        self.assertIn('-mtime +"$RETENTION_DAYS"', script)

    def test_systemd_runs_a_persistent_daily_backup(self):
        service = (PROJECT_ROOT / "deploy" / "edu-data-backup.service").read_text(encoding="utf-8")
        timer = (PROJECT_ROOT / "deploy" / "edu-data-backup.timer").read_text(encoding="utf-8")

        self.assertIn("Requires=docker.service", service)
        self.assertIn("ExecStart=/opt/edu-mvp/deploy/backup-edu-data.sh", service)
        self.assertIn("OnCalendar=*-*-* 02:30:00", timer)
        self.assertIn("RandomizedDelaySec=30m", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("WantedBy=timers.target", timer)

    def test_backup_directory_is_not_publicly_mounted(self):
        compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        nginx = (PROJECT_ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")

        self.assertNotIn("data/backups:/usr/share/nginx", compose)
        self.assertNotIn("/data/backups", nginx)


if __name__ == "__main__":
    unittest.main()
