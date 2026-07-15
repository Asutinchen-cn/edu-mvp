import unittest

from api.main import (
    CURRICULUM_UNITS,
    WORKSHEET_GRADE_LABEL,
    UnitWorksheetRequest,
    _fallback_unit_worksheet,
)


class CurriculumUnitsTest(unittest.TestCase):
    def units_for(self, subject, semester):
        return [
            unit
            for unit in CURRICULUM_UNITS
            if unit["subject"] == subject and unit["semester"] == semester
        ]

    def test_curriculum_is_sixth_grade_only(self):
        self.assertEqual(WORKSHEET_GRADE_LABEL, "六年级")
        self.assertTrue(CURRICULUM_UNITS)
        for unit in CURRICULUM_UNITS:
            self.assertNotIn("-5", unit["id"])
            self.assertIn("六年级", unit["source_note"])

    def test_math_matches_shanghai_sixth_grade_chapters(self):
        first_titles = [unit["title"] for unit in self.units_for("math", "first")]
        second_titles = [unit["title"] for unit in self.units_for("math", "second")]

        self.assertEqual(
            first_titles,
            ["第一章 数的整除", "第二章 分数", "第三章 比和比例", "第四章 圆和扇形"],
        )
        self.assertEqual(
            second_titles,
            [
                "第五章 有理数",
                "第六章 一次方程（组）和一次不等式（组）",
                "第七章 线段与角的画法",
                "第八章 长方体的再认识",
            ],
        )

    def test_english_matches_oxford_shanghai_sixth_grade_units(self):
        first_titles = [unit["title"] for unit in self.units_for("english", "first")]
        second_titles = [unit["title"] for unit in self.units_for("english", "second")]

        self.assertEqual(len(first_titles), 11)
        self.assertEqual(first_titles[0], "Module 1 Unit 1 Family and relatives")
        self.assertEqual(first_titles[-1], "Module 3 Unit 11 Let's make a pizza")
        self.assertEqual(len(second_titles), 11)
        self.assertEqual(second_titles[0], "Module 1 Unit 1 Great cities in Asia")
        self.assertEqual(second_titles[-1], "Module 3 Unit 11 Controlling fire")


class SixthGradeFallbackTest(unittest.TestCase):
    def test_math_fallback_uses_selected_sixth_grade_topic(self):
        body = UnitWorksheetRequest(
            subject="math",
            semester="first",
            unit_ids=["math-6a-divisibility"],
            knowledge_points=["因数和倍数"],
            difficulty="basic",
            question_count=3,
            title="六年级数学复习",
        )

        questions = _fallback_unit_worksheet(body)

        self.assertEqual(len(questions), 3)
        self.assertTrue(all("因数和倍数" in q["knowledge_points"] for q in questions))
        self.assertFalse(any("2.4×3" in q["question"] for q in questions))
        self.assertFalse(any("3.6÷0.6" in q["question"] for q in questions))


if __name__ == "__main__":
    unittest.main()
