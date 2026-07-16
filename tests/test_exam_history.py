import json
import unittest

from api.main import (
    _analysis_history_detail,
    _analysis_history_summary,
    _normalize_ai_analysis,
    _normalize_review_progress,
    generate_correction_sheet_pdf,
    generate_family_review_report_pdf,
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
            }],
            "error_types": ["移项符号错误"],
            "weak_points": ["一元一次方程"],
            "root_cause": "没有理解移项要改变符号。",
            "recommendations": ["先口述等式两边同时运算的理由。"],
        }, ensure_ascii=False))

        self.assertEqual(detail["wrong_questions"][0]["student_answer"], "x = 6")
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
    def test_normalizes_completed_review_stages_in_teaching_order(self):
        progress = _normalize_review_progress(json.dumps({
            "completed": ["retested", "corrected", "unknown", "corrected"],
            "updated_at": "2026-07-15T12:00:00",
        }))

        self.assertEqual(progress["completed"], ["corrected", "retested"])
        self.assertEqual(progress["completed_count"], 2)
        self.assertEqual(progress["total"], 3)
        self.assertEqual(progress["next_step"], "practiced")
        self.assertEqual(progress["updated_at"], "2026-07-15T12:00:00")

    def test_invalid_review_progress_starts_from_correction(self):
        self.assertEqual(
            _normalize_review_progress("not-json"),
            {
                "completed": [],
                "completed_count": 0,
                "total": 3,
                "next_step": "corrected",
                "updated_at": None,
            },
        )


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
    def test_builds_a_weekly_report_from_saved_summary_evidence(self):
        pdf_bytes = generate_family_review_report_pdf(
            student_name="小明",
            grade="六年级",
            records=[{
                "subject": "math",
                "created_at": "2026-07-16T10:00:00",
                "wrong_count": 2,
                "weak_points": ["一元一次方程"],
                "review_progress": {
                    "completed": ["corrected"],
                    "completed_count": 1,
                    "total": 3,
                    "next_step": "practiced",
                },
            }],
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 5000)


if __name__ == "__main__":
    unittest.main()
