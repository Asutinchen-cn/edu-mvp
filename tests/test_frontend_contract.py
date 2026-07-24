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
        self.assertIn("worksheetMeta?.verified_on", HTML)
        self.assertIn("worksheetMeta?.catalog_status_note", HTML)
        self.assertIn("目录最近核验", HTML)
        self.assertGreaterEqual(len(re.findall(r"renderWorksheetSource\(\)", HTML)), 2)

    def test_worksheet_keeps_verified_source_details_compact_by_default(self):
        details_tag = re.search(
            r'<details class="curriculum-source-details" id="worksheetSourceDetails"[^>]*>',
            HTML,
        )
        self.assertIsNotNone(details_tag)
        self.assertNotIn(" open", details_tag.group(0))
        self.assertIn('id="worksheetSourceSummary"', HTML)
        self.assertIn('id="worksheetSourceVerification"', HTML)
        self.assertIn("目录核验 ${verifiedOn}", HTML)
        self.assertIn("当前共 ${units.length} 个单元", HTML)
        self.assertIn("sourceDetails.dataset.autoOpened", HTML)
        self.assertIn("sourceDetails.open = true", HTML)
        self.assertIn("delete sourceDetails.dataset.autoOpened", HTML)

    def test_worksheet_catalog_recovers_without_reloading_the_page(self):
        self.assertIn("const WORKSHEET_CATALOG_RETRY_DELAYS", HTML)
        self.assertIn("for (const delay of WORKSHEET_CATALOG_RETRY_DELAYS)", HTML)
        self.assertIn("if (!resp.ok)", HTML)
        self.assertIn("if (!Array.isArray(data.units) || !data.units.length)", HTML)
        self.assertIn('onclick="loadWorksheetUnits()"', HTML)
        self.assertIn("重新加载教材目录", HTML)
        self.assertIn("请通过线上网址打开本网站", HTML)
        self.assertNotIn("教材目录加载失败，请刷新页面后重试", HTML)

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

    def test_worksheet_generation_has_recoverable_inline_status(self):
        self.assertIn(
            'id="worksheetStatus" role="status" aria-live="polite" hidden',
            HTML,
        )
        self.assertIn("function setWorksheetStatus(type, message)", HTML)
        self.assertIn("function setWorksheetFormBusy(busy)", HTML)
        self.assertIn("正在根据考点组卷并生成两份 PDF", HTML)
        self.assertIn("document.getElementById('worksheetDownloads').innerHTML = ''", HTML)
        self.assertIn("document.getElementById('worksheetPreview').innerHTML = ''", HTML)
        self.assertIn("setWorksheetStatus('success'", HTML)
        self.assertIn("setWorksheetStatus('error'", HTML)
        self.assertNotIn("alert('生成复习卷失败：' + e.message)", HTML)

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

    def test_upload_form_explains_and_links_to_family_data_controls(self):
        self.assertIn('<details class="family-data-note">', HTML)
        self.assertIn("孩子试卷会怎么保存？", HTML)
        self.assertIn("访问码只保存不可还原的校验值", HTML)
        self.assertIn("删除时原卷和分析结果会一并移除", HTML)
        self.assertIn('onclick="openWrongBankQuery()">管理或删除错题</button>', HTML)

    def test_returning_parent_can_query_wrong_bank_without_scrolling_to_upload_form(self):
        self.assertIn('onclick="goToTodayReview()">查看今日复习</button>', HTML)
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
        self.assertIn("setHistorySyncStatus('', '')", HTML)
        self.assertIn("firstEmptyField.focus();", HTML)
        self.assertIn("await setHistoryView('exams');", HTML)
        self.assertNotIn("window.setTimeout(() => firstEmptyField.focus()", HTML)

    def test_wrong_bank_remember_profile_stays_inside_the_dialog(self):
        self.assertIn('.wrong-bank-field input:not([type="checkbox"])', HTML)
        self.assertNotIn(".wrong-bank-field input {", HTML)
        self.assertIn(".wrong-bank-field > .remember-profile { width: 100%; }", HTML)
        self.assertIn(
            ".wrong-bank-field > .remember-profile span { min-width: 0; overflow-wrap: anywhere; }",
            HTML,
        )

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
        self.assertIn(
            "setAnalysisStatus('error', '请填写学生姓名，之后查询家庭错题库需要使用同一姓名。')",
            HTML,
        )
        self.assertNotIn("alert('请填写学生姓名，之后查询家庭错题库需要使用同一姓名')", HTML)
        self.assertNotIn("document.getElementById('studentName').value || '同学'", HTML)

    def test_exam_upload_has_recoverable_inline_status(self):
        self.assertIn(
            'id="analysisStatus" role="status" aria-live="polite" hidden',
            HTML,
        )
        self.assertRegex(
            HTML,
            r'id="analyzeBtn"[^>]*disabled[^>]*aria-busy="false"',
        )
        self.assertIn("function setAnalysisStatus(type, message)", HTML)
        self.assertIn("function setAnalysisBusy(busy)", HTML)
        self.assertIn("btn.disabled = analysisBusy || uploadedFiles.length === 0", HTML)
        self.assertIn("setAnalysisStatus('loading'", HTML)
        self.assertIn("setAnalysisStatus('success'", HTML)
        self.assertIn("setAnalysisStatus('error'", HTML)
        self.assertNotIn("alert('上传出错：' + e.message)", HTML)
        for message in (
            "一份试卷最多上传 12 页",
            "仅支持 JPG、PNG 或 PDF 文件",
            "文件大小不能超过 10MB",
            "多页试卷总大小不能超过 50MB",
        ):
            self.assertNotIn(f"alert('{message}')", HTML)

    def test_clear_subject_mismatch_switches_subject_and_keeps_files_for_retry(self):
        self.assertIn("error.code = json.code || ''", HTML)
        self.assertIn("error.detectedSubject = json.detected_subject || ''", HTML)
        self.assertIn("if (e.code === 'subject_mismatch'", HTML)
        self.assertIn("document.getElementById('analysisSubject').value = e.detectedSubject", HTML)
        self.assertIn("已为你切换到", HTML)
        self.assertIn("已选文件仍保留", HTML)

    def test_upload_access_code_has_a_full_width_row_on_larger_screens(self):
        self.assertRegex(
            HTML,
            r"\.form-row\s*\{[^}]*display:\s*grid;[^}]*"
            r"grid-template-columns:\s*minmax\(0,\s*0\.8fr\)\s+"
            r"minmax\(0,\s*0\.8fr\)\s+minmax\(0,\s*1\.4fr\)",
        )
        self.assertIn('<div class="form-group family-access-group">', HTML)
        self.assertIn(".family-access-group { grid-column: 1 / -1; }", HTML)

        tablet_css = re.search(
            r"@media \(min-width: 769px\) and \(max-width: 1080px\) \{(?P<body>.*?)\n        \}",
            HTML,
            re.S,
        )
        self.assertIsNotNone(tablet_css)
        self.assertRegex(tablet_css.group("body"), r"\.steps-sidebar\s*\{[^}]*display:\s*none")

    def test_mobile_layout_prioritizes_the_real_upload_tool(self):
        mobile_css = re.search(r"@media \(max-width: 768px\) \{(?P<body>.*?)\n        \}", HTML, re.S)
        self.assertIsNotNone(mobile_css)
        css = mobile_css.group("body")
        self.assertRegex(css, r"\.hero-card\s*\{[^}]*display:\s*none")
        self.assertRegex(css, r"\.steps-sidebar\s*\{[^}]*display:\s*none")
        self.assertRegex(css, r"\.hero-actions\s*\{[^}]*grid-template-columns:\s*repeat\(2,")
        self.assertRegex(css, r"\.main-card\s*\{[^}]*margin:\s*10px 12px")

    def test_mobile_quick_nav_keeps_core_parent_actions_reachable(self):
        self.assertIn('<nav class="mobile-quick-nav" aria-label="手机快捷操作">', HTML)
        self.assertIn('<a href="#analysis"', HTML)
        self.assertIn('onclick="goToTodayReview()"', HTML)
        self.assertIn('<a href="#worksheet"', HTML)
        self.assertIn("function goToTodayReview()", HTML)
        self.assertIn("!wrongQuestionBank.loaded && historyRecords.length === 0", HTML)
        self.assertIn("openWrongBankQuery()", HTML)
        self.assertIn("document.getElementById('history').scrollIntoView", HTML)
        self.assertRegex(HTML, r"\.mobile-quick-nav\s*\{[^}]*display:\s*none")

        today_review = re.search(
            r"function goToTodayReview\(\) \{(?P<body>.*?)\n\}",
            HTML,
            re.S,
        )
        self.assertIsNotNone(today_review)
        today_review_body = today_review.group("body")
        self.assertIn("setHistoryFilter('all')", today_review_body)
        self.assertIn("currentSubjectArchive = 'all'", today_review_body)
        self.assertIn("currentMasteryFilter = 'pending'", today_review_body)
        self.assertIn("renderHistory()", today_review_body)

        mobile_css = re.search(r"@media \(max-width: 768px\) \{(?P<body>.*?)\n        \}", HTML, re.S)
        self.assertIsNotNone(mobile_css)
        css = mobile_css.group("body")
        self.assertRegex(css, r"body\s*\{[^}]*padding-bottom:")
        self.assertRegex(css, r"\.mobile-quick-nav\s*\{[^}]*display:\s*grid")

    def test_family_access_code_has_safe_visibility_and_generation_helpers(self):
        self.assertIn("function toggleFamilyCodeVisibility", HTML)
        self.assertIn("function generateFamilyAccessCode", HTML)
        self.assertIn("crypto.getRandomValues", HTML)
        self.assertIn('aria-label="显示家庭访问码"', HTML)
        self.assertIn('aria-label="生成家庭访问码"', HTML)
        self.assertNotIn("localStorage.setItem('familyAccessCode'", HTML)

    def test_family_access_code_can_be_copied_without_browser_persistence(self):
        self.assertIn('aria-label="复制家庭访问码"', HTML)
        self.assertIn("onclick=\"copyFamilyAccessCode('familyAccessCode', this)\"", HTML)
        self.assertIn("async function copyFamilyAccessCode(inputId, button)", HTML)
        self.assertIn("navigator.clipboard.writeText(familyCode)", HTML)
        self.assertIn("document.execCommand('copy')", HTML)
        self.assertIn("访问码已复制，请妥善保存", HTML)
        self.assertIn('id="familyAccessHint" role="status" aria-live="polite"', HTML)
        self.assertNotRegex(
            HTML,
            r"localStorage\.setItem\([^\n]*(familyAccessCode|family_code|familyCode)",
        )

    def test_original_exam_files_use_the_protected_image_endpoint(self):
        self.assertIn("async function openProtectedExamImage(id)", HTML)
        self.assertIn("/image?${params.toString()}", HTML)
        self.assertIn("params.set('page', String(pageNumber))", HTML)
        self.assertIn("headers: accessHeaders", HTML)
        self.assertIn("record.imageCount", HTML)
        self.assertIn("查看原卷（", HTML)
        self.assertNotIn("function safeUploadUrl", HTML)
        self.assertNotIn("href=\"${escapeHtml(imageUrl)}\"", HTML)

    def test_original_exam_image_failure_is_recoverable_in_history(self):
        self.assertIn("imageOpening: false", HTML)
        self.assertRegex(HTML, r"record\.imageOpening\s*\?\s*'正在读取原卷\.\.\.'")
        self.assertIn("record.imageOpening = true", HTML)
        self.assertIn("record.imageOpening = false", HTML)
        self.assertIn("读取原卷失败：", HTML)
        self.assertIn("原记录仍保留，可以重试", HTML)
        image_handler = re.search(
            r"async function openProtectedExamImage\(id\)(?P<body>.*?)"
            r"\nasync function exportCorrectionSheet",
            HTML,
            re.S,
        )
        self.assertIsNotNone(image_handler)
        self.assertNotIn("alert(", image_handler.group("body"))

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

    def test_retry_analysis_failure_stays_visible_on_the_saved_record(self):
        self.assertIn("function renderPendingAnalysisState(record)", HTML)
        self.assertIn("正在重新分析已保存的原卷", HTML)
        self.assertIn("上次重新分析未完成", HTML)
        self.assertIn("原卷仍安全保存在错题库", HTML)
        self.assertIn('role="status" aria-live="polite"', HTML)
        self.assertIn("function setHistorySyncStatus(type, message)", HTML)
        self.assertIn("setHistorySyncStatus('error'", HTML)
        self.assertIn("record.analysisError = error.message", HTML)
        self.assertNotIn(
            "alert('重新分析失败：' + record.analysisError + '。原卷仍已保存，可以稍后再试。')",
            HTML,
        )

    def test_server_record_deletion_explains_that_originals_are_removed(self):
        self.assertIn("原卷文件和分析结果将一并删除，且无法恢复", HTML)
        self.assertIn('id="confirmStatus" role="alert" aria-live="assertive"', HTML)
        self.assertIn("let deleteSaving = false", HTML)
        self.assertIn("正在删除...", HTML)
        self.assertIn("原记录仍保留，可以重试", HTML)
        self.assertNotIn("alert('删除服务器记录失败：' + e.message)", HTML)

    def test_analysis_result_gives_parents_an_evidence_based_action_plan(self):
        self.assertIn("function buildParentReviewPlan(data)", HTML)
        self.assertIn("7 天复习安排", HTML)
        self.assertIn("本次识别错题", HTML)
        self.assertIn('id="summaryGenerateBtn"', HTML)
        self.assertIn("function startPracticeFromSummary()", HTML)
        self.assertIn("function setPracticeGenerationState", HTML)
        self.assertIn(".parent-plan-header { flex-direction: column; }", HTML)
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
        self.assertIn("let practiceMasteryError = ''", HTML)
        self.assertIn("本轮练习结果仍保留", HTML)
        self.assertNotIn("alert('同步掌握状态失败：' + error.message)", HTML)

    def test_history_has_an_evidence_based_parent_dashboard(self):
        self.assertIn('id="reviewDashboard"', HTML)
        self.assertIn("function buildReviewDashboard(records)", HTML)
        self.assertIn("function renderReviewDashboard(records)", HTML)
        self.assertIn("function normalizeWrongCount(value)", HTML)
        self.assertIn("value === null || value === undefined || value === ''", HTML)
        self.assertIn("数据来自服务器保存的试卷与逐题复习状态，不代表考试成绩", HTML)
        self.assertNotIn("进步率", HTML)

    def test_unqueried_wrong_bank_is_not_presented_as_zero_history(self):
        self.assertIn(
            "if (!wrongQuestionBank.loaded && historyRecords.length === 0)",
            HTML,
        )
        self.assertIn("当前尚未读取服务器错题库", HTML)
        self.assertIn("空白不代表没有历史记录", HTML)
        self.assertIn("输入访问码查看今日复习", HTML)
        self.assertIn("尚未查询家庭错题库", HTML)

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

    def test_knowledge_view_total_count_is_not_double_counted(self):
        count_updater = re.search(
            r"const subjectCounts = datedQuestions\.reduce\(\(counts, item\) => "
            r"\{(?P<body>.*?)"
            r"\}, \{ all: 0, math: 0, english: 0 \}\);",
            HTML,
            re.S,
        )
        self.assertIsNotNone(count_updater)
        self.assertEqual(count_updater.group("body").count("counts.all += 1;"), 1)

    def test_knowledge_source_record_failure_is_recoverable_inline(self):
        self.assertIn("let sourceExamLoadingId = null", HTML)
        self.assertIn("sourceExamLoadingId === Number(item.exam_id)", HTML)
        self.assertIn("正在加载...", HTML)
        self.assertIn("sourceExamLoadingId = Number(examId)", HTML)
        self.assertIn("sourceExamLoadingId = null", HTML)
        self.assertIn("加载原试卷记录失败：", HTML)
        self.assertIn("错题仍保留，可以重试", HTML)
        source_handler = re.search(
            r"async function openQuestionSourceExam\(examId\)(?P<body>.*?)"
            r"\nfunction renderHistory\(\)",
            HTML,
            re.S,
        )
        self.assertIsNotNone(source_handler)
        self.assertNotIn("alert(", source_handler.group("body"))

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
        self.assertIn("原复习状态未改变，请重试", HTML)
        self.assertNotIn("alert('保存单题状态失败：' + error.message)", HTML)

    def test_history_can_export_a_protected_correction_sheet(self):
        self.assertIn("function exportCorrectionSheet(id)", HTML)
        self.assertIn("/correction-sheet?${params.toString()}", HTML)
        self.assertIn("headers: familyAccessHeaders()", HTML)
        self.assertIn("URL.createObjectURL(await response.blob())", HTML)
        self.assertIn("导出订正单", HTML)
        self.assertIn("correctionExporting: false", HTML)
        self.assertIn("订正单导出失败", HTML)
        self.assertIn("订正单下载已开始", HTML)
        self.assertNotIn("alert(e.message || '导出订正单失败，请稍后重试')", HTML)

    def test_practice_generation_uses_the_saved_exam_endpoint(self):
        self.assertIn("const examId = currentAnalysisData.examIds?.[0]", HTML)
        self.assertRegex(
            HTML,
            r"requestJson\(`/generate-practice/\$\{examId\}\?\$\{params\.toString\(\)\}`",
        )
        self.assertNotIn("fetch('/generate-practice'", HTML)

    def test_practice_generation_failure_does_not_create_a_fake_exportable_question(self):
        self.assertIn(
            'id="practiceGenerationStatus" role="status" aria-live="polite" hidden',
            HTML,
        )
        self.assertIn("function setPracticeGenerationStatus(type, message)", HTML)
        self.assertIn("const hadExistingPractice = currentPracticeQuestions.length > 0", HTML)
        self.assertIn("上一轮练习和作答结果仍保留，可以重试", HTML)
        self.assertIn("没有生成可用题目，未提供 PDF 下载，可以重试", HTML)
        self.assertIn(
            "exportButton.style.display = hadExistingPractice ? 'inline-block' : 'none'",
            HTML,
        )
        self.assertNotIn("巩固题暂时没有生成成功，请先根据上方薄弱点完成原题订正", HTML)

    def test_practice_state_is_isolated_between_analysis_contexts(self):
        self.assertIn("let activePracticeContextKey = ''", HTML)
        self.assertIn("let practiceGenerationRequestId = 0", HTML)
        self.assertIn("function buildPracticeContextKey(data)", HTML)
        self.assertIn("function resetPracticeExperience()", HTML)
        self.assertIn("function syncPracticeContext(data)", HTML)
        self.assertIn("function isPracticeGenerationRequestCurrent(requestId, contextKey)", HTML)
        self.assertIn("syncPracticeContext(data);", HTML)
        self.assertIn("studentName: String(data?.studentName || '')", HTML)
        self.assertIn("examIds: [...new Set", HTML)
        self.assertIn("practiceKnowledgePoint: String(data?.practiceKnowledgePoint", HTML)
        self.assertIn("currentPracticeQuestions = []", HTML)
        self.assertIn("currentPracticeResults = []", HTML)
        self.assertIn("practiceGenerationRequestId += 1", HTML)
        self.assertIn("const requestId = ++practiceGenerationRequestId", HTML)
        self.assertIn("const requestContextKey = activePracticeContextKey", HTML)
        self.assertIn("if (!isPracticeGenerationRequestCurrent(requestId, requestContextKey)) return", HTML)
        self.assertIn("exportButton.style.display = 'none'", HTML)

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
        self.assertIn("原进度未改变，请重试", HTML)
        self.assertNotIn("alert('保存复习进度失败：' + e.message)", HTML)

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
        self.assertIn("近 7 天报告导出失败", HTML)
        self.assertIn("近 7 天复习报告下载已开始", HTML)
        self.assertNotIn("alert(e.message || '导出近 7 天报告失败，请稍后重试')", HTML)

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
