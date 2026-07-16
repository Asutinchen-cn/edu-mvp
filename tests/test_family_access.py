import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import (
    Base,
    Exam,
    ReviewProgressRequest,
    app,
    _exam_has_family_access,
    _hash_family_access_code,
    _validate_family_access_code,
    _verify_family_access_code,
    analyze_exam,
    delete_exam,
    export_correction_sheet,
    export_family_review_report,
    export_practice_pdf,
    generate_practice,
    get_exam,
    get_exam_image,
    list_exams,
    update_review_progress,
    upload_exam,
)


class FamilyAccessCodeTest(unittest.TestCase):
    def test_accepts_parent_friendly_alphanumeric_codes(self):
        self.assertEqual(_validate_family_access_code("Home2026A"), "Home2026A")

    def test_rejects_short_or_non_alphanumeric_codes(self):
        for value in ("1234567", "family code", "家庭访问码", "abc-12345"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _validate_family_access_code(value)

    def test_hashes_with_unique_salts_and_verifies_without_plaintext_storage(self):
        salt_a, digest_a = _hash_family_access_code("Home2026A")
        salt_b, digest_b = _hash_family_access_code("Home2026A")

        self.assertNotEqual(salt_a, salt_b)
        self.assertNotEqual(digest_a, digest_b)
        self.assertNotIn("Home2026A", salt_a + digest_a)
        self.assertTrue(_verify_family_access_code("Home2026A", salt_a, digest_a))
        self.assertFalse(_verify_family_access_code("Wrong2026", salt_a, digest_a))

    def test_legacy_record_without_hash_cannot_be_claimed_by_name(self):
        legacy_exam = Exam(grade="六年级", student_name="小明")

        self.assertFalse(
            _exam_has_family_access(legacy_exam, "六年级", "小明", "Home2026A")
        )


class FamilyAccessEndpointTest(unittest.TestCase):
    def setUp(self):
        self.upload_dir = tempfile.TemporaryDirectory()
        self.upload_patch = patch("api.main.UPLOAD_DIR", self.upload_dir.name)
        self.upload_patch.start()
        (Path(self.upload_dir.name) / "protected.png").write_bytes(b"private-image")
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        db = self.session_factory()
        salt_a, digest_a = _hash_family_access_code("Home2026A")
        salt_b, digest_b = _hash_family_access_code("Other2026B")
        db.add_all([
            Exam(
                grade="六年级",
                subject="math",
                student_name="小明",
                access_code_salt=salt_a,
                access_code_hash=digest_a,
                image_path="/uploads/protected.png",
                ocr_text="第一份试卷",
                ai_analysis=json.dumps({
                    "wrong_questions": [{
                        "question": "解方程 2x + 3 = 9",
                        "error_type": "移项符号错误",
                        "student_answer": "x = 6",
                        "correct_answer": "x = 3",
                    }],
                    "weak_points": ["一元一次方程"],
                    "root_cause": "没有理解移项要改变符号。",
                    "recommendations": ["先口述等式两边同时运算的理由。"],
                }, ensure_ascii=False),
            ),
            Exam(
                grade="六年级",
                subject="english",
                student_name="小明",
                access_code_salt=salt_b,
                access_code_hash=digest_b,
                ocr_text="第二份试卷",
            ),
        ])
        db.commit()
        self.first_exam_id = db.query(Exam).filter(Exam.subject == "math").one().id
        db.close()
        self.session_patch = patch("api.main.SessionLocal", self.session_factory)
        self.session_patch.start()

    def tearDown(self):
        self.session_patch.stop()
        self.upload_patch.stop()
        self.upload_dir.cleanup()
        self.engine.dispose()

    def test_list_returns_only_records_for_the_matching_family_code(self):
        response = asyncio.run(list_exams(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
            limit=50,
        ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["subject"] for item in payload["exams"]], ["math"])
        self.assertEqual(payload["subject_archive"], {"all": 1, "math": 1, "english": 0})
        self.assertTrue(payload["exams"][0]["image_available"])
        self.assertNotIn("image_url", payload["exams"][0])

    def test_detail_rejects_a_wrong_or_missing_family_code(self):
        wrong = asyncio.run(get_exam(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            family_code="Other2026B",
        ))
        missing = asyncio.run(get_exam(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            family_code=None,
        ))

        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(missing.status_code, 400)

    def test_protected_image_is_returned_for_the_matching_family_code(self):
        response = asyncio.run(get_exam_image(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Path(response.path).name, "protected.png")

    def test_correction_sheet_is_returned_for_the_matching_family_code(self):
        response = asyncio.run(export_correction_sheet(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("attachment", response.headers["content-disposition"])

    def test_correction_sheet_requires_saved_wrong_question_evidence(self):
        db = self.session_factory()
        english_exam_id = db.query(Exam).filter(Exam.subject == "english").one().id
        db.close()

        response = asyncio.run(export_correction_sheet(
            english_exam_id,
            grade="六年级",
            student_name="小明",
            family_code="Other2026B",
        ))

        self.assertEqual(response.status_code, 400)
        self.assertIn("没有可导出的错题", json.loads(response.body)["error"])

    def test_family_review_report_is_returned_for_the_matching_code(self):
        response = asyncio.run(export_family_review_report(
            grade="六年级",
            student_name="小明",
            subject="math",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("attachment", response.headers["content-disposition"])

    def test_every_record_operation_rejects_the_wrong_family_code(self):
        calls = [
            lambda: analyze_exam(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: generate_practice(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: export_practice_pdf(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: export_correction_sheet(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: export_family_review_report(
                "六年级", "小明", subject="math", family_code="Other2026B"
            ),
            lambda: get_exam_image(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: update_review_progress(
                self.first_exam_id,
                ReviewProgressRequest(completed=["corrected"]),
                "六年级",
                "小明",
                family_code="Other2026B",
            ),
            lambda: delete_exam(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
        ]

        for call in calls:
            with self.subTest(call=call):
                response = asyncio.run(call())
                self.assertEqual(response.status_code, 403)

    def test_upload_requires_a_family_code_before_processing_the_file(self):
        response = asyncio.run(upload_exam(
            student_name="小明",
            grade="六年级",
            subject="math",
            file=None,
            family_code=None,
        ))

        self.assertEqual(response.status_code, 400)

    def test_upload_directory_is_not_publicly_mounted(self):
        mounted_paths = [getattr(route, "path", None) for route in app.routes]

        self.assertNotIn("/uploads", mounted_paths)

    def test_reverse_proxy_does_not_publish_upload_directory(self):
        project_root = Path(__file__).parents[1]
        nginx_config = (project_root / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        compose_config = (project_root / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertNotIn("location /uploads", nginx_config)
        self.assertEqual(compose_config.count("./uploads:/uploads"), 1)


if __name__ == "__main__":
    unittest.main()
