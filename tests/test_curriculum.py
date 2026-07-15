import unittest

from api.main import (
    CURRICULUM_META,
    CURRICULUM_UNITS,
    WORKSHEET_GRADE_LABEL,
    UnitWorksheetRequest,
    _fallback_english_content,
    _fallback_math_content,
    _fallback_unit_worksheet,
    _validate_unit_request,
)


class CurriculumUnitsTest(unittest.TestCase):
    def units_for(self, subject, semester, grade="六年级"):
        return [
            unit
            for unit in CURRICULUM_UNITS
            if unit["grade"] == grade
            and unit["subject"] == subject
            and unit["semester"] == semester
        ]

    def test_curriculum_declares_available_and_pending_junior_grades(self):
        self.assertEqual(WORKSHEET_GRADE_LABEL, "六年级")
        self.assertEqual(CURRICULUM_META["default_grade"], "六年级")
        self.assertEqual(CURRICULUM_META["available_grades"], ["六年级", "七年级"])
        self.assertEqual(
            [item["value"] for item in CURRICULUM_META["grades"]],
            ["六年级", "七年级", "八年级", "九年级"],
        )
        self.assertTrue(CURRICULUM_UNITS)
        self.assertEqual(
            {unit["grade"] for unit in CURRICULUM_UNITS},
            {"六年级", "七年级"},
        )

    def test_math_matches_current_shanghai_sixth_grade_chapters(self):
        first_titles = [unit["title"] for unit in self.units_for("math", "first")]
        second_titles = [unit["title"] for unit in self.units_for("math", "second")]

        self.assertEqual(
            first_titles,
            ["第1章 有理数", "第2章 简单的代数式", "第3章 一元一次方程", "第4章 线段与角"],
        )
        self.assertEqual(
            second_titles,
            [
                "第5章 比与比例",
                "第6章 圆与扇形",
                "第7章 可能性与统计图表",
                "第8章 圆柱与圆锥",
                "第9章 二元一次方程组",
            ],
        )

    def test_english_matches_current_shanghai_sixth_grade_units(self):
        first_titles = [unit["title"] for unit in self.units_for("english", "first")]
        second_titles = [unit["title"] for unit in self.units_for("english", "second")]

        self.assertEqual(
            first_titles,
            [
                "Unit 1 School life",
                "Unit 2 Family ties",
                "Unit 3 Food",
                "Unit 4 Sports",
                "Unit 5 Animals and us",
                "Unit 6 Travelling around China",
            ],
        )
        self.assertEqual(
            second_titles,
            [
                "Unit 1 Everyone is different",
                "Unit 2 Rules around us",
                "Unit 3 Festivals across cultures",
                "Unit 4 Weather and our lives",
                "Unit 5 Green neighbourhood",
                "Unit 6 Famous people in history",
            ],
        )

    def test_math_matches_current_shanghai_seventh_grade_chapters(self):
        first_titles = [unit["title"] for unit in self.units_for("math", "first", "七年级")]
        second_titles = [unit["title"] for unit in self.units_for("math", "second", "七年级")]

        self.assertEqual(
            first_titles,
            ["第10章 整式的加减", "第11章 整式的乘除", "第12章 因式分解", "第13章 分式", "第14章 图形的运动"],
        )
        self.assertEqual(
            second_titles,
            ["第15章 一元一次不等式", "第16章 相交线与平行线", "第17章 三角形", "第18章 等腰三角形"],
        )

    def test_english_matches_current_shanghai_seventh_grade_units(self):
        first_titles = [unit["title"] for unit in self.units_for("english", "first", "七年级")]
        second_titles = [unit["title"] for unit in self.units_for("english", "second", "七年级")]

        self.assertEqual(
            first_titles,
            [
                "Unit 1 Friendship",
                "Unit 2 School life",
                "Unit 3 The seasons",
                "Unit 4 The Earth",
                "Unit 5 Off to space",
                "Unit 6 Travelling around Asia",
                "Unit 7 Fun after school",
                "Unit 8 Collecting as a hobby",
            ],
        )
        self.assertEqual(
            second_titles,
            [
                "Unit 1 Music",
                "Unit 2 Language and communication",
                "Unit 3 A helping hand",
                "Unit 4 Honesty",
                "Unit 5 Wild animals",
                "Unit 6 Trees",
            ],
        )


class GradeAwareWorksheetTest(unittest.TestCase):
    def test_math_fallback_uses_selected_current_topic(self):
        body = UnitWorksheetRequest(
            grade="六年级",
            subject="math",
            semester="first",
            unit_ids=["math-6a-rational-numbers"],
            knowledge_points=["有理数的加法与减法"],
            difficulty="basic",
            question_count=3,
            title="六年级数学复习",
        )

        selected_units = _validate_unit_request(body)
        questions = _fallback_unit_worksheet(body, selected_units)

        self.assertEqual(len(questions), 3)
        self.assertTrue(all("有理数的加法与减法" in q["knowledge_points"] for q in questions))

    def test_unavailable_grade_is_rejected_instead_of_using_other_grade_units(self):
        body = UnitWorksheetRequest(
            grade="八年级",
            subject="math",
            semester="first",
            unit_ids=["math-6a-rational-numbers"],
            knowledge_points=["有理数的加法与减法"],
            difficulty="basic",
            question_count=3,
            title="八年级数学复习",
        )

        with self.assertRaisesRegex(ValueError, "八年级教材目录尚未开放"):
            _validate_unit_request(body)

    def test_seventh_grade_math_fallback_is_specific_to_factoring(self):
        body = UnitWorksheetRequest(
            grade="七年级",
            subject="math",
            semester="first",
            unit_ids=["math-7a-factoring"],
            knowledge_points=["提公因式法"],
            difficulty="advanced",
            question_count=3,
            title="七年级数学复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertTrue(all("因式" in (q["question"] + q["explanation"]) for q in questions))
        self.assertFalse(any(q["question"].startswith("请用一个例子说明") for q in questions))

    def test_seventh_grade_english_fallback_is_specific_to_wildlife(self):
        body = UnitWorksheetRequest(
            grade="七年级",
            subject="english",
            semester="second",
            unit_ids=["english-7b-u5-wild-animals"],
            knowledge_points=["wildlife conservation"],
            difficulty="advanced",
            question_count=3,
            title="七年级英语复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        content = " ".join(q["question"] + " " + q["explanation"] for q in questions).lower()

        self.assertTrue(any(term in content for term in ("wildlife", "wild animals", "protect")))
        self.assertFalse(any("best matches the topic" in q["question"] for q in questions))

    def test_every_seventh_grade_knowledge_point_has_a_specific_fallback(self):
        generic_questions = []
        for unit in CURRICULUM_UNITS:
            if unit["grade"] != "七年级":
                continue
            fallback = _fallback_math_content if unit["subject"] == "math" else _fallback_english_content
            for point in unit["knowledge_points"]:
                question = fallback(point)["question"]
                if question.startswith("请用一个例子说明") or "best matches the topic" in question:
                    generic_questions.append((unit["id"], point))

        self.assertEqual(generic_questions, [])

    def test_seventh_grade_geometry_fallback_respects_the_selected_point(self):
        cases = {
            "平移": "平移",
            "旋转": "旋转",
            "轴对称": "轴对称",
            "中心对称": "中心对称",
            "等腰三角形的性质": "等腰三角形",
            "等边三角形": "等边三角形",
            "线段垂直平分线": "垂直平分线",
        }

        for point, expected in cases.items():
            content = _fallback_math_content(point)
            self.assertIn(expected, content["question"] + content["explanation"])

    def test_current_math_fallback_is_specific_to_cylinder_topic(self):
        body = UnitWorksheetRequest(
            grade="六年级",
            subject="math",
            semester="second",
            unit_ids=["math-6b-cylinder-cone"],
            knowledge_points=["圆柱及其侧面展开图"],
            difficulty="basic",
            question_count=3,
            title="六年级数学复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertTrue(all("圆柱" in (q["question"] + q["explanation"]) for q in questions))
        self.assertFalse(any(q["question"].startswith("请用一个例子说明") for q in questions))

    def test_current_english_fallback_is_specific_to_sports_topic(self):
        body = UnitWorksheetRequest(
            grade="六年级",
            subject="english",
            semester="first",
            unit_ids=["english-6a-u4-sports"],
            knowledge_points=["sports safety"],
            difficulty="basic",
            question_count=3,
            title="六年级英语复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertTrue(all("sport" in (q["question"] + q["explanation"]).lower() for q in questions))
        self.assertFalse(any("best matches the topic" in q["question"] for q in questions))


if __name__ == "__main__":
    unittest.main()
