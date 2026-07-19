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
        self.assertIn('onclick="openWrongBankQuery()">查看今日复习</button>', HTML)
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
        self.assertIn("firstEmptyField.focus();", HTML)
        self.assertIn("await setHistoryView('exams');", HTML)
        self.assertNotIn("window.setTimeout(() => firstEmptyField.focus()", HTML)

    def test_returning_parent_can_remember_only_non_secret_family_profile_fields(self):
        self.assertIn("const FAMILY_PROFILE_STORAGE_KEY = 'xiahunao_family_profile'", HTML)
        self.assertIn("function loadRememberedFamilyProfile()", HTML)
        self.assertIn("function rememberFamilyProfile(grade, studentName, enabled)", HTML)
        self.assertIn("function restoreRememberedFamilyProfile()", HTML)
        self.assertIn('id="rememberFamilyProfile"', HTML)
        self.assertIn('id="wrongBankRememberProfile"', HTML)
        self.assertIn("restoreRememberedFamilyProfile();", HTML)
        self.assertIn("rememberFamilyProfile(grade, name,", HTML)
        self.assertIn("rememberFamilyProfile(grade, studentName,", HTML)
        self.assertNotRegex(
            HTML,
            r"localStorage\.setItem\([^\n]*(familyAccessCode|wrongBankFamilyCode|family_code|familyCode)",
        )

    def test_analysis_requires_a_named_student_for_reliable_wrong_bank_lookup(self):
        self.assertRegex(
            HTML,
            r'<input type="text" id="studentName"[^>]*required[^>]*autocomplete="name"',
        )
        self.assertIn("const name = document.getElementById('studentName').value.trim();", HTML)
        self.assertIn("alert('请填写学生姓名，之后查询家庭错题库需要使用同一姓名')", HTML)
        self.assertNotIn("document.getElementById('studentName').value || '同学'", HTML)

    def test_mobile_layout_prioritizes_the_real_upload_tool(self):
        mobile_css = re.search(r"@media \(max-width: 768px\) \{(?P<body>.*?)\n        \}", HTML, re.S)
        self.assertIsNotNone(mobile_css)
        css = mobile_css.group("body")
        self.assertRegex(css, r"\.hero-card\s*\{[^}]*display:\s*none")
        self.assertRegex(css, r"\.steps-sidebar\s*\{[^}]*display:\s*none")
        self.assertRegex(css, r"\.hero-actions\s*\{[^}]*grid-template-columns:\s*repeat\(2,")
        self.assertRegex(css, r"\.main-card\s*\{[^}]*margin:\s*10px 12px")

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
        self.assertIn("params.set('page', String(pageNumber))", HTML)
        self.assertIn("headers: accessHeaders", HTML)
        self.assertIn("record.imageCount", HTML)
        self.assertIn("查看原卷（", HTML)
        self.assertNotIn("function safeUploadUrl", HTML)
        self.assertNotIn("href=\"${escapeHtml(imageUrl)}\"", HTML)

    def test_multi_page_exam_is_uploaded_and_analyzed_as_one_record(self):
        self.assertIn("fd.append('files', current.file, current.name)", HTML)
        self.assertIn("requestJson('/upload-batch'", HTML)
        self.assertIn("imageCount: uploadJson.image_count", HTML)
        self.assertIn("uploadedFiles.length >= 12", HTML)
        self.assertIn("totalBytes + f.size > 50 * 1024 * 1024", HTML)
        self.assertNotIn("mergeApiAnalyses(apiAnalyses, subject)", HTML)

    def test_uploaded_exam_can_retry_ai_analysis_without_reuploading_files(self):
        self.assertIn("let uploadedExam = null", HTML)
        self.assertIn("function savePendingAnalysisRecord", HTML)
        self.assertIn("analysisStatus: 'pending'", HTML)
        self.assertIn("async function retryExamAnalysis(id)", HTML)
        self.assertIn("重新分析", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/analyze/\$\{record\.serverId\}\?\$\{params\.toString\(\)\}`",
        )
        self.assertIn("record.analysisStatus === 'pending'", HTML)
        self.assertIn("等待 AI 分析", HTML)

    def test_server_record_deletion_explains_that_originals_are_removed(self):
        self.assertIn("原卷文件和分析结果将一并删除，且无法恢复", HTML)

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

    def test_focused_practice_can_confirm_mastery_only_after_a_perfect_score(self):
        self.assertIn("let currentPracticeResults = []", HTML)
        self.assertIn("function practiceAnswersMatch(givenAnswer, expectedAnswer)", HTML)
        self.assertIn("function recordPracticeResult(questionIndex, isCorrect)", HTML)
        self.assertIn("function renderPracticeResultPanel()", HTML)
        self.assertIn("本轮答对", HTML)
        self.assertIn("查看答案按未答对记录", HTML)
        self.assertIn("currentPracticeResults.every(result => result === true)", HTML)
        self.assertIn("async function confirmKnowledgeMastery()", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/wrong-questions/mastery-by-knowledge\?\$\{params\.toString\(\)\}`",
        )
        self.assertIn("确认本知识点已掌握", HTML)

    def test_history_has_an_evidence_based_parent_dashboard(self):
        self.assertIn('id="reviewDashboard"', HTML)
        self.assertIn("function buildReviewDashboard(records)", HTML)
        self.assertIn("function renderReviewDashboard(records)", HTML)
        self.assertIn("function normalizeWrongCount(value)", HTML)
        self.assertIn("value === null || value === undefined || value === ''", HTML)
        self.assertIn("数据来自服务器保存的试卷与逐题复习状态，不代表考试成绩", HTML)
        self.assertNotIn("进步率", HTML)

    def test_history_records_render_readable_diagnosis_and_actions(self):
        self.assertIn("function renderHistoryDiagnosis(record)", HTML)
        self.assertIn("async function loadHistoryDetail(id)", HTML)
        self.assertIn("function prepareHistoryPractice(id)", HTML)
        self.assertIn("错题诊断", HTML)
        self.assertIn("生成巩固练习", HTML)
        self.assertNotIn("<pre>${escapeHtml(r.result)}</pre>", HTML)

    def test_wrong_bank_can_browse_questions_grouped_by_knowledge_point(self):
        self.assertIn('data-history-view="exams"', HTML)
        self.assertIn('data-history-view="knowledge"', HTML)
        self.assertIn("function setHistoryView(view)", HTML)
        self.assertIn("async function loadWrongQuestionBank", HTML)
        self.assertIn("/wrong-questions?${params.toString()}", HTML)
        self.assertIn("function renderKnowledgeQuestionBank()", HTML)
        self.assertIn("function openQuestionSourceExam(examId)", HTML)
        self.assertIn("按知识点", HTML)

    def test_knowledge_point_group_can_generate_focused_practice(self):
        self.assertIn("function prepareKnowledgePractice(knowledgePoint, subject)", HTML)
        self.assertIn("生成专项练习", HTML)
        self.assertIn("practiceKnowledgePoint: knowledgePoint", HTML)
        self.assertIn("practiceFromWrongBank: true", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/generate-knowledge-practice\?\$\{params\.toString\(\)\}`",
        )
        self.assertIn("params.set('subject', currentAnalysisData.subject)", HTML)
        self.assertIn("data.pending_wrong_count", HTML)

    def test_each_wrong_question_has_an_independent_server_synced_mastery_status(self):
        self.assertIn("function wrongQuestionMasteryStatus(question)", HTML)
        self.assertIn("typeof question.mastered === 'boolean'", HTML)
        self.assertIn("async function toggleWrongQuestionMastery(questionId)", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/exams/\$\{item\.exam_id\}/wrong-questions/\$\{questionNumber\}/mastery\?\$\{params\.toString\(\)\}`",
        )
        self.assertIn("标记已掌握", HTML)
        self.assertIn("重新复习", HTML)

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

    def test_history_keeps_the_server_synced_review_process_separate_from_mastery(self):
        self.assertIn("整卷复习流程", HTML)
        self.assertNotIn("三步掌握进度", HTML)
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
        self.assertIn("function normalizeQuestionMasterySummary(value)", HTML)
        self.assertIn("function recordQuestionMasterySummary(record)", HTML)
        self.assertIn("function refreshHistoryQuestionMasteryFromBank(", HTML)
        self.assertIn("function recordMasteryStatus(record)", HTML)
        self.assertIn("function setMasteryFilter(status)", HTML)
        self.assertIn("function updateMasteryFilterCounts(records)", HTML)
        self.assertIn("questionMastery.pending === 0", HTML)
        self.assertIn("currentMasteryFilter !== 'all'", HTML)
        self.assertIn("本筛选范围内的错题都已逐题掌握", HTML)

    def test_parent_dashboard_turns_pending_records_into_actionable_review_tasks(self):
        self.assertIn("今日复习清单", HTML)
        self.assertIn("pendingTasks: pendingTasks", HTML)
        self.assertIn("todayTasks.slice(0, 3)", HTML)
        self.assertIn("function openReviewTask(id)", HTML)
        self.assertIn("继续复习", HTML)
        self.assertIn("setMasteryFilter('pending')", HTML)

    def test_parent_dashboard_respects_spaced_review_due_dates(self):
        self.assertIn("function normalizeReviewSchedule", HTML)
        self.assertIn("function reviewTaskTiming", HTML)
        self.assertIn("建议优先", HTML)
        self.assertIn("今天完成", HTML)
        self.assertIn("明天回测", HTML)
        self.assertIn("todayTasks", HTML)
        self.assertIn("upcomingTasks", HTML)
        self.assertIn("reviewSchedule: normalizeReviewSchedule(exam.review_schedule)", HTML)
        self.assertIn("REVIEW_STEP_DEFINITIONS.slice(0, stepIndex + 1)", HTML)
        self.assertIn("const retestLocked", HTML)
        self.assertIn("到期后自动开放", HTML)

    def test_parent_dashboard_uses_question_mastery_for_knowledge_tasks(self):
        self.assertIn("function buildKnowledgeReviewTasks()", HTML)
        self.assertIn("wrongQuestionBank.loaded", HTML)
        self.assertIn("wrongQuestionMasteryStatus(question) === 'pending'", HTML)
        self.assertIn("sourceExamCount", HTML)
        self.assertIn("待复习错题", HTML)
        self.assertIn("function openKnowledgeReviewTask(subject, knowledgePoint)", HTML)
        self.assertIn("data-knowledge-point=", HTML)
        self.assertIn("查看错题", HTML)

    def test_parent_can_export_a_protected_seven_day_review_report(self):
        self.assertIn("function exportFamilyReviewReport()", HTML)
        self.assertIn("/family-review-report?${params.toString()}", HTML)
        self.assertIn("headers: familyAccessHeaders()", HTML)
        self.assertIn("URL.createObjectURL(await response.blob())", HTML)
        self.assertIn("导出近 7 天报告", HTML)
        self.assertIn("let familyReportExporting = false", HTML)

    def test_wrong_bank_records_are_not_persisted_in_browser_storage(self):
        self.assertIn("const LEGACY_HISTORY_STORAGE_KEY = 'xiahunao_history'", HTML)
        self.assertIn("localStorage.removeItem(LEGACY_HISTORY_STORAGE_KEY)", HTML)
        self.assertIn("let historyRecords = []", HTML)
        self.assertNotIn("localStorage.getItem('xiahunao_history'", HTML)
        self.assertNotIn("localStorage.setItem('xiahunao_history'", HTML)

    def test_wrong_bank_query_replaces_records_from_another_student(self):
        self.assertIn(
            "record.grade === grade && record.name === studentName",
            HTML,
        )
        self.assertIn("错题内容仅在验证访问码后显示", HTML)


if __name__ == "__main__":
    unittest.main()
