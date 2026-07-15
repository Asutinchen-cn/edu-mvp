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
    def units_for(self, subject, semester, grade="六年级", edition=None):
        return [
            unit
            for unit in CURRICULUM_UNITS
            if unit["grade"] == grade
            and unit["subject"] == subject
            and unit["semester"] == semester
            and (edition is None or unit.get("edition") == edition)
        ]

    def test_curriculum_declares_available_and_pending_junior_grades(self):
        self.assertEqual(WORKSHEET_GRADE_LABEL, "六年级")
        self.assertEqual(CURRICULUM_META["default_grade"], "六年级")
        self.assertEqual(
            CURRICULUM_META["available_grades"],
            ["六年级", "七年级", "八年级", "九年级"],
        )
        self.assertEqual(
            [item["value"] for item in CURRICULUM_META["grades"]],
            ["六年级", "七年级", "八年级", "九年级"],
        )
        self.assertTrue(CURRICULUM_UNITS)
        self.assertEqual(
            {unit["grade"] for unit in CURRICULUM_UNITS},
            {"六年级", "七年级", "八年级", "九年级"},
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

    def test_math_matches_current_shanghai_eighth_grade_chapters(self):
        first_titles = [unit["title"] for unit in self.units_for("math", "first", "八年级")]
        second_titles = [unit["title"] for unit in self.units_for("math", "second", "八年级")]

        self.assertEqual(
            first_titles,
            ["第19章 实数", "第20章 二次根式", "第21章 一元二次方程", "第22章 直角三角形"],
        )
        self.assertEqual(
            second_titles,
            ["第23章 四边形", "第24章 平面直角坐标系", "第25章 一次函数", "第26章 反比例函数"],
        )

    def test_english_matches_current_shanghai_eighth_grade_units(self):
        first_titles = [unit["title"] for unit in self.units_for("english", "first", "八年级")]
        second_titles = [unit["title"] for unit in self.units_for("english", "second", "八年级")]

        self.assertEqual(
            first_titles,
            [
                "Unit 1 Water",
                "Unit 2 Digital life",
                "Unit 3 Curious minds",
                "Unit 4 Then and now",
                "Unit 5 Teamwork",
                "Unit 6 Life in the future",
            ],
        )
        self.assertEqual(
            second_titles,
            [
                "Unit 1 Art and artists",
                "Unit 2 Great inventions and discoveries",
                "Unit 3 Money",
                "Unit 4 Fashion",
                "Unit 5 Natural disasters",
                "Unit 6 Friendship",
            ],
        )

    def test_eighth_grade_second_semester_source_is_marked_pending_approval(self):
        second_semester_units = [
            unit
            for unit in CURRICULUM_UNITS
            if unit["grade"] == "八年级" and unit["semester"] == "second"
        ]

        self.assertTrue(second_semester_units)
        self.assertTrue(all("待审" in unit["source_note"] for unit in second_semester_units))

    def test_math_matches_current_shanghai_ninth_grade_trial_chapters(self):
        first_titles = [unit["title"] for unit in self.units_for("math", "first", "九年级")]
        second_titles = [unit["title"] for unit in self.units_for("math", "second", "九年级")]

        self.assertEqual(
            first_titles,
            ["第24章 相似三角形", "第25章 锐角的三角比", "第26章 二次函数"],
        )
        self.assertEqual(second_titles, ["第27章 圆与正多边形", "第28章 统计初步"])

    def test_oxford_english_matches_current_shanghai_ninth_grade_units(self):
        first_titles = [
            unit["title"]
            for unit in self.units_for("english", "first", "九年级", "oxford-shanghai")
        ]
        second_titles = [
            unit["title"]
            for unit in self.units_for("english", "second", "九年级", "oxford-shanghai")
        ]

        self.assertEqual(
            first_titles,
            [
                "Unit 1 Ancient Greece",
                "Unit 2 Traditional skills",
                "Unit 3 Pets",
                "Unit 4 Computers",
                "Unit 5 The human brain",
                "Unit 6 Detectives",
                "Unit 7 Escaping from kidnappers",
            ],
        )
        self.assertEqual(
            second_titles,
            [
                "Unit 1 Saving the Earth",
                "Unit 2 Life in the future",
                "Unit 3 Going places",
                "Unit 4 All about films and TV",
                "Unit 5 A story by Mark Twain",
            ],
        )

    def test_new_century_english_matches_current_shanghai_ninth_grade_units(self):
        first_titles = [
            unit["title"]
            for unit in self.units_for("english", "first", "九年级", "new-century")
        ]
        second_titles = [
            unit["title"]
            for unit in self.units_for("english", "second", "九年级", "new-century")
        ]

        self.assertEqual(
            first_titles,
            [
                "Unit 1 International Visits",
                "Unit 2 Post and Communications",
                "Unit 3 Science and Technology",
                "Unit 4 Student Life",
            ],
        )
        self.assertEqual(second_titles, ["Unit 1 Values", "Unit 2 Changes in Life"])

    def test_ninth_grade_english_units_are_partitioned_by_school_edition(self):
        english_units = [
            unit
            for unit in CURRICULUM_UNITS
            if unit["grade"] == "九年级" and unit["subject"] == "english"
        ]

        self.assertEqual(
            {unit.get("edition") for unit in english_units},
            {"oxford-shanghai", "new-century"},
        )
        self.assertTrue(all("版本" in unit["source_note"] for unit in english_units))


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
            grade="五年级",
            subject="math",
            semester="first",
            unit_ids=["math-6a-rational-numbers"],
            knowledge_points=["有理数的加法与减法"],
            difficulty="basic",
            question_count=3,
            title="五年级数学复习",
        )

        with self.assertRaisesRegex(ValueError, "五年级教材目录尚未开放"):
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

    def test_eighth_grade_math_fallback_uses_quadratic_discriminant(self):
        body = UnitWorksheetRequest(
            grade="八年级",
            subject="math",
            semester="first",
            unit_ids=["math-8a-quadratic-equations"],
            knowledge_points=["一元二次方程的判别式"],
            difficulty="advanced",
            question_count=8,
            title="八年级数学复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        content = " ".join(q["question"] + " " + q["explanation"] for q in questions)

        self.assertTrue(any(term in content for term in ("判别式", "Δ")))
        self.assertFalse(any(q["question"].startswith("请用一个例子说明") for q in questions))
        self.assertEqual(len({q["question"] for q in questions}), 8)

    def test_eighth_grade_english_fallback_is_specific_to_natural_disasters(self):
        body = UnitWorksheetRequest(
            grade="八年级",
            subject="english",
            semester="second",
            unit_ids=["english-8b-u5-natural-disasters"],
            knowledge_points=["warnings and safety"],
            difficulty="advanced",
            question_count=3,
            title="八年级英语复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        content = " ".join(q["question"] + " " + q["explanation"] for q in questions).lower()

        self.assertTrue(any(term in content for term in ("disaster", "warning", "safety", "earthquake")))
        self.assertFalse(any("best matches the topic" in q["question"] for q in questions))
        self.assertEqual(len({q["question"] for q in questions}), 3)

    def test_every_eighth_grade_knowledge_point_has_a_specific_fallback(self):
        generic_questions = []
        for unit in CURRICULUM_UNITS:
            if unit["grade"] != "八年级":
                continue
            fallback = _fallback_math_content if unit["subject"] == "math" else _fallback_english_content
            for point in unit["knowledge_points"]:
                question = fallback(point)["question"]
                if question.startswith("请用一个例子说明") or "best matches the topic" in question:
                    generic_questions.append((unit["id"], point))

        self.assertEqual(generic_questions, [])

    def test_eighth_grade_function_fallback_respects_the_selected_point(self):
        cases = {
            "一次函数的图像与性质": "一次函数",
            "反比例函数的图像与性质": "反比例函数",
            "两点间的距离公式": "距离",
            "平移与轴对称的坐标变化": "对称",
        }

        for point, expected in cases.items():
            content = _fallback_math_content(point)
            self.assertIn(expected, content["question"] + content["explanation"])

    def test_ninth_grade_math_fallback_is_specific_to_quadratic_functions(self):
        body = UnitWorksheetRequest(
            grade="九年级",
            subject="math",
            semester="first",
            unit_ids=["math-9a-quadratic-functions"],
            knowledge_points=["二次函数的图像与性质"],
            difficulty="advanced",
            question_count=3,
            title="九年级数学复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        content = " ".join(q["question"] + " " + q["explanation"] for q in questions)

        self.assertIn("二次函数", content)
        self.assertEqual(len({q["question"] for q in questions}), 3)

    def test_ninth_grade_new_century_fallback_is_specific_to_broadcasting(self):
        body = UnitWorksheetRequest(
            grade="九年级",
            subject="english",
            semester="first",
            unit_ids=["english-9a-new-century-u2-communications"],
            knowledge_points=["school broadcasting"],
            difficulty="advanced",
            question_count=3,
            title="九年级新世纪英语复习",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        content = " ".join(q["question"] + " " + q["explanation"] for q in questions).lower()

        self.assertTrue(any(term in content for term in ("broadcast", "report", "news")))
        self.assertEqual(len({q["question"] for q in questions}), 3)

    def test_ninth_grade_english_request_cannot_mix_school_editions(self):
        body = UnitWorksheetRequest(
            grade="九年级",
            subject="english",
            semester="first",
            unit_ids=[
                "english-9a-oxford-u1-ancient-greece",
                "english-9a-new-century-u1-international-visits",
            ],
            knowledge_points=["ancient Greek history", "travelling by air"],
            difficulty="advanced",
            question_count=3,
            title="九年级英语复习",
        )

        with self.assertRaisesRegex(ValueError, "英语版本"):
            _validate_unit_request(body)

    def test_every_ninth_grade_knowledge_point_has_a_specific_fallback(self):
        generic_questions = []
        for unit in CURRICULUM_UNITS:
            if unit["grade"] != "九年级":
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
