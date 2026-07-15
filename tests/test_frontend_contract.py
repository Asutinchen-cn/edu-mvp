from pathlib import Path
import re
import unittest


HTML = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")


class FrontendCurriculumContractTest(unittest.TestCase):
    def test_brand_logo_is_used_as_the_site_icon(self):
        self.assertIn('<link rel="icon" href="logo.png" type="image/png">', HTML)

    def test_sixth_grade_is_the_default_analysis_grade(self):
        self.assertRegex(HTML, r'<option value="六年级" selected>六年级</option>')
        self.assertNotRegex(HTML, r'<option value="五年级" selected>')

    def test_worksheet_displays_curriculum_source_metadata(self):
        self.assertIn('id="worksheetSource"', HTML)
        self.assertIn("let worksheetMeta = null", HTML)
        self.assertIn("worksheetMeta = data.meta || null", HTML)
        self.assertGreaterEqual(len(re.findall(r"renderWorksheetSource\(\)", HTML)), 2)

    def test_worksheet_is_grade_aware_and_does_not_silently_reuse_sixth_grade(self):
        self.assertIn('id="worksheetGrade"', HTML)
        self.assertIn('<option value="七年级">七年级</option>', HTML)
        self.assertNotIn('value="七年级" disabled', HTML)
        self.assertIn('<option value="八年级">八年级</option>', HTML)
        self.assertNotIn('value="八年级" disabled', HTML)
        self.assertIn('value="九年级" disabled', HTML)
        self.assertIn("u.grade === grade", HTML)
        self.assertRegex(HTML, r"grade:\s*document\.getElementById\('worksheetGrade'\)\.value")

    def test_analysis_grade_selector_is_focused_on_junior_middle_school(self):
        for grade in ("六年级", "七年级", "八年级", "九年级"):
            self.assertIn(f'<option value="{grade}"', HTML)

        for grade in ("一年级", "五年级", "高一", "高三"):
            self.assertNotIn(f'<option value="{grade}"', HTML)

    def test_analysis_result_gives_parents_an_evidence_based_action_plan(self):
        self.assertIn("function buildParentReviewPlan(data)", HTML)
        self.assertIn("7 天复习安排", HTML)
        self.assertIn("本次识别错题", HTML)
        self.assertNotIn("总错误率", HTML)

    def test_ai_practice_content_is_escaped_before_rendering(self):
        self.assertIn("currentPracticeQuestions = questions", HTML)
        self.assertIn("${escapeHtml(q.question)}", HTML)
        self.assertIn("checkAnswer(${i}, ${j})", HTML)
        self.assertNotIn("checkAnswer(${i}, '${q.answer}'", HTML)

    def test_history_has_an_evidence_based_parent_dashboard(self):
        self.assertIn('id="reviewDashboard"', HTML)
        self.assertIn("function buildReviewDashboard(records)", HTML)
        self.assertIn("function renderReviewDashboard(records)", HTML)
        self.assertIn("function normalizeWrongCount(value)", HTML)
        self.assertIn("value === null || value === undefined || value === ''", HTML)
        self.assertIn("只反映已保存的分析记录，不代表考试成绩", HTML)
        self.assertNotIn("进步率", HTML)

    def test_history_records_render_readable_diagnosis_and_actions(self):
        self.assertIn("function renderHistoryDiagnosis(record)", HTML)
        self.assertIn("async function loadHistoryDetail(id)", HTML)
        self.assertIn("function prepareHistoryPractice(id)", HTML)
        self.assertIn("错题诊断", HTML)
        self.assertIn("生成巩固练习", HTML)
        self.assertNotIn("<pre>${escapeHtml(r.result)}</pre>", HTML)

    def test_practice_generation_uses_the_saved_exam_endpoint(self):
        self.assertIn("const examId = currentAnalysisData.examIds?.[0]", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/generate-practice/\$\{examId\}\?\$\{params\.toString\(\)\}`",
        )
        self.assertNotIn("fetch('/generate-practice'", HTML)

    def test_history_string_ids_are_safe_inside_inline_actions(self):
        self.assertIn("escapeHtml(JSON.stringify(r.id))", HTML)
        self.assertIn("escapeHtml(JSON.stringify(record.id))", HTML)
        self.assertNotIn('onclick="toggleRecord(${JSON.stringify(r.id)})"', HTML)

    def test_history_has_server_synced_three_step_mastery_progress(self):
        self.assertIn("三步掌握进度", HTML)
        self.assertIn("订正原题", HTML)
        self.assertIn("完成同类题", HTML)
        self.assertIn("隔天回测", HTML)
        self.assertIn("async function toggleReviewStep(id, step)", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/exams/\$\{record\.serverId\}/review-progress\?\$\{params\.toString\(\)\}`",
        )
        self.assertIn("method: 'PATCH'", HTML)

    def test_transient_history_request_flags_are_cleared_after_reload(self):
        self.assertIn("detailLoading: false", HTML)
        self.assertIn("progressSaving: false", HTML)
        self.assertIn("function saveHistoryRecords()", HTML)


if __name__ == "__main__":
    unittest.main()
