import unittest
from unittest.mock import AsyncMock, patch

from api.main import (
    UnitWorksheetRequest,
    _fallback_unit_worksheet,
    _validate_generated_questions,
    _validate_unit_request,
    ai_generate_unit_worksheet,
    call_deepseek,
)


def math_body(question_count=3):
    return UnitWorksheetRequest(
        grade="六年级",
        subject="math",
        semester="second",
        unit_ids=["math-6b-cylinder-cone"],
        knowledge_points=["圆柱及其侧面展开图", "圆锥及其侧面展开图"],
        difficulty="advanced",
        question_count=question_count,
        title="六年级圆柱与圆锥单元诊断卷",
    )


def valid_math_questions():
    return [
        {
            "id": "q1",
            "unit_id": "math-6b-cylinder-cone",
            "type": "填空题",
            "question": "圆柱底面半径为 3 cm，侧面展开图的长是多少？",
            "options": [],
            "answer": "6π cm",
            "explanation": "底面周长为 2πr=6π cm。",
            "knowledge_points": ["圆柱及其侧面展开图"],
            "exam_focus": "圆柱侧面展开图",
            "common_mistake": "把半径当作展开图的长",
            "teaching_intent": "检查基本概念",
        },
        {
            "id": "q2",
            "unit_id": "math-6b-cylinder-cone",
            "type": "选择题",
            "question": "圆锥的侧面展开图是什么图形？",
            "options": ["A. 扇形", "B. 三角形", "C. 圆", "D. 梯形"],
            "answer": "A",
            "explanation": "圆锥的侧面展开图是扇形。",
            "knowledge_points": ["圆锥及其侧面展开图"],
            "exam_focus": "圆锥侧面展开图",
            "common_mistake": "把轴截面和侧面展开图混淆",
            "teaching_intent": "辨析图形",
        },
        {
            "id": "q3",
            "unit_id": "math-6b-cylinder-cone",
            "type": "解答题",
            "question": "说明圆柱侧面展开图的长与底面周长的关系。",
            "options": [],
            "answer": "二者相等。",
            "explanation": "沿高剪开后，底面圆周恰好成为长方形的一条边。",
            "knowledge_points": ["圆柱及其侧面展开图"],
            "exam_focus": "展开图边长关系",
            "common_mistake": "把底面直径当作展开图的长",
            "teaching_intent": "解释数量关系",
        },
    ]


class DeepSeekWorksheetRequestTest(unittest.IsolatedAsyncioTestCase):
    async def test_structured_requests_disable_default_thinking_mode(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def post(self, url, json, headers):
                captured["payload"] = json
                return FakeResponse()

        with patch("api.main.httpx.AsyncClient", return_value=FakeClient()):
            result = await call_deepseek("Return JSON.", json_mode=True)

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(captured["payload"]["thinking"], {"type": "disabled"})

    async def test_invalid_ai_paper_falls_back_after_one_attempt_with_topic_guardrails(self):
        body = math_body(question_count=6)
        units = _validate_unit_request(body)
        invalid_response = '{"questions": []}'

        with patch(
            "api.main.call_deepseek",
            new=AsyncMock(return_value=invalid_response),
        ) as mocked_call:
            questions = await ai_generate_unit_worksheet(body, units)

        self.assertEqual(mocked_call.await_count, 1)
        self.assertIn("不得考体积", mocked_call.await_args.args[0])
        self.assertEqual(len(questions), 6)
        self.assertEqual(len({question["question"] for question in questions}), 6)


class WorksheetQualityValidationTest(unittest.TestCase):
    def test_duplicate_question_stems_are_rejected(self):
        questions = valid_math_questions()
        questions[2]["question"] = questions[0]["question"]

        with self.assertRaisesRegex(ValueError, "重复"):
            _validate_generated_questions(math_body(), questions)

    def test_choice_answer_must_reference_one_of_four_options(self):
        questions = valid_math_questions()
        questions[1]["answer"] = "E"

        with self.assertRaisesRegex(ValueError, "答案"):
            _validate_generated_questions(math_body(), questions)

    def test_question_type_and_knowledge_point_must_follow_plan(self):
        questions = valid_math_questions()
        questions[0]["type"] = "选择题"
        questions[0]["knowledge_points"] = ["未选择的知识点"]

        with self.assertRaisesRegex(ValueError, "题型|知识点"):
            _validate_generated_questions(math_body(), questions)

    def test_math_answer_keeps_steps_in_explanation_instead_of_final_answer(self):
        questions = valid_math_questions()
        questions[2]["answer"] = (
            "先设半径为 r，再列出 2πr=12.56，解得 r=2；然后根据展开图边长得到高为 "
            "12.56 cm。这里继续重复很多计算步骤，导致答案字段不再是便于核对的最终结果。"
        )

        with self.assertRaisesRegex(ValueError, "答案.*简洁"):
            _validate_generated_questions(math_body(), questions)

    def test_cylinder_and_cone_unfolding_questions_reject_volume_detours(self):
        questions = valid_math_questions()
        questions[2]["question"] = "一个圆锥形沙堆体积是多少？"
        questions[2]["answer"] = "25.12 m³"
        questions[2]["explanation"] = "使用圆锥体积公式计算。"

        with self.assertRaisesRegex(ValueError, "考点"):
            _validate_generated_questions(math_body(), questions)

    def test_text_only_pdf_rejects_questions_that_reference_a_missing_figure(self):
        questions = valid_math_questions()
        questions[2]["question"] = "如图，说明圆柱侧面展开图的长与底面周长的关系。"

        with self.assertRaisesRegex(ValueError, "图片"):
            _validate_generated_questions(math_body(), questions)

    def test_reading_may_use_choices_but_writing_must_stay_open(self):
        body = UnitWorksheetRequest(
            grade="八年级",
            subject="english",
            semester="second",
            unit_ids=["english-8b-u5-natural-disasters"],
            knowledge_points=[
                "types of natural disasters",
                "warnings and safety",
                "disaster news reports",
                "emergency preparation",
            ],
            difficulty="advanced",
            question_count=4,
            title="Natural disasters",
        )
        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))
        questions[2]["options"] = [
            "A. To stay safe from flooding.",
            "B. To watch a film.",
            "C. To attend a party.",
            "D. To play sport.",
        ]
        questions[2]["answer"] = "A"

        self.assertEqual(_validate_generated_questions(body, questions), questions)

        questions[3]["options"] = ["A. One", "B. Two", "C. Three", "D. Four"]
        questions[3]["answer"] = "A"
        with self.assertRaisesRegex(ValueError, "开放题"):
            _validate_generated_questions(body, questions)


class WorksheetFallbackQualityTest(unittest.TestCase):
    def test_math_fallback_uses_real_varied_question_types(self):
        body = math_body(question_count=6)
        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertEqual(
            [question["type"] for question in questions],
            ["填空题", "选择题", "解答题", "应用题", "填空题", "选择题"],
        )
        self.assertEqual(len({question["question"] for question in questions}), 6)
        self.assertTrue(all(question["answer"].strip() for question in questions))
        self.assertTrue(all(question["explanation"].strip() for question in questions))

    def test_english_fallback_includes_reading_and_open_writing(self):
        body = UnitWorksheetRequest(
            grade="八年级",
            subject="english",
            semester="second",
            unit_ids=["english-8b-u5-natural-disasters"],
            knowledge_points=[
                "types of natural disasters",
                "warnings and safety",
                "disaster news reports",
                "emergency preparation",
            ],
            difficulty="advanced",
            question_count=6,
            title="八年级 Natural disasters 单元诊断卷",
        )

        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertEqual(
            [question["type"] for question in questions],
            ["词汇选择", "语法选择", "阅读理解", "书面表达", "词汇选择", "语法选择"],
        )
        self.assertEqual(len({question["question"] for question in questions}), 6)
        self.assertEqual(questions[2]["options"], [])
        self.assertEqual(questions[3]["options"], [])
        self.assertIn("Read", questions[2]["question"])
        self.assertIn("Write", questions[3]["question"])


if __name__ == "__main__":
    unittest.main()
