import asyncio
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import (
    AnalysisServiceUnavailable,
    Base,
    Exam,
    ReviewProgressRequest,
    WrongQuestionMasteryRequest,
    app,
    _detect_ocr_subject,
    _exam_has_family_access,
    _hash_family_access_code,
    _normalize_wrong_question_mastery,
    _normalize_wrong_question_mastery_times,
    _validate_family_access_code,
    _verify_family_access_code,
    ai_analyze,
    analyze_exam,
    delete_exam,
    export_correction_sheet,
    export_family_review_report,
    export_practice_pdf,
    generate_knowledge_practice,
    generate_practice,
    get_exam,
    get_exam_image,
    list_wrong_questions,
    list_exams,
    serve_logo,
    update_knowledge_point_mastery,
    update_review_progress,
    update_wrong_question_mastery,
    upload_exam,
    upload_exam_batch,
)


class FamilyAccessCodeTest(unittest.TestCase):
    def test_detects_only_clear_english_or_math_ocr_subjects(self):
        english_text = """
        Read the passage and choose the best answer.
        Tom usually walks to school, but yesterday he went by bus because it was raining.
        What did Tom do yesterday? Write a complete sentence and check your grammar.
        """
        math_text = """
        一、选择题。计算下列各题，并写出必要步骤。
        1. 解方程 3x+5=20。2. 求三角形的面积。3. 化简代数式并判断正负。
        """

        self.assertEqual(_detect_ocr_subject(english_text), "english")
        self.assertEqual(_detect_ocr_subject(math_text), "math")
        self.assertIsNone(_detect_ocr_subject("第一页文字 期中练习"))

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

    def test_ai_provider_errors_are_retryable_instead_of_fake_diagnoses(self):
        with patch(
            "api.main.call_deepseek",
            new=AsyncMock(side_effect=RuntimeError("provider timeout")),
        ):
            with self.assertRaises(AnalysisServiceUnavailable):
                asyncio.run(ai_analyze("第1题批改错误", "math", "六年级"))


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
                        "knowledge_point": "一元一次方程",
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
        self.assertEqual(payload["exams"][0]["review_schedule"]["next_step"], "corrected")
        self.assertEqual(payload["exams"][0]["question_mastery"], {
            "total": 1,
            "mastered": 0,
            "pending": 1,
        })

    def test_wrong_question_bank_flattens_and_groups_accessible_questions(self):
        response = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
            limit=50,
        ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["question_count"], 1)
        self.assertEqual(payload["subject_archive"], {"all": 1, "math": 1, "english": 0})
        self.assertEqual(payload["knowledge_points"], [{
            "name": "一元一次方程",
            "subject": "math",
            "wrong_count": 1,
            "latest_created": payload["questions"][0]["created"],
        }])
        self.assertEqual(payload["questions"][0]["id"], f"{self.first_exam_id}-1")
        self.assertEqual(payload["questions"][0]["exam_id"], self.first_exam_id)
        self.assertEqual(payload["questions"][0]["question_number"], 1)
        self.assertEqual(payload["questions"][0]["knowledge_point"], "一元一次方程")
        self.assertFalse(payload["questions"][0]["mastered"])
        self.assertEqual(payload["questions"][0]["review_schedule"]["next_step"], "corrected")

    def test_each_wrong_question_can_be_marked_mastered_independently(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        analysis = json.loads(exam.ai_analysis)
        analysis["wrong_questions"].append({
            "question": "解方程 5x - 2 = 13",
            "error_type": "计算错误",
            "student_answer": "x = 5",
            "correct_answer": "x = 3",
            "knowledge_point": "一元一次方程",
        })
        exam.ai_analysis = json.dumps(analysis, ensure_ascii=False)
        db.commit()
        db.close()

        mastered = asyncio.run(update_wrong_question_mastery(
            self.first_exam_id,
            1,
            WrongQuestionMasteryRequest(mastered=True),
            "六年级",
            "小明",
            family_code="Home2026A",
        ))
        listed = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))
        exam_list = asyncio.run(list_exams(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))
        exam_detail = asyncio.run(get_exam(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(mastered.status_code, 200)
        self.assertTrue(json.loads(mastered.body)["mastered"])
        self.assertEqual(
            [item["mastered"] for item in json.loads(listed.body)["questions"]],
            [True, False],
        )
        self.assertEqual(json.loads(exam_list.body)["exams"][0]["question_mastery"], {
            "total": 2,
            "mastered": 1,
            "pending": 1,
        })
        self.assertEqual(json.loads(exam_detail.body)["question_mastery"], {
            "total": 2,
            "mastered": 1,
            "pending": 1,
        })

        pending = asyncio.run(update_wrong_question_mastery(
            self.first_exam_id,
            1,
            WrongQuestionMasteryRequest(mastered=False),
            "六年级",
            "小明",
            family_code="Home2026A",
        ))
        relisted = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(pending.status_code, 200)
        self.assertFalse(json.loads(pending.body)["mastered"])
        self.assertFalse(json.loads(relisted.body)["questions"][0]["mastered"])

    def test_mastery_time_is_saved_only_for_a_real_pending_to_mastered_transition(self):
        mastered_at = datetime(2026, 8, 13, 12, 30, tzinfo=timezone.utc)
        with patch("api.main._utc_now", return_value=mastered_at):
            mastered = asyncio.run(update_wrong_question_mastery(
                self.first_exam_id,
                1,
                WrongQuestionMasteryRequest(mastered=True),
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
        first_payload = json.loads(mastered.body)

        with patch("api.main._utc_now", return_value=datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)):
            repeated = asyncio.run(update_wrong_question_mastery(
                self.first_exam_id,
                1,
                WrongQuestionMasteryRequest(mastered=True),
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
        repeated_payload = json.loads(repeated.body)
        listed = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(first_payload["mastered_at"], "2026-08-13T12:30:00Z")
        self.assertEqual(repeated_payload["mastered_at"], "2026-08-13T12:30:00Z")
        self.assertEqual(
            json.loads(listed.body)["questions"][0]["mastered_at"],
            "2026-08-13T12:30:00Z",
        )

        pending = asyncio.run(update_wrong_question_mastery(
            self.first_exam_id,
            1,
            WrongQuestionMasteryRequest(mastered=False),
            "六年级",
            "小明",
            family_code="Home2026A",
        ))
        relisted = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertIsNone(json.loads(pending.body)["mastered_at"])
        self.assertIsNone(json.loads(relisted.body)["questions"][0]["mastered_at"])

    def test_legacy_boolean_mastery_remains_compatible_with_timestamp_metadata(self):
        raw = {
            "1": True,
            "2": False,
            "_mastered_at": {
                "1": "2026-08-13T12:30:00Z",
                "2": "2026-08-13T12:31:00Z",
                "bad": "not-a-date",
            },
        }

        self.assertEqual(_normalize_wrong_question_mastery(raw), {"1": True, "2": False})
        self.assertEqual(
            _normalize_wrong_question_mastery_times(raw),
            {"1": "2026-08-13T12:30:00Z"},
        )

    def test_knowledge_point_mastery_updates_only_matching_accessible_questions(self):
        db = self.session_factory()
        first_exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        second_exam = Exam(
            grade="六年级",
            subject="math",
            student_name="小明",
            access_code_salt=first_exam.access_code_salt,
            access_code_hash=first_exam.access_code_hash,
            ai_analysis=json.dumps({
                "wrong_questions": [{
                    "question": "解方程 5x - 2 = 13",
                    "error_type": "计算错误",
                    "student_answer": "x = 5",
                    "correct_answer": "x = 3",
                    "knowledge_point": "一元一次方程",
                }, {
                    "question": "计算 (-2) + 5",
                    "error_type": "符号错误",
                    "student_answer": "-7",
                    "correct_answer": "3",
                    "knowledge_point": "有理数加法",
                }],
                "weak_points": ["一元一次方程", "有理数加法"],
            }, ensure_ascii=False),
        )
        db.add(second_exam)
        db.commit()
        second_exam_id = second_exam.id
        db.close()

        with patch(
            "api.main._utc_now",
            return_value=datetime(2026, 8, 13, 12, 30, tzinfo=timezone.utc),
        ):
            response = asyncio.run(update_knowledge_point_mastery(
                WrongQuestionMasteryRequest(mastered=True),
                grade="六年级",
                student_name="小明",
                subject="math",
                knowledge_point="一元一次方程",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["matched_count"], 2)
        self.assertEqual(payload["updated_count"], 2)
        self.assertEqual(payload["source_exam_ids"], [second_exam_id, self.first_exam_id])
        db = self.session_factory()
        first_mastery = json.loads(db.query(Exam).filter(Exam.id == self.first_exam_id).one().wrong_question_mastery)
        second_mastery = json.loads(db.query(Exam).filter(Exam.id == second_exam_id).one().wrong_question_mastery)
        db.close()
        expected_mastery = {
            "1": True,
            "_mastered_at": {"1": "2026-08-13T12:30:00Z"},
        }
        self.assertEqual(first_mastery, expected_mastery)
        self.assertEqual(second_mastery, expected_mastery)
        self.assertEqual(payload["question_updates"], [
            {
                "exam_id": second_exam_id,
                "question_number": 1,
                "mastered_at": "2026-08-13T12:30:00Z",
            },
            {
                "exam_id": self.first_exam_id,
                "question_number": 1,
                "mastered_at": "2026-08-13T12:30:00Z",
            },
        ])

        with patch(
            "api.main._utc_now",
            return_value=datetime(2026, 8, 14, 12, 30, tzinfo=timezone.utc),
        ):
            repeated = asyncio.run(update_knowledge_point_mastery(
                WrongQuestionMasteryRequest(mastered=True),
                grade="六年级",
                student_name="小明",
                subject="math",
                knowledge_point="一元一次方程",
                family_code="Home2026A",
            ))
        repeated_payload = json.loads(repeated.body)

        self.assertEqual(repeated_payload["updated_count"], 0)
        self.assertTrue(all(
            item["mastered_at"] == "2026-08-13T12:30:00Z"
            for item in repeated_payload["question_updates"]
        ))

    def test_knowledge_point_mastery_rejects_wrong_code_and_unknown_point(self):
        wrong_code = asyncio.run(update_knowledge_point_mastery(
            WrongQuestionMasteryRequest(mastered=True),
            grade="六年级",
            student_name="小明",
            subject="math",
            knowledge_point="一元一次方程",
            family_code="Other2026B",
        ))
        unknown_point = asyncio.run(update_knowledge_point_mastery(
            WrongQuestionMasteryRequest(mastered=True),
            grade="六年级",
            student_name="小明",
            subject="math",
            knowledge_point="几何证明",
            family_code="Home2026A",
        ))

        self.assertEqual(wrong_code.status_code, 403)
        self.assertEqual(unknown_point.status_code, 400)
        self.assertIn("知识点", json.loads(unknown_point.body)["error"])

    def test_wrong_question_mastery_rejects_unknown_question_number(self):
        response = asyncio.run(update_wrong_question_mastery(
            self.first_exam_id,
            9,
            WrongQuestionMasteryRequest(mastered=True),
            "六年级",
            "小明",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 404)
        self.assertIn("错题不存在", json.loads(response.body)["error"])

    def test_wrong_question_bank_rejects_a_wrong_family_code(self):
        response = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Wrong2026",
        ))

        self.assertEqual(response.status_code, 403)

    def test_wrong_question_bank_uses_saved_weak_point_for_legacy_questions(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        analysis = json.loads(exam.ai_analysis)
        analysis["wrong_questions"][0].pop("knowledge_point")
        exam.ai_analysis = json.dumps(analysis, ensure_ascii=False)
        db.commit()
        db.close()

        response = asyncio.run(list_wrong_questions(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))
        payload = json.loads(response.body)

        self.assertEqual(payload["questions"][0]["knowledge_point"], "一元一次方程")

    def test_practice_can_target_a_confirmed_knowledge_point(self):
        generated_questions = [{
            "id": 1,
            "type": "填空题",
            "question": "3x + 4 = 16，x = ___。",
            "answer": "4",
            "hint": "等式两边先同时减去 4。",
        }]
        generator = AsyncMock(return_value=generated_questions)

        with (
            patch("api.main.ai_generate_questions", generator),
            patch("api.main.generate_practice_pdf", return_value=b"%PDF-same-practice") as render_pdf,
        ):
            response = asyncio.run(generate_practice(
                self.first_exam_id,
                "六年级",
                "小明",
                knowledge_point="一元一次方程",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["weak_points"], ["一元一次方程"])
        self.assertEqual(payload["practice_mode"], "knowledge_point")
        self.assertEqual(payload["questions"], generated_questions)
        self.assertEqual(payload["practice_pdf"]["filename"], "六年级数学-错题巩固练习.pdf")
        self.assertEqual(
            base64.b64decode(payload["practice_pdf"]["data_url"].split(",", 1)[1]),
            b"%PDF-same-practice",
        )
        render_pdf.assert_called_once_with(
            "小明",
            ["一元一次方程"],
            generated_questions,
            grade="六年级",
            subject="math",
        )
        generator.assert_awaited_once()
        self.assertEqual(generator.await_args.args[0], ["一元一次方程"])
        self.assertEqual(generator.await_args.kwargs["subject"], "math")
        self.assertEqual(generator.await_args.kwargs["grade"], "六年级")
        self.assertEqual(
            generator.await_args.kwargs["wrong_questions"][0]["error_type"],
            "移项符号错误",
        )

    def test_practice_rejects_an_unconfirmed_knowledge_point(self):
        generator = AsyncMock(return_value=[])

        with patch("api.main.ai_generate_questions", generator):
            response = asyncio.run(generate_practice(
                self.first_exam_id,
                "六年级",
                "小明",
                knowledge_point="几何证明",
                family_code="Home2026A",
            ))

        self.assertEqual(response.status_code, 400)
        self.assertIn("不在这份试卷", json.loads(response.body)["error"])
        generator.assert_not_awaited()

    def test_practice_generation_failure_is_retryable_and_has_no_fake_question(self):
        generator = AsyncMock(side_effect=AnalysisServiceUnavailable("provider timeout"))

        with patch("api.main.ai_generate_questions", generator):
            response = asyncio.run(generate_practice(
                self.first_exam_id,
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 503)
        self.assertTrue(payload["retryable"])
        self.assertNotIn("questions", payload)
        self.assertIn("稍后重试", payload["error"])

    def test_knowledge_practice_combines_exams_and_prefers_pending_evidence(self):
        db = self.session_factory()
        first_exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        first_exam.wrong_question_mastery = json.dumps({"1": True})
        second_exam = Exam(
            grade="六年级",
            subject="math",
            student_name="小明",
            access_code_salt=first_exam.access_code_salt,
            access_code_hash=first_exam.access_code_hash,
            ocr_text="第三份试卷",
            ai_analysis=json.dumps({
                "wrong_questions": [{
                    "question": "解方程 5x - 2 = 13",
                    "error_type": "计算错误",
                    "student_answer": "x = 5",
                    "correct_answer": "x = 3",
                    "knowledge_point": "一元一次方程",
                }],
                "weak_points": ["一元一次方程"],
                "root_cause": "合并同类项后计算不稳定。",
                "recommendations": ["每步验算。"],
            }, ensure_ascii=False),
        )
        db.add(second_exam)
        db.commit()
        second_exam_id = second_exam.id
        db.close()
        generated_questions = [{
            "id": 1,
            "type": "填空题",
            "question": "7x - 3 = 18，x = ___。",
            "answer": "3",
            "hint": "先移项。",
        }]
        generator = AsyncMock(return_value=generated_questions)

        with (
            patch("api.main.ai_generate_questions", generator),
            patch("api.main.generate_practice_pdf", return_value=b"%PDF-bank-practice") as render_pdf,
        ):
            response = asyncio.run(generate_knowledge_practice(
                grade="六年级",
                student_name="小明",
                subject="math",
                knowledge_point="一元一次方程",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["practice_mode"], "knowledge_point_bank")
        self.assertEqual(payload["matched_wrong_count"], 2)
        self.assertEqual(payload["pending_wrong_count"], 1)
        self.assertEqual(payload["evidence_count"], 1)
        self.assertEqual(payload["source_exam_ids"], [second_exam_id])
        self.assertEqual(payload["questions"], generated_questions)
        self.assertEqual(payload["practice_pdf"]["filename"], "六年级数学-错题巩固练习.pdf")
        self.assertEqual(
            base64.b64decode(payload["practice_pdf"]["data_url"].split(",", 1)[1]),
            b"%PDF-bank-practice",
        )
        render_pdf.assert_called_once_with(
            "小明",
            ["一元一次方程"],
            generated_questions,
            grade="六年级",
            subject="math",
        )
        generator.assert_awaited_once()
        self.assertEqual(generator.await_args.args[0], ["一元一次方程"])
        self.assertEqual(generator.await_args.kwargs["subject"], "math")
        self.assertEqual(generator.await_args.kwargs["grade"], "六年级")
        self.assertEqual(
            [item["question"] for item in generator.await_args.kwargs["wrong_questions"]],
            ["解方程 5x - 2 = 13"],
        )

    def test_knowledge_practice_rejects_an_unconfirmed_bank_point(self):
        generator = AsyncMock(return_value=[])

        with patch("api.main.ai_generate_questions", generator):
            response = asyncio.run(generate_knowledge_practice(
                grade="六年级",
                student_name="小明",
                subject="math",
                knowledge_point="几何证明",
                family_code="Home2026A",
            ))

        self.assertEqual(response.status_code, 400)
        self.assertIn("家庭错题库", json.loads(response.body)["error"])
        generator.assert_not_awaited()

    def test_knowledge_practice_generation_failure_is_retryable(self):
        generator = AsyncMock(side_effect=AnalysisServiceUnavailable("provider timeout"))

        with patch("api.main.ai_generate_questions", generator):
            response = asyncio.run(generate_knowledge_practice(
                grade="六年级",
                student_name="小明",
                subject="math",
                knowledge_point="一元一次方程",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 503)
        self.assertTrue(payload["retryable"])
        self.assertNotIn("questions", payload)

    def test_practice_pdf_generation_failure_is_retryable(self):
        generator = AsyncMock(side_effect=AnalysisServiceUnavailable("provider timeout"))

        with patch("api.main.ai_generate_questions", generator):
            response = asyncio.run(export_practice_pdf(
                self.first_exam_id,
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 503)
        self.assertTrue(payload["retryable"])
        self.assertEqual(response.headers["retry-after"], "15")

    def test_reanalysis_resets_each_current_wrong_question_to_pending(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.wrong_question_mastery = json.dumps({"1": True})
        saved_analysis = json.loads(exam.ai_analysis)
        db.commit()
        db.close()

        with patch("api.main.ai_analyze", AsyncMock(return_value=saved_analysis)):
            response = asyncio.run(analyze_exam(
                self.first_exam_id,
                "六年级",
                "小明",
                family_code="Home2026A",
            ))

        db = self.session_factory()
        stored_mastery = db.query(Exam).filter(Exam.id == self.first_exam_id).one().wrong_question_mastery
        db.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body)["analysis_status"], "completed")
        self.assertEqual(json.loads(stored_mastery), {"1": False})

    def test_unavailable_ai_keeps_the_uploaded_exam_pending_for_retry(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.ai_analysis = None
        exam.weak_points = None
        exam.recommendations = None
        db.commit()
        db.close()

        with patch(
            "api.main.ai_analyze",
            AsyncMock(side_effect=AnalysisServiceUnavailable("provider timeout")),
        ):
            response = asyncio.run(analyze_exam(
                self.first_exam_id,
                "六年级",
                "小明",
                family_code="Home2026A",
            ))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(payload["retryable"])
        self.assertEqual(payload["analysis_status"], "pending")
        self.assertIn("原卷已保存", payload["error"])
        db = self.session_factory()
        stored = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        self.assertIsNone(stored.ai_analysis)
        self.assertIsNone(stored.weak_points)
        self.assertIsNone(stored.recommendations)
        db.close()

    def test_failed_placeholder_analysis_is_reported_as_pending(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.ai_analysis = json.dumps({
            "wrong_questions": [],
            "weak_points": ["请稍后重试"],
            "root_cause": "AI分析服务异常: timeout",
        }, ensure_ascii=False)
        db.commit()
        db.close()

        response = asyncio.run(list_exams(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["exams"][0]["analysis_status"], "pending")

    def test_legacy_retry_weak_point_is_also_reported_as_pending(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.ai_analysis = None
        exam.weak_points = json.dumps(["请稍后重试"], ensure_ascii=False)
        db.commit()
        db.close()

        response = asyncio.run(list_exams(
            grade="六年级",
            student_name="小明",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body)["exams"][0]["analysis_status"], "pending")

    def test_review_progress_saves_each_step_time_and_enforces_the_retest_day(self):
        with patch("api.main._utc_now", return_value=datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)):
            response = asyncio.run(update_review_progress(
                self.first_exam_id,
                ReviewProgressRequest(completed=["corrected", "practiced"]),
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
            early_retest = asyncio.run(update_review_progress(
                self.first_exam_id,
                ReviewProgressRequest(completed=["corrected", "practiced", "retested"]),
                "六年级",
                "小明",
                family_code="Home2026A",
            ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["review_progress"]["completed"], ["corrected", "practiced"])
        self.assertEqual(
            payload["review_progress"]["completed_at"],
            {
                "corrected": "2026-07-16T06:00:00Z",
                "practiced": "2026-07-16T06:00:00Z",
            },
        )
        self.assertEqual(payload["review_schedule"], {
            "next_step": "retested",
            "due_at": "2026-07-17T06:00:00Z",
            "status": "upcoming",
        })
        self.assertEqual(early_retest.status_code, 409)
        self.assertIn("隔天回测", json.loads(early_retest.body)["error"])

        with patch("api.main._utc_now", return_value=datetime(2026, 7, 17, 1, 0, tzinfo=timezone.utc)):
            on_time_retest = asyncio.run(update_review_progress(
                self.first_exam_id,
                ReviewProgressRequest(completed=["corrected", "practiced", "retested"]),
                "六年级",
                "小明",
                family_code="Home2026A",
            ))

        self.assertEqual(on_time_retest.status_code, 200)
        self.assertEqual(
            json.loads(on_time_retest.body)["review_progress"]["completed_count"],
            3,
        )

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

    def test_family_review_report_uses_question_mastery_even_when_exam_progress_is_pending(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.review_progress = json.dumps({"completed": []})
        exam.wrong_question_mastery = json.dumps({"1": True})
        db.commit()
        db.close()

        with patch("api.main.generate_family_review_report_pdf", return_value=b"%PDF-test") as render_pdf:
            response = asyncio.run(export_family_review_report(
                grade="六年级",
                student_name="小明",
                subject="math",
                family_code="Home2026A",
            ))

        self.assertEqual(response.status_code, 200)
        records = render_pdf.call_args.kwargs["records"]
        self.assertEqual(records[0]["review_progress"]["completed_count"], 0)
        self.assertEqual(records[0]["wrong_questions"], [{
            "knowledge_point": "一元一次方程",
            "mastered": True,
        }])

    def test_family_review_report_uses_the_shanghai_calendar_window_boundary(self):
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.created_at = datetime(2026, 8, 6, 16, 0)
        db.commit()
        db.close()

        now = datetime(2026, 8, 13, 15, 30, tzinfo=timezone.utc)
        with (
            patch("api.main._utc_now", return_value=now),
            patch("api.main.generate_family_review_report_pdf", return_value=b"%PDF-test") as render_pdf,
        ):
            included = asyncio.run(export_family_review_report(
                grade="六年级",
                student_name="小明",
                subject="math",
                family_code="Home2026A",
            ))

        self.assertEqual(included.status_code, 200)
        self.assertEqual(len(render_pdf.call_args.kwargs["records"]), 1)

        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.created_at = datetime(2026, 8, 6, 15, 59, 59)
        db.commit()
        db.close()

        with patch("api.main._utc_now", return_value=now):
            excluded = asyncio.run(export_family_review_report(
                grade="六年级",
                student_name="小明",
                subject="math",
                family_code="Home2026A",
            ))

        self.assertEqual(excluded.status_code, 400)
        self.assertIn("近 7 天暂无", json.loads(excluded.body)["error"])

    def test_every_record_operation_rejects_the_wrong_family_code(self):
        calls = [
            lambda: analyze_exam(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: generate_practice(
                self.first_exam_id, "六年级", "小明", family_code="Other2026B"
            ),
            lambda: generate_knowledge_practice(
                "六年级",
                "小明",
                "math",
                "一元一次方程",
                family_code="Other2026B",
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
            lambda: update_wrong_question_mastery(
                self.first_exam_id,
                1,
                WrongQuestionMasteryRequest(mastered=True),
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

    def test_failed_ocr_removes_the_newly_stored_upload(self):
        class TestUpload:
            filename = "exam.png"
            content_type = "image/png"

            async def read(self):
                return b"exam-image"

        files_before = {path.name for path in Path(self.upload_dir.name).iterdir()}
        with patch(
            "api.main.baidu_ocr",
            new=AsyncMock(side_effect=RuntimeError("OCR unavailable")),
        ):
            response = asyncio.run(upload_exam(
                student_name="小明",
                grade="六年级",
                subject="math",
                file=TestUpload(),
                family_code="Home2026A",
            ))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            {path.name for path in Path(self.upload_dir.name).iterdir()},
            files_before,
        )

    def test_clear_subject_mismatch_rejects_upload_and_removes_stored_file(self):
        class TestUpload:
            filename = "english-exam.png"
            content_type = "image/png"

            async def read(self):
                return b"english-exam-image"

        files_before = {path.name for path in Path(self.upload_dir.name).iterdir()}
        with patch(
            "api.main.baidu_ocr",
            new=AsyncMock(return_value=(
                "Read the passage and choose the best answer. "
                "Tom usually walks to school, but yesterday he went by bus because it was raining. "
                "What did Tom do yesterday? Write a complete sentence and check your grammar."
            )),
        ):
            response = asyncio.run(upload_exam(
                student_name="小明",
                grade="六年级",
                subject="math",
                file=TestUpload(),
                family_code="Home2026A",
            ))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(payload["code"], "subject_mismatch")
        self.assertEqual(payload["detected_subject"], "english")
        self.assertIn("更像英语试卷", payload["error"])
        self.assertEqual(
            {path.name for path in Path(self.upload_dir.name).iterdir()},
            files_before,
        )
        db = self.session_factory()
        self.assertEqual(db.query(Exam).count(), 2)
        db.close()

    def test_multi_page_upload_creates_one_exam_record(self):
        class TestUpload:
            content_type = "image/png"

            def __init__(self, filename, content):
                self.filename = filename
                self.content = content

            async def read(self):
                return self.content

        with patch(
            "api.main.baidu_ocr",
            new=AsyncMock(side_effect=["第一页文字", "第二页文字"]),
        ):
            response = asyncio.run(upload_exam_batch(
                student_name="小明",
                grade="六年级",
                subject="math",
                files=[
                    TestUpload("page-1.png", b"page-one"),
                    TestUpload("page-2.png", b"page-two"),
                ],
                family_code="Home2026A",
            ))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["image_count"], 2)
        db = self.session_factory()
        uploaded = db.query(Exam).filter(Exam.id == payload["id"]).one()
        self.assertEqual(len(json.loads(uploaded.image_paths)), 2)
        self.assertIn("第 1 页", uploaded.ocr_text)
        self.assertIn("第一页文字", uploaded.ocr_text)
        self.assertIn("第 2 页", uploaded.ocr_text)
        self.assertIn("第二页文字", uploaded.ocr_text)
        db.close()

    def test_failed_multi_page_upload_removes_every_new_file_and_record(self):
        class TestUpload:
            content_type = "image/png"

            def __init__(self, filename, content):
                self.filename = filename
                self.content = content

            async def read(self):
                return self.content

        files_before = {path.name for path in Path(self.upload_dir.name).iterdir()}
        db = self.session_factory()
        exam_count_before = db.query(Exam).count()
        db.close()

        with patch(
            "api.main.baidu_ocr",
            new=AsyncMock(side_effect=["第一页文字", RuntimeError("OCR unavailable")]),
        ):
            response = asyncio.run(upload_exam_batch(
                student_name="小明",
                grade="六年级",
                subject="math",
                files=[
                    TestUpload("page-1.png", b"page-one"),
                    TestUpload("page-2.png", b"page-two"),
                ],
                family_code="Home2026A",
            ))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            {path.name for path in Path(self.upload_dir.name).iterdir()},
            files_before,
        )
        db = self.session_factory()
        self.assertEqual(db.query(Exam).count(), exam_count_before)
        db.close()

    def test_protected_original_can_return_a_specific_page(self):
        second_page = Path(self.upload_dir.name) / "protected-2.png"
        second_page.write_bytes(b"second-private-image")
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.image_paths = json.dumps([
            "/uploads/protected.png",
            "/uploads/protected-2.png",
        ])
        db.commit()
        db.close()

        response = asyncio.run(get_exam_image(
            self.first_exam_id,
            grade="六年级",
            student_name="小明",
            page=2,
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Path(response.path).name, "protected-2.png")

    def test_deleting_an_exam_also_deletes_its_original_upload(self):
        stored_file = Path(self.upload_dir.name) / "protected.png"
        second_page = Path(self.upload_dir.name) / "protected-2.png"
        second_page.write_bytes(b"second-private-image")
        db = self.session_factory()
        exam = db.query(Exam).filter(Exam.id == self.first_exam_id).one()
        exam.image_paths = json.dumps([
            "/uploads/protected.png",
            "/uploads/protected-2.png",
        ])
        db.commit()
        db.close()

        response = asyncio.run(delete_exam(
            self.first_exam_id,
            "六年级",
            "小明",
            family_code="Home2026A",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(stored_file.exists())
        self.assertFalse(second_page.exists())
        db = self.session_factory()
        self.assertIsNone(db.query(Exam).filter(Exam.id == self.first_exam_id).first())
        db.close()

    def test_upload_directory_is_not_publicly_mounted(self):
        mounted_paths = [getattr(route, "path", None) for route in app.routes]

        self.assertNotIn("/uploads", mounted_paths)

    def test_local_api_serves_the_brand_logo_used_by_the_frontend(self):
        response = asyncio.run(serve_logo())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Path(response.path).name, "logo.png")

    def test_reverse_proxy_does_not_publish_upload_directory(self):
        project_root = Path(__file__).parents[1]
        nginx_config = (project_root / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        compose_config = (project_root / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertNotIn("location /uploads", nginx_config)
        self.assertIn("family-review-report", nginx_config)
        self.assertIn("wrong-questions", nginx_config)
        self.assertIn("generate-knowledge-practice", nginx_config)
        self.assertEqual(compose_config.count("./uploads:/uploads"), 1)


if __name__ == "__main__":
    unittest.main()
