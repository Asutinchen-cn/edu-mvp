import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fontTools.ttLib import TTFont

from api.main import (
    UnitWorksheetRequest,
    _fallback_unit_worksheet,
    _validate_generated_questions,
    _validate_unit_request,
    ai_generate_unit_worksheet,
    call_deepseek,
    generate_unit_worksheet_pdf,
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


def rational_math_body():
    return UnitWorksheetRequest(
        grade="六年级",
        subject="math",
        semester="first",
        unit_ids=["math-6a-rational-numbers"],
        knowledge_points=["有理数的加法与减法"],
        difficulty="basic",
        question_count=3,
        title="六年级有理数单元诊断卷",
    )


def rational_math_questions():
    return [
        {
            "id": "q1",
            "unit_id": "math-6a-rational-numbers",
            "type": "选择题",
            "question": "下列说法正确的是（ ）",
            "options": [
                "A. 两个有理数的和一定大于每一个加数",
                "B. 减去一个负数，等于加上这个数的相反数",
                "C. 异号两数相加，取绝对值较大的加数的符号，并用较大的绝对值减去较小的绝对值",
                "D. 一个数减去 0，差为 0",
            ],
            "answer": "C",
            "explanation": "B 表述不完整，C 正确。",
            "knowledge_points": ["有理数的加法与减法"],
            "exam_focus": "有理数加减法则",
            "common_mistake": "负数减法变号错误",
            "teaching_intent": "判断学生是否真正理解核心概念",
        },
        {
            "id": "q2",
            "unit_id": "math-6a-rational-numbers",
            "type": "填空题",
            "question": "计算：(-3)-(-7)=______。",
            "options": [],
            "answer": "4",
            "explanation": "(-3)-(-7)=(-3)+7=4。",
            "knowledge_points": ["有理数的加法与减法"],
            "exam_focus": "有理数减法",
            "common_mistake": "减去负数时没有变号",
            "teaching_intent": "检查单步算法和书写准确性",
        },
        {
            "id": "q3",
            "unit_id": "math-6a-rational-numbers",
            "type": "应用题",
            "question": "小明从起点向东走 5 米，向西走 8 米，再向东走 3 米。他最后在哪里？",
            "options": [],
            "answer": "回到起点，距离起点 0 米。",
            "explanation": "规定向东为正，5-8+3=0，所以回到起点。",
            "knowledge_points": ["有理数的加法与减法"],
            "exam_focus": "用有理数表示方向和位移",
            "common_mistake": "方向符号混淆",
            "teaching_intent": "把单一考点放入直接情境",
        },
    ]


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

    async def test_semantic_review_replaces_an_ambiguous_math_paper(self):
        body = rational_math_body()
        units = _validate_unit_request(body)
        ambiguous_questions = rational_math_questions()
        generated_response = json.dumps(
            {"questions": ambiguous_questions},
            ensure_ascii=False,
        )
        review_response = json.dumps(
            {
                "valid": False,
                "issues": [
                    {
                        "number": 1,
                        "reason": "B 与 C 都可成立，选择题答案不唯一",
                    }
                ],
            },
            ensure_ascii=False,
        )

        with patch(
            "api.main.call_deepseek",
            new=AsyncMock(side_effect=[generated_response, review_response]),
        ) as mocked_call:
            questions = await ai_generate_unit_worksheet(body, units)

        self.assertEqual(mocked_call.await_count, 2)
        self.assertIn("逐项独立求解", mocked_call.await_args_list[1].args[0])
        self.assertNotEqual(questions[0]["question"], ambiguous_questions[0]["question"])
        self.assertIn("回到起点", questions[2]["answer"])


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

    def test_zero_distance_cannot_still_claim_a_compass_direction(self):
        questions = rational_math_questions()
        questions[2]["answer"] = "在起点正西方向，距离起点 0 米。"
        questions[2]["explanation"] = "5-8+3=0，所以回到了起点。"

        with self.assertRaisesRegex(ValueError, "答案.*矛盾"):
            _validate_generated_questions(rational_math_body(), questions)

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

    def test_rational_number_fallback_has_a_consistent_real_context(self):
        body = rational_math_body()
        questions = _fallback_unit_worksheet(body, _validate_unit_request(body))

        self.assertEqual(
            [question["type"] for question in questions],
            ["选择题", "填空题", "应用题"],
        )
        self.assertIn("回到起点", questions[2]["answer"])
        self.assertNotRegex(questions[2]["answer"], r"[东南西北]方向")
        self.assertIn("5", questions[2]["question"])
        self.assertIn("8", questions[2]["question"])


class WorksheetPdfCompatibilityTest(unittest.TestCase):
    def test_ai_line_breaks_do_not_fragment_question_or_explanation_text(self):
        pdftotext = shutil.which("pdftotext")
        if not pdftotext:
            self.skipTest("Poppler PDF inspection tools are not installed")

        questions = rational_math_questions()
        questions[2]["question"] = "某冷库的室温为\n-4℃，目标为\n-25℃。"
        questions[2]["explanation"] = "选项\nA\n错误，因为\n0\n不是正数。"

        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "answer.pdf"
            pdf_path.write_bytes(
                generate_unit_worksheet_pdf(
                    rational_math_body(), questions, include_answers=True
                )
            )
            text_result = subprocess.run(
                [pdftotext, str(pdf_path), "-"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(text_result.returncode, 0, text_result.stderr)
        self.assertIn("某冷库的室温为 -4℃，目标为 -25℃。", text_result.stdout)
        self.assertIn("解析：选项 A 错误，因为 0 不是正数。", text_result.stdout)

    def test_question_and_answer_pdfs_embed_a_matching_truetype_font(self):
        font_dir = Path(__file__).parents[1] / "fonts"
        for font_path in (
            font_dir / "NotoSansSC-Regular.ttf",
            font_dir / "NotoSansSC-Bold.ttf",
        ):
            self.assertTrue(font_path.exists())
            with TTFont(font_path) as font:
                self.assertIn("glyf", font)
                self.assertNotIn("CFF ", font)
                self.assertNotIn("fvar", font)

        pdffonts = shutil.which("pdffonts")
        pdftotext = shutil.which("pdftotext")
        if not pdffonts or not pdftotext:
            self.skipTest("Poppler PDF inspection tools are not installed")

        body = rational_math_body()
        questions = rational_math_questions()
        with tempfile.TemporaryDirectory() as directory:
            for include_answers, filename in (
                (False, "question.pdf"),
                (True, "answer.pdf"),
            ):
                pdf_path = Path(directory) / filename
                pdf_path.write_bytes(
                    generate_unit_worksheet_pdf(body, questions, include_answers)
                )

                font_result = subprocess.run(
                    [pdffonts, str(pdf_path)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                font_output = font_result.stdout + font_result.stderr
                self.assertEqual(font_result.returncode, 0, font_output)
                self.assertNotIn("Mismatch between font type", font_output)
                self.assertIn("CID TrueType", font_result.stdout)

                text_result = subprocess.run(
                    [pdftotext, str(pdf_path), "-"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(text_result.returncode, 0, text_result.stderr)
                self.assertNotIn("Mismatch between font type", text_result.stderr)
                self.assertIn("六年级有理数单元诊断卷", text_result.stdout)
                self.assertIn("(-3)-(-7)=______", text_result.stdout)
                if include_answers:
                    self.assertIn("答案：4", text_result.stdout)
                else:
                    self.assertNotIn("答案：4", text_result.stdout)


if __name__ == "__main__":
    unittest.main()
