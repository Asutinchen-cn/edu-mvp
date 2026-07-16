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
        self.assertIn('<option value="九年级">九年级</option>', HTML)
        self.assertNotIn('value="九年级" disabled', HTML)
        self.assertIn("u.grade === grade", HTML)
        self.assertRegex(HTML, r"grade:\s*document\.getElementById\('worksheetGrade'\)\.value")

    def test_ninth_grade_english_requires_an_explicit_school_edition(self):
        self.assertIn('id="worksheetEditionField"', HTML)
        self.assertIn('id="worksheetEnglishEdition"', HTML)
        self.assertIn('<option value="oxford-shanghai">牛津上海版</option>', HTML)
        self.assertIn('<option value="new-century">新世纪版</option>', HTML)
        self.assertIn("u.edition === edition", HTML)
        self.assertIn("grade === '九年级' && subject === 'english'", HTML)
        self.assertIn(".worksheet-field[hidden]", HTML)

    def test_analysis_grade_selector_is_focused_on_junior_middle_school(self):
        for grade in ("六年级", "七年级", "八年级", "九年级"):
            self.assertIn(f'<option value="{grade}"', HTML)

        for grade in ("一年级", "五年级", "高一", "高三"):
            self.assertNotIn(f'<option value="{grade}"', HTML)

    def test_wrong_bank_uses_a_family_access_code_without_persisting_it(self):
        self.assertIn('id="familyAccessCode"', HTML)
        self.assertIn('type="password"', HTML)
        self.assertIn("function familyAccessHeaders", HTML)
        self.assertIn("'X-Family-Code': familyCode", HTML)
        self.assertNotIn("localStorage.setItem('familyAccessCode'", HTML)
        self.assertNotRegex(HTML, r"URLSearchParams\([^)]*familyAccessCode")

    def test_returning_parent_can_query_wrong_bank_without_scrolling_to_upload_form(self):
        self.assertIn('id="wrongBankDialog"', HTML)
        self.assertIn('id="wrongBankGrade"', HTML)
        self.assertIn('id="wrongBankStudentName"', HTML)
        self.assertIn('id="wrongBankFamilyCode"', HTML)
        self.assertIn('novalidate onsubmit="submitWrongBankQuery(event)"', HTML)
        self.assertIn('onclick="openWrongBankQuery()"', HTML)
        self.assertIn("function openWrongBankQuery()", HTML)
        self.assertIn("function submitWrongBankQuery(event)", HTML)
        self.assertIn("wrongBankDialog.showModal()", HTML)
        self.assertIn("wrongBankDialog.addEventListener('cancel'", HTML)
        self.assertIn("historyStatus.classList.remove('show')", HTML)

    def test_family_access_code_has_safe_visibility_and_generation_helpers(self):
        self.assertIn("function toggleFamilyCodeVisibility", HTML)
        self.assertIn("function generateFamilyAccessCode", HTML)
        self.assertIn("crypto.getRandomValues", HTML)
        self.assertIn('aria-label="显示家庭访问码"', HTML)
        self.assertIn('aria-label="生成家庭访问码"', HTML)
        self.assertNotIn("localStorage.setItem('familyAccessCode'", HTML)

    def test_original_exam_files_use_the_protected_image_endpoint(self):
        self.assertIn("async function openProtectedExamImage(id)", HTML)
        self.assertIn("/image?${params.toString()}", HTML)
        self.assertIn("headers: accessHeaders", HTML)
        self.assertNotIn("function safeUploadUrl", HTML)
        self.assertNotIn("href=\"${escapeHtml(imageUrl)}\"", HTML)

    def test_analysis_result_gives_parents_an_evidence_based_action_plan(self):
        self.assertIn("function buildParentReviewPlan(data)", HTML)
        self.assertIn("7 天复习安排", HTML)
        self.assertIn("本次识别错题", HTML)
        self.assertNotIn("总错误率", HTML)

    def test_analysis_distribution_uses_real_wrong_question_counts(self):
        self.assertIn("function buildErrorTypeStats(wrongQuestions, providedStats = [])", HTML)
        self.assertIn("analysis.evidence_note", HTML)
        self.assertIn("证据已核对", HTML)
        self.assertIn("已过滤串科内容", HTML)
        self.assertNotIn("Math.ceil(wq.length / displayErrorTypes.length)", HTML)

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

    def test_history_can_export_a_protected_correction_sheet(self):
        self.assertIn("function exportCorrectionSheet(id)", HTML)
        self.assertIn("/correction-sheet?${params.toString()}", HTML)
        self.assertIn("headers: familyAccessHeaders()", HTML)
        self.assertIn("URL.createObjectURL(await response.blob())", HTML)
        self.assertIn("导出订正单", HTML)
        self.assertIn("correctionExporting: false", HTML)

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

    def test_history_defaults_to_a_parent_focused_pending_review_queue(self):
        self.assertIn("let currentMasteryFilter = 'pending'", HTML)
        self.assertIn('data-mastery-filter="pending"', HTML)
        self.assertIn('id="masteryCountPending"', HTML)
        self.assertIn('data-mastery-filter="mastered"', HTML)
        self.assertIn('id="masteryCountMastered"', HTML)
        self.assertIn("function recordMasteryStatus(record)", HTML)
        self.assertIn("function setMasteryFilter(status)", HTML)
        self.assertIn("function updateMasteryFilterCounts(records)", HTML)
        self.assertIn("progress.completedCount === progress.total", HTML)
        self.assertIn("currentMasteryFilter !== 'all'", HTML)
        self.assertIn("本筛选范围内的错题都已完成三步复习", HTML)

    def test_transient_history_request_flags_are_cleared_after_reload(self):
        self.assertIn("detailLoading: false", HTML)
        self.assertIn("progressSaving: false", HTML)
        self.assertIn("function saveHistoryRecords()", HTML)


if __name__ == "__main__":
    unittest.main()
