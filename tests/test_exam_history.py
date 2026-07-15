import json
import unittest

from api.main import _analysis_history_summary


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


if __name__ == "__main__":
    unittest.main()
