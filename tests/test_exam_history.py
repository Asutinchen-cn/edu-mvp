import asyncio
import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from pypdf import PdfReader
from pypdf.generic import ContentStream

from api.main import (
    AnalysisServiceUnavailable,
    _analysis_history_detail,
    _analysis_history_summary,
    _build_review_schedule,
    _family_report_window_start,
    _normalize_ai_analysis,
    _normalize_review_progress,
    _summarize_family_review_records,
    ai_generate_questions,
    generate_correction_sheet_pdf,
    generate_family_review_report_pdf,
    generate_practice_pdf,
)


class AiAnalysisNormalizationTest(unittest.TestCase):
    def test_error_distribution_uses_saved_wrong_question_counts(self):
        analysis = _normalize_ai_analysis({
            "subject": "math",
            "wrong_questions": [
                {"question": "计算 1", "error_type": "计算错误", "student_answer": "1", "correct_answer": "2"},
                {"question": "计算 2", "error_type": "计算错误", "student_answer": "3", "correct_answer": "4"},
                {"question": "应用题", "error_type": "审题错误", "student_answer": "5", "correct_answer": "6"},
            ],
            "error_types": ["计算错误", "审题错误"],
            "weak_points": ["有理数运算"],
            "root_cause": "计算步骤不稳定。",
            "recommendations": ["逐步验算。"],
        }, "math")

        self.assertEqual(analysis["wrong_count"], 3)
        self.assertEqual(
            analysis["error_type_stats"],
            [
                {"name": "计算错误", "count": 2, "percent": 67},
                {"name": "审题错误", "count": 1, "percent": 33},
            ],
        )
        self.assertEqual(analysis["evidence_status"], "confirmed")

    def test_english_analysis_filters_math_content_before_it_is_saved(self):
        analysis = _normalize_ai_analysis({
            "subject": "math",
            "wrong_questions": [
                {"question": "计算小数加法", "error_type": "小数计算错误", "student_answer": "1.2", "correct_answer": "1.3"},
                {"question": "Choose the correct past tense.", "error_type": "一般过去时错误", "student_answer": "go", "correct_answer": "went"},
            ],
            "error_types": ["小数计算错误", "一般过去时错误"],
            "weak_points": ["小数运算", "一般过去时", "阅读理解", "一般过去时"],
            "root_cause": "小数计算和时态都不稳定。",
            "recommendations": ["练习小数计算。", "圈出英语句中的时间标志。"],
        }, "english")

        self.assertEqual(analysis["subject"], "english")
        self.assertEqual(len(analysis["wrong_questions"]), 1)
        self.assertEqual(analysis["wrong_questions"][0]["error_type"], "一般过去时错误")
        self.assertEqual(analysis["weak_points"], ["一般过去时", "阅读理解"])
        self.assertEqual(analysis["recommendations"], ["圈出英语句中的时间标志。"])
        self.assertEqual(analysis["evidence_status"], "filtered")
        self.assertIn("已过滤", analysis["evidence_note"])

    def test_analysis_without_wrong_question_evidence_is_not_presented_as_confirmed(self):
        analysis = _normalize_ai_analysis({
            "subject": "english",
            "wrong_questions": [],
            "error_types": ["一般过去时错误"],
            "weak_points": ["一般过去时"],
            "root_cause": "图片中没有看清学生作答。",
            "recommendations": ["重新上传清晰图片。"],
        }, "english")

        self.assertEqual(analysis["wrong_count"], 0)
        self.assertEqual(analysis["error_type_stats"], [])
        self.assertEqual(analysis["evidence_status"], "insufficient")

    def test_focused_practice_prompt_keeps_grade_subject_and_error_evidence(self):
        generated = json.dumps([
            {
                "id": index,
                "type": "填空题",
                "question": f"Yesterday, Tom ___ home early. ({index})",
                "answer": "went",
                "hint": "Look at the time word.",
            }
            for index in range(1, 6)
        ])
        model = AsyncMock(return_value=generated)

        with patch("api.main.call_deepseek", model):
            asyncio.run(ai_generate_questions(
                ["一般过去时"],
                subject="english",
                grade="六年级",
                wrong_questions=[{
                    "question": "Yesterday I go home.",
                    "error_type": "一般过去时错误",
                    "student_answer": "go",
                    "correct_answer": "went",
                }],
            ))
        prompt = model.await_args.args[0]

        self.assertIn("资深六年级英语教师", prompt)
        self.assertIn("只生成英语题", prompt)
        self.assertIn("一般过去时错误", prompt)
        self.assertIn("不得照抄原题", prompt)

    def test_practice_generation_rejects_an_incomplete_model_paper(self):
        incomplete = json.dumps([{
            "id": 1,
            "type": "填空题",
            "question": "Yesterday, Tom ___ home early.",
            "answer": "went",
            "hint": "Look at the time word.",
        }])

        with patch("api.main.call_deepseek", AsyncMock(return_value=incomplete)):
            with self.assertRaises(AnalysisServiceUnavailable):
                asyncio.run(ai_generate_questions(
                    ["一般过去时"],
                    subject="english",
                    grade="六年级",
                ))

    def test_practice_generation_rejects_invalid_choice_answers(self):
        invalid = json.dumps([
            {
                "id": index,
                "type": "选择题",
                "question": f"Choose the correct answer. ({index})",
                "options": ["one", "two", "three", "four"],
                "answer": "E",
                "hint": "Read the sentence.",
            }
            for index in range(1, 6)
        ])

        with patch("api.main.call_deepseek", AsyncMock(return_value=invalid)):
            with self.assertRaises(AnalysisServiceUnavailable):
                asyncio.run(ai_generate_questions(
                    ["一般过去时"],
                    subject="english",
                    grade="六年级",
                ))

    def test_practice_generation_removes_model_option_labels(self):
        generated = json.dumps([
            {
                "id": index,
                "type": "选择题",
                "question": f"My brother often ___ his homework. ({index})",
                "options": ["A. do", "B. does", "C. doing", "D. to do"],
                "answer": "does",
                "hint": "Check the subject.",
            }
            for index in range(1, 6)
        ])

        with patch("api.main.call_deepseek", AsyncMock(return_value=generated)):
            questions = asyncio.run(ai_generate_questions(
                ["一般现在时"],
                subject="english",
                grade="六年级",
            ))

        self.assertEqual(questions[0]["options"], ["do", "does", "doing", "to do"])
        self.assertEqual(questions[0]["answer"], "B")


class AnalysisHistorySummaryTest(unittest.TestCase):
    def test_counts_only_saved_wrong_questions(self):
        summary = _analysis_history_summary(json.dumps({
            "wrong_questions": [{"question": "A"}, {"question": "B"}],
            "weak_points": ["一元一次方程", "有理数运算"],
        }, ensure_ascii=False))

        self.assertEqual(summary["wrong_count"], 2)
        self.assertEqual(summary["weak_points"], ["一元一次方程", "有理数运算"])

    def test_missing_or_invalid_analysis_is_unknown(self):
        self.assertEqual(
            _analysis_history_summary(None),
            {"wrong_count": None, "weak_points": []},
        )

    def test_legacy_weak_points_are_preserved_without_full_analysis(self):
        summary = _analysis_history_summary(
            None,
            json.dumps(["一般过去时", "阅读细节理解"], ensure_ascii=False),
        )

        self.assertEqual(summary["wrong_count"], None)
        self.assertEqual(summary["weak_points"], ["一般过去时", "阅读细节理解"])
        self.assertEqual(
            _analysis_history_summary("not-json"),
            {"wrong_count": None, "weak_points": []},
        )


class AnalysisHistoryDetailTest(unittest.TestCase):
    def test_returns_parent_readable_saved_analysis(self):
        detail = _analysis_history_detail(json.dumps({
            "wrong_questions": [{
                "question": "解方程 2x + 3 = 9",
                "error_type": "移项符号错误",
                "student_answer": "x = 6",
                "correct_answer": "x = 3",
                "knowledge_point": "一元一次方程",
            }],
            "error_types": ["移项符号错误"],
            "weak_points": ["一元一次方程"],
            "root_cause": "没有理解移项要改变符号。",
            "recommendations": ["先口述等式两边同时运算的理由。"],
        }, ensure_ascii=False))

        self.assertEqual(detail["wrong_questions"][0]["student_answer"], "x = 6")
        self.assertEqual(detail["wrong_questions"][0]["knowledge_point"], "一元一次方程")
        self.assertEqual(detail["weak_points"], ["一元一次方程"])
        self.assertEqual(detail["root_cause"], "没有理解移项要改变符号。")
        self.assertEqual(detail["recommendations"], ["先口述等式两边同时运算的理由。"])

    def test_recomputes_error_distribution_from_saved_wrong_questions(self):
        detail = _analysis_history_detail(json.dumps({
            "wrong_questions": [
                {"question": "题 1", "error_type": "计算错误"},
                {"question": "题 2", "error_type": "计算错误"},
                {"question": "题 3", "error_type": "审题错误"},
            ],
            "error_type_stats": [{"name": "错误的旧统计", "count": 9, "percent": 100}],
            "evidence_status": "confirmed",
            "evidence_note": "只依据保存的错题证据。",
        }, ensure_ascii=False))

        self.assertEqual(
            detail["error_type_stats"],
            [
                {"name": "计算错误", "count": 2, "percent": 67},
                {"name": "审题错误", "count": 1, "percent": 33},
            ],
        )
        self.assertEqual(detail["evidence_status"], "confirmed")
        self.assertEqual(detail["evidence_note"], "只依据保存的错题证据。")

    def test_falls_back_to_legacy_weak_points_and_recommendations(self):
        detail = _analysis_history_detail(
            None,
            json.dumps(["一般过去时"], ensure_ascii=False),
            json.dumps(["回到原句辨认时间标志。"], ensure_ascii=False),
        )

        self.assertEqual(detail["wrong_questions"], [])
        self.assertEqual(detail["weak_points"], ["一般过去时"])
        self.assertEqual(detail["recommendations"], ["回到原句辨认时间标志。"])


class ReviewProgressTest(unittest.TestCase):
    def test_normalizes_only_a_contiguous_teaching_sequence(self):
        progress = _normalize_review_progress(json.dumps({
            "completed": ["retested", "corrected", "unknown", "corrected"],
            "updated_at": "2026-07-15T12:00:00",
            "completed_at": {
                "corrected": "2026-07-15T10:00:00Z",
                "retested": "2026-07-15T12:00:00Z",
            },
        }))

        self.assertEqual(progress["completed"], ["corrected"])
        self.assertEqual(progress["completed_count"], 1)
        self.assertEqual(progress["total"], 3)
        self.assertEqual(progress["next_step"], "practiced")
        self.assertEqual(progress["updated_at"], "2026-07-15T12:00:00")
        self.assertEqual(
            progress["completed_at"],
            {"corrected": "2026-07-15T10:00:00Z"},
        )

    def test_invalid_review_progress_starts_from_correction(self):
        self.assertEqual(
            _normalize_review_progress("not-json"),
            {
                "completed": [],
                "completed_count": 0,
                "total": 3,
                "next_step": "corrected",
                "updated_at": None,
                "completed_at": {},
            },
        )

    def test_builds_due_dates_for_the_three_step_review_rhythm(self):
        created_at = datetime(2026, 7, 15, 4, 0, tzinfo=timezone.utc)
        now = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)

        correction = _build_review_schedule(created_at, {}, now=now)
        practice = _build_review_schedule(created_at, {
            "completed": ["corrected"],
            "completed_at": {"corrected": "2026-07-15T05:00:00Z"},
        }, now=now)
        retest = _build_review_schedule(created_at, {
            "completed": ["corrected", "practiced"],
            "completed_at": {
                "corrected": "2026-07-15T05:00:00Z",
                "practiced": "2026-07-15T06:00:00Z",
            },
        }, now=now)
        overdue_retest = _build_review_schedule(
            created_at,
            {
                "completed": ["corrected", "practiced"],
                "completed_at": {
                    "corrected": "2026-07-15T05:00:00Z",
                    "practiced": "2026-07-15T06:00:00Z",
                },
            },
            now=datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc),
        )
        completed = _build_review_schedule(created_at, {
            "completed": ["corrected", "practiced", "retested"],
        }, now=now)

        self.assertEqual(correction, {
            "next_step": "corrected",
            "due_at": "2026-07-15T04:00:00Z",
            "status": "today",
        })
        self.assertEqual(practice, {
            "next_step": "practiced",
            "due_at": "2026-07-15T05:00:00Z",
            "status": "today",
        })
        self.assertEqual(retest, {
            "next_step": "retested",
            "due_at": "2026-07-16T06:00:00Z",
            "status": "upcoming",
        })
        self.assertEqual(overdue_retest["status"], "overdue")
        self.assertEqual(completed, {
            "next_step": None,
            "due_at": None,
            "status": "completed",
        })


class PracticePdfTest(unittest.TestCase):
    def test_builds_the_current_five_questions_without_answers_or_hints(self):
        questions = [
            {
                "type": "选择题",
                "question": "Choose the correct past tense of go.",
                "options": ["go", "goes", "went", "going"],
                "answer": "C",
                "hint": "Look for yesterday.",
            },
            {
                "type": "填空题",
                "question": "Yesterday I ____ to school.",
                "options": [],
                "answer": "went",
                "hint": "Use the past tense.",
            },
            {
                "type": "选择题",
                "question": "Which sentence is correct?",
                "options": ["I go yesterday.", "I went yesterday.", "I going yesterday.", "I goes yesterday."],
                "answer": "B",
                "hint": "Find the time marker.",
            },
            {
                "type": "填空题",
                "question": "Last week they ____ football.",
                "options": [],
                "answer": "played",
                "hint": "Add -ed.",
            },
            {
                "type": "选择题",
                "question": "What did Ben do last night?",
                "options": ["He reads.", "He read a book.", "He reading.", "He is read."],
                "answer": "B",
                "hint": "Read is irregular here.",
            },
        ]

        pdf_bytes = generate_practice_pdf(
            "小明",
            ["一般过去时"],
            questions,
            grade="六年级",
            subject="english",
        )
        text = "\n".join(
            page.extract_text() or ""
            for page in PdfReader(io.BytesIO(pdf_bytes)).pages
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn("错题巩固练习", text)
        self.assertIn("学生：小明", text)
        self.assertIn("年级：六年级", text)
        self.assertIn("学科：英语", text)
        self.assertIn("Choose the correct past tense of go.", text)
        self.assertIn("C. went", text)
        self.assertIn("答：", text)
        self.assertNotIn("Consolidation Practice", text)
        self.assertNotIn("答案：", text)
        self.assertNotIn("提示：", text)
        self.assertNotIn("Look for yesterday.", text)


class CorrectionSheetPdfTest(unittest.TestCase):
    def test_builds_a_printable_pdf_from_saved_wrong_question_evidence(self):
        pdf_bytes = generate_correction_sheet_pdf(
            student_name="小明",
            grade="六年级",
            subject="math",
            created_at="2026-07-16",
            analysis={
                "wrong_questions": [{
                    "question": "解方程 2x + 3 = 9",
                    "error_type": "移项符号错误",
                    "student_answer": "x = 6",
                    "correct_answer": "x = 3",
                }],
                "weak_points": ["一元一次方程"],
                "root_cause": "没有理解移项要改变符号。",
                "recommendations": ["先口述等式两边同时运算的理由。"],
            },
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 5000)


class FamilyReviewReportPdfTest(unittest.TestCase):
    def test_report_window_covers_seven_complete_shanghai_calendar_days(self):
        now = datetime(2026, 8, 13, 15, 30, tzinfo=timezone.utc)

        cutoff = _family_report_window_start(now)

        self.assertEqual(cutoff, datetime(2026, 8, 6, 16, 0, tzinfo=timezone.utc))

    def test_weekly_summary_uses_question_mastery_and_groups_by_subject_and_point(self):
        summary = _summarize_family_review_records([
            {
                "exam_id": 11,
                "subject": "math",
                "created_at": "2026-07-16T10:00:00",
                "wrong_questions": [
                    {"knowledge_point": "一元一次方程", "mastered": True},
                    {"knowledge_point": "有理数加法", "mastered": False},
                ],
            },
            {
                "exam_id": 12,
                "subject": "math",
                "created_at": "2026-07-17T10:00:00",
                "wrong_questions": [
                    {"knowledge_point": "一元一次方程", "mastered": False},
                ],
            },
            {
                "exam_id": 13,
                "subject": "english",
                "created_at": "2026-07-18T10:00:00",
                "wrong_questions": [
                    {"knowledge_point": "一般过去时", "mastered": True},
                ],
            },
        ])

        self.assertEqual(summary["exam_count"], 3)
        self.assertEqual(summary["question_count"], 4)
        self.assertEqual(summary["mastered_count"], 2)
        self.assertEqual(summary["pending_count"], 2)
        self.assertEqual(summary["subject_exam_counts"], {"math": 2, "english": 1})
        self.assertEqual(summary["knowledge_points"][0], {
            "name": "一元一次方程",
            "subject": "math",
            "wrong_count": 2,
            "mastered_count": 1,
            "pending_count": 1,
            "source_exam_count": 2,
        })
        self.assertEqual(
            [(item["name"], item["pending_count"]) for item in summary["priority_tasks"]],
            [("一元一次方程", 1), ("有理数加法", 1)],
        )

        empty_summary = _summarize_family_review_records([{
            "exam_id": 14,
            "subject": "math",
            "wrong_questions": [],
        }])
        self.assertEqual(empty_summary["question_count"], 0)
        self.assertEqual(empty_summary["priority_tasks"], [])

    def test_weekly_summary_separates_new_errors_from_mastered_old_questions(self):
        summary = _summarize_family_review_records([
            {
                "exam_id": 21,
                "subject": "math",
                "created_in_window": True,
                "wrong_questions": [
                    {
                        "knowledge_point": "一元一次方程",
                        "mastered": True,
                        "recorded_in_window": True,
                        "mastered_in_window": False,
                    },
                    {
                        "knowledge_point": "有理数加法",
                        "mastered": False,
                        "recorded_in_window": True,
                        "mastered_in_window": False,
                    },
                ],
            },
            {
                "exam_id": 22,
                "subject": "math",
                "created_in_window": False,
                "wrong_questions": [{
                    "knowledge_point": "一元一次方程",
                    "mastered": True,
                    "recorded_in_window": False,
                    "mastered_in_window": True,
                }],
            },
        ])

        self.assertEqual(summary["new_exam_count"], 1)
        self.assertEqual(summary["recorded_question_count"], 2)
        self.assertEqual(summary["mastered_this_week_count"], 1)
        self.assertEqual(summary["pending_recorded_count"], 1)
        self.assertEqual(summary["reviewed_old_exam_count"], 1)

    def test_builds_a_weekly_report_from_saved_summary_evidence(self):
        pdf_bytes = generate_family_review_report_pdf(
            student_name="小明",
            grade="六年级",
            report_now=datetime(2026, 8, 13, 15, 30, tzinfo=timezone.utc),
            records=[{
                "exam_id": 11,
                "subject": "math",
                "created_at": "2026-07-16T10:00:00",
                "wrong_questions": [
                    {"knowledge_point": "一元一次方程", "mastered": True},
                    {"knowledge_point": "一元一次方程", "mastered": False},
                ],
            }],
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 5000)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("周期：2026-08-07 至 2026-08-13", text)
        self.assertNotIn("周期：2026-08-06 至 2026-08-13", text)

    def test_weekly_report_labels_new_errors_and_this_week_mastery_separately(self):
        pdf_bytes = generate_family_review_report_pdf(
            student_name="小明",
            grade="六年级",
            report_now=datetime(2026, 8, 13, 15, 30, tzinfo=timezone.utc),
            records=[
                {
                    "exam_id": 21,
                    "subject": "math",
                    "created_in_window": True,
                    "wrong_questions": [
                        {
                            "knowledge_point": "一元一次方程",
                            "mastered": True,
                            "recorded_in_window": True,
                            "mastered_in_window": False,
                        },
                        {
                            "knowledge_point": "有理数加法",
                            "mastered": False,
                            "recorded_in_window": True,
                            "mastered_in_window": False,
                        },
                    ],
                },
                {
                    "exam_id": 22,
                    "subject": "math",
                    "created_in_window": False,
                    "wrong_questions": [{
                        "knowledge_point": "一元一次方程",
                        "mastered": True,
                        "recorded_in_window": False,
                        "mastered_in_window": True,
                    }],
                },
            ],
        )

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("新分析 1 份", text)
        self.assertIn("新录错题 2 道", text)
        self.assertIn("本周掌握 1 道", text)
        self.assertIn("新增待复习 1 道", text)
        self.assertIn("本周标记掌握且当前仍为掌握状态的旧错题", text)
        content = ContentStream(reader.pages[0].get_contents(), reader)
        self.assertNotIn(b"TJ", [operator for _, operator in content.operations])


if __name__ == "__main__":
    unittest.main()
