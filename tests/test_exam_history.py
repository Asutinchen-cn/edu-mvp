import json
import unittest

from api.main import _analysis_history_detail, _analysis_history_summary, _normalize_review_progress


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


if __name__ == "__main__":
    unittest.main()
