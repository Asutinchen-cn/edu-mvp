from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
import io
import httpx
import base64
from datetime import datetime
from urllib.parse import quote

# 数据库配置 - Railway 使用 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-9f2b01275a904d40badccff22ae2db09")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 百度 OCR 配置
BAIDU_OCR_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "DIEUO1gvv10PryVLdMqVnTsJ")
BAIDU_OCR_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "vMvvJqBwdvBNOP25yWq9mDBuKYQvA96U")

# 数据模型
class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    grade = Column(String(50), index=True, nullable=False, default="未分类")
    student_name = Column(String(100), index=True)
    image_path = Column(Text)
    ocr_text = Column(Text)
    ai_analysis = Column(Text)
    weak_points = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建表
Base.metadata.create_all(bind=engine)

# 兼容旧库：若已有 exams 表但无 grade 字段，启动时自动补列
try:
    inspector = inspect(engine)
    if inspector.has_table("exams"):
        cols = {c["name"] for c in inspector.get_columns("exams")}
        if "grade" not in cols:
            with engine.begin() as conn:
                if "postgresql" in DATABASE_URL:
                    conn.execute(text("ALTER TABLE exams ADD COLUMN IF NOT EXISTS grade VARCHAR(50)"))
                    conn.execute(text("UPDATE exams SET grade = '未分类' WHERE grade IS NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_grade ON exams (grade)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_student_name ON exams (student_name)"))
                else:
                    conn.execute(text("ALTER TABLE exams ADD COLUMN grade VARCHAR(50)"))
                    conn.execute(text("UPDATE exams SET grade = '未分类' WHERE grade IS NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_grade ON exams (grade)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_student_name ON exams (student_name)"))
except Exception as _e:
    print(f"DB migration warning: {_e}")

app = FastAPI(title="虾胡闹教育 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== 百度 OCR =====

_baidu_token = {"access_token": None, "expires_at": 0}

async def get_baidu_access_token() -> str:
    """获取百度 OCR access_token（带缓存）"""
    import time
    now = time.time()
    if _baidu_token["access_token"] and _baidu_token["expires_at"] > now:
        return _baidu_token["access_token"]
    
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_OCR_API_KEY,
        "client_secret": BAIDU_OCR_SECRET_KEY
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params)
        data = resp.json()
        _baidu_token["access_token"] = data.get("access_token")
        _baidu_token["expires_at"] = now + data.get("expires_in", 2592000) - 60
        return _baidu_token["access_token"]

async def baidu_ocr(image_bytes: bytes) -> str:
    """调用百度 OCR 识别试卷（优先试卷专用接口）"""
    try:
        token = await get_baidu_access_token()
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # 1. 试卷分析与识别（专用接口）
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://aip.baidubce.com/rest/2.0/ocr/v1/doc_analysis",
                    params={"access_token": token},
                    data={
                        "image": img_b64,
                        "language_type": "CHN_ENG"
                    }
                )
                data = resp.json()
                text = _extract_ocr_text(data)
                if text:
                    return text
        except Exception as e:
            print(f"Doc analysis OCR error: {e}")
        
        # 2. 高精度通用文字识别
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic",
                    params={"access_token": token},
                    data={"image": img_b64, "language_type": "CHN_ENG"}
                )
                data = resp.json()
                text = _extract_ocr_text(data)
                if text:
                    return text
        except Exception as e:
            print(f"Accurate OCR error: {e}")
        
        # 3. 标准通用文字识别
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic",
                    params={"access_token": token},
                    data={"image": img_b64, "language_type": "CHN_ENG"}
                )
                data = resp.json()
                text = _extract_ocr_text(data)
                if text:
                    return text
        except Exception as e:
            print(f"General OCR error: {e}")
        
        return "[OCR识别失败，未提取到文字内容]"
        
    except Exception as e:
        print(f"Baidu OCR error: {e}")
        return f"[OCR服务异常] {str(e)[:50]}，请稍后重试"


def _extract_ocr_text(data: dict) -> str:
    """从百度OCR各种接口返回中提取文字，兼容不同格式"""
    if not isinstance(data, dict):
        return ""
    
    # 检查错误
    if "error_code" in data:
        print(f"OCR error: {data.get('error_code')} - {data.get('error_msg')}")
        return ""
    
    # 格式1：试卷分析接口 - results 数组
    if "results" in data and isinstance(data["results"], list):
        lines = []
        for item in data["results"]:
            if isinstance(item, dict):
                words = item.get("words", "")
                if isinstance(words, str) and words.strip():
                    q_type = item.get("type", "")
                    if q_type == "question":
                        lines.append(f"【题目】{words.strip()}")
                    elif q_type == "answer":
                        lines.append(f"【作答】{words.strip()}")
                    elif q_type == "handwriting":
                        lines.append(f"【手写】{words.strip()}")
                    else:
                        lines.append(words.strip())
            elif isinstance(item, str) and item.strip():
                lines.append(item.strip())
        if lines:
            return "\n".join(lines)
    
    # 格式2：通用/高精度接口 - words_result 数组
    if "words_result" in data and isinstance(data["words_result"], list):
        lines = []
        for item in data["words_result"]:
            if isinstance(item, dict):
                words = item.get("words", "")
                if isinstance(words, str) and words.strip():
                    lines.append(words.strip())
            elif isinstance(item, str) and item.strip():
                lines.append(item.strip())
        if lines:
            return "\n".join(lines)
    
    return ""

# ===== DeepSeek API 调用 =====

async def call_deepseek(prompt: str, temperature: float = 0.3) -> str:
    """调用 DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 2000
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

# ===== AI 分析（DeepSeek） =====

async def ai_analyze(ocr_text: str) -> dict:
    """使用 DeepSeek 进行错题分析"""
    prompt = f"""你是一位资深教育分析专家。请根据以下试卷内容，进行详细的错题分析。

试卷OCR识别内容：
{ocr_text}

请按以下JSON格式返回分析结果（不要包含其他文字，只返回JSON）：
{{
    "error_types": ["错误类型1", "错误类型2"],
    "weak_points": ["薄弱知识点1", "薄弱知识点2"],
    "root_cause": "根本原因分析",
    "recommendations": [
        "针对性建议1",
        "针对性建议2",
        "针对性建议3"
    ]
}}"""

    try:
        result = await call_deepseek(prompt)
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1])
        analysis = json.loads(result)
        analysis.setdefault("error_types", [])
        analysis.setdefault("weak_points", [])
        analysis.setdefault("root_cause", "")
        analysis.setdefault("recommendations", [])
        return analysis
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return {
            "error_types": ["分析服务暂时不可用"],
            "weak_points": ["请稍后重试"],
            "root_cause": f"AI分析服务异常: {str(e)[:50]}",
            "recommendations": ["请稍后重试AI分析"]
        }

# ===== AI 生成巩固练习题（DeepSeek） =====

async def ai_generate_questions(weak_points: list) -> list:
    """使用 DeepSeek 根据薄弱知识点动态生成练习题"""
    prompt = f"""你是一位经验丰富的出题老师。请根据以下薄弱知识点，生成5道针对性的巩固练习题。

薄弱知识点：{', '.join(weak_points)}

要求：
1. 题目要有针对性，围绕薄弱知识点出题
2. 包含选择题（2-3道）和填空题（2-3道）
3. 难度适中，由易到难
4. 每道题都要有提示和答案

请按以下JSON格式返回（不要包含其他文字，只返回JSON数组）：
[
    {{
        "id": 1,
        "type": "选择题",
        "question": "题目内容",
        "options": ["A选项", "B选项", "C选项", "D选项"],
        "answer": "A",
        "hint": "解题提示"
    }},
    {{
        "id": 2,
        "type": "填空题",
        "question": "题目内容",
        "answer": "答案",
        "hint": "解题提示"
    }}
]"""

    try:
        result = await call_deepseek(prompt, temperature=0.7)
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1])
        questions = json.loads(result)
        for i, q in enumerate(questions):
            q.setdefault("id", i + 1)
        return questions[:5]
    except Exception as e:
        print(f"DeepSeek generate error: {e}")
        return [{
            "id": 1,
            "type": "提示",
            "question": "AI出题服务暂时不可用，请稍后重试",
            "answer": "",
            "hint": str(e)[:50]
        }]

# ===== API 路由 =====

@app.post("/upload")
async def upload_exam(
    student_name: str = Form(...),
    grade: str = Form(...),
    file: UploadFile = File(...)
):
    """上传试卷图片（按 年级 + 学生名 隔离）"""
    try:
        db = SessionLocal()

        student_name = (student_name or "").strip()
        grade = (grade or "").strip()
        if not student_name:
            db.close()
            return JSONResponse({"success": False, "error": "student_name 不能为空"}, status_code=400)
        if not grade:
            db.close()
            return JSONResponse({"success": False, "error": "grade 不能为空"}, status_code=400)

        # 读取文件内容
        content = await file.read()

        # 百度 OCR 识别
        ocr_result = await baidu_ocr(content)

        # 创建记录
        exam = Exam(
            grade=grade,
            student_name=student_name,
            image_path=file.filename,
            ocr_text=ocr_result
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)
        db.close()

        return JSONResponse({
            "success": True,
            "id": exam.id,
            "message": "上传成功",
            "grade": grade,
            "student": student_name,
            "ocr_preview": ocr_result[:200] + "..." if len(ocr_result) > 200 else ocr_result,
            "next_step": f"POST /analyze/{exam.id}?grade={grade}&student_name={student_name} 进行AI分析"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/analyze/{exam_id}")
async def analyze_exam(exam_id: int, grade: str = None, student_name: str = None):
    """AI分析错题（DeepSeek，按 年级 + 学生名 校验）"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()

        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)

        # 双字段隔离校验：仅允许操作当前年级+学生的记录
        if grade and (exam.grade or "").strip() != grade.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（年级不匹配）"}, status_code=403)
        if student_name and (exam.student_name or "").strip() != student_name.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（学生姓名不匹配）"}, status_code=403)

        # 调用 DeepSeek AI 分析
        analysis = await ai_analyze(exam.ocr_text)

        # 更新记录
        exam.ai_analysis = json.dumps(analysis, ensure_ascii=False)
        exam.weak_points = json.dumps(analysis.get("weak_points", []), ensure_ascii=False)
        exam.recommendations = json.dumps(analysis.get("recommendations", []), ensure_ascii=False)
        db.commit()
        db.close()

        return JSONResponse({
            "success": True,
            "exam_id": exam_id,
            "grade": exam.grade,
            "student": exam.student_name,
            "analysis": analysis,
            "summary": {
                "weak_points": analysis.get("weak_points", []),
                "recommendations": analysis.get("recommendations", [])[:3]
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/exams")
async def list_exams(grade: str = None, student_name: str = None, limit: int = 10):
    """获取最近上传的试卷列表（必须 年级 + 学生名 同时提供）"""
    grade = (grade or "").strip()
    student_name = (student_name or "").strip()

    # 按产品需求：只有年级不展示任何历史，必须双字段同时存在
    if not grade or not student_name:
        return JSONResponse({"exams": []})

    db = SessionLocal()
    exams = (
        db.query(Exam)
        .filter(Exam.grade == grade, Exam.student_name == student_name)
        .order_by(Exam.created_at.desc())
        .limit(limit)
        .all()
    )
    db.close()

    return JSONResponse({
        "exams": [{
            "id": e.id,
            "grade": e.grade,
            "student": e.student_name,
            "image": e.image_path,
            "ocr_preview": e.ocr_text[:50] + "..." if e.ocr_text else None,
            "weak_points": json.loads(e.weak_points) if e.weak_points else None,
            "created": e.created_at.isoformat() if e.created_at else None
        } for e in exams]
    })

@app.get("/exams/{exam_id}")
async def get_exam(exam_id: int, grade: str = None, student_name: str = None):
    """获取单个试卷详情（支持按 年级 + 学生名 校验）"""
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    db.close()

    if not exam:
        return JSONResponse({"error": "试卷不存在"}, status_code=404)

    if grade and (exam.grade or "").strip() != grade.strip():
        return JSONResponse({"error": "无权限访问该记录（年级不匹配）"}, status_code=403)
    if student_name and (exam.student_name or "").strip() != student_name.strip():
        return JSONResponse({"error": "无权限访问该记录（学生姓名不匹配）"}, status_code=403)

    return JSONResponse({
        "id": exam.id,
        "grade": exam.grade,
        "student": exam.student_name,
        "image": exam.image_path,
        "ocr_text": exam.ocr_text,
        "ai_analysis": json.loads(exam.ai_analysis) if exam.ai_analysis else None,
        "weak_points": json.loads(exam.weak_points) if exam.weak_points else None,
        "recommendations": json.loads(exam.recommendations) if exam.recommendations else None,
        "created": exam.created_at.isoformat() if exam.created_at else None
    })

@app.delete("/exams/{exam_id}")
async def delete_exam(exam_id: int, grade: str = None, student_name: str = None):
    """删除试卷（支持按 年级 + 学生名 校验）"""
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        db.close()
        return JSONResponse({"success": False, "error": "试卷不存在"}, status_code=404)

    if grade and (exam.grade or "").strip() != grade.strip():
        db.close()
        return JSONResponse({"success": False, "error": "无权限删除该记录（年级不匹配）"}, status_code=403)
    if student_name and (exam.student_name or "").strip() != student_name.strip():
        db.close()
        return JSONResponse({"success": False, "error": "无权限删除该记录（学生姓名不匹配）"}, status_code=403)

    db.delete(exam)
    db.commit()
    db.close()
    return JSONResponse({"success": True, "message": "已删除"})

@app.get("/")
async def root():
    """返回前端页面"""
    # 尝试多个可能的路径，兼容本地开发和 Railway 部署
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "..", "web", "index.html"),
        os.path.join(base_dir, "web", "index.html"),
        os.path.join(base_dir, "static", "index.html"),
    ]
    for web_path in possible_paths:
        abs_path = os.path.normpath(web_path)
        if os.path.exists(abs_path):
            return FileResponse(abs_path)
    return JSONResponse({"message": "虾胡闹教育 API运行中，前端文件未找到", "searched_paths": [os.path.normpath(p) for p in possible_paths]})

@app.post("/generate-practice/{exam_id}")
async def generate_practice(exam_id: int, grade: str = None, student_name: str = None):
    """根据薄弱知识点生成5道巩固练习题（DeepSeek AI 生成）"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()

        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)

        if grade and (exam.grade or "").strip() != grade.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（年级不匹配）"}, status_code=403)
        if student_name and (exam.student_name or "").strip() != student_name.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（学生姓名不匹配）"}, status_code=403)

        # 获取薄弱知识点
        weak_points = json.loads(exam.weak_points) if exam.weak_points else []

        if not weak_points:
            db.close()
            return JSONResponse({"error": "请先进行AI分析"}, status_code=400)

        # 调用 DeepSeek AI 生成练习题
        questions = await ai_generate_questions(weak_points)

        db.close()

        return JSONResponse({
            "success": True,
            "exam_id": exam_id,
            "grade": exam.grade,
            "student": exam.student_name,
            "weak_points": weak_points,
            "questions": questions,
            "total": len(questions),
            "note": "由 DeepSeek AI 动态生成"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# ===== PDF 导出 =====

def generate_practice_pdf(student_name: str, weak_points: list, questions: list) -> bytes:
    """生成巩固练习题 PDF（中文稳定版）"""
    from fpdf import FPDF

    def _clean_text(v) -> str:
        if v is None:
            return ""
        s = str(v)
        # 去掉不可见控制字符，避免排版异常
        return "".join(ch for ch in s if ch >= " " or ch in "\n\t").strip()

    def _safe_multicell(pdf_obj, text: str, h: float = 7.0):
        """更稳健的多行输出，避免 Not enough horizontal space 错误"""
        text = _clean_text(text)
        if not text:
            return

        # 每次写入前重置到左边距，避免可用宽度变成 0
        pdf_obj.set_x(pdf_obj.l_margin)
        epw = pdf_obj.w - pdf_obj.l_margin - pdf_obj.r_margin

        try:
            pdf_obj.multi_cell(epw, h, text)
            return
        except Exception as e:
            # 兜底：按固定宽度分段，避免超长连续字符串撑爆行宽
            if "Not enough horizontal space" not in str(e):
                raise

        chunk = 28
        for line in text.split("\n"):
            if not line:
                pdf_obj.multi_cell(epw, h, "")
                continue
            start = 0
            while start < len(line):
                part = line[start:start + chunk]
                pdf_obj.set_x(pdf_obj.l_margin)
                pdf_obj.multi_cell(epw, h, part)
                start += chunk

    class PracticePDF(FPDF):
        def header(self):
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, "Consolidation Practice", new_x="LMARGIN", new_y="NEXT", align="C")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PracticePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 尝试加载中文字体
    project_font = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansCJKsc-Regular.otf")
    )
    font_paths = [
        project_font,  # 项目内置中文字体（Railway可用）
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]

    chinese_font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdf.add_font("zh", "", fp)
                pdf.add_font("zh", "B", fp)
                chinese_font = "zh"
                break
            except Exception:
                continue

    font = chinese_font or "helvetica"

    # 标题
    pdf.set_font(font, "B", 18)
    _safe_multicell(pdf, "巩固练习题", h=10)
    pdf.ln(2)

    # 学生信息
    pdf.set_font(font, "", 11)
    _safe_multicell(pdf, f"学生：{_clean_text(student_name)}")

    # 薄弱知识点
    if weak_points:
        wp_text = "薄弱知识点：" + "、".join([_clean_text(x) for x in weak_points])
        pdf.set_text_color(200, 0, 0)
        _safe_multicell(pdf, wp_text)
        pdf.set_text_color(0, 0, 0)

    pdf.ln(2)

    # 题目
    for i, q in enumerate(questions):
        q_type = _clean_text(q.get("type", ""))
        q_text = _clean_text(q.get("question", ""))
        q_hint = _clean_text(q.get("hint", ""))
        q_answer = _clean_text(q.get("answer", ""))
        q_options = q.get("options", [])

        # 题号 + 类型
        pdf.set_font(font, "B", 12)
        label = f"第{i+1}题 [{q_type}]" if q_type else f"第{i+1}题"
        _safe_multicell(pdf, label, h=8)

        # 题目内容
        pdf.set_font(font, "", 11)
        _safe_multicell(pdf, q_text, h=7)

        # 选项
        if q_options:
            for j, opt in enumerate(q_options):
                opt_label = chr(65 + j)
                _safe_multicell(pdf, f"{opt_label}. {_clean_text(opt)}", h=7)

        # 提示和答案
        pdf.set_font(font, "", 9)
        pdf.set_text_color(128, 128, 128)
        if q_hint:
            _safe_multicell(pdf, f"提示：{q_hint}", h=6)
        if q_answer:
            _safe_multicell(pdf, f"答案：{q_answer}", h=6)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    return pdf.output()

@app.post("/export-practice-pdf/{exam_id}")
async def export_practice_pdf(exam_id: int, grade: str = None, student_name: str = None):
    """导出巩固练习题为 PDF"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()

        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)

        if grade and (exam.grade or "").strip() != grade.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（年级不匹配）"}, status_code=403)
        if student_name and (exam.student_name or "").strip() != student_name.strip():
            db.close()
            return JSONResponse({"error": "无权限访问该记录（学生姓名不匹配）"}, status_code=403)

        weak_points = json.loads(exam.weak_points) if exam.weak_points else []
        if not weak_points:
            db.close()
            return JSONResponse({"error": "请先进行AI分析"}, status_code=400)

        # 生成练习题
        questions = await ai_generate_questions(weak_points)
        db.close()

        # 生成 PDF
        pdf_bytes = generate_practice_pdf(exam.student_name, weak_points, questions)

        # 避免 latin-1 编码错误：使用 ASCII 安全文件名 + RFC5987 filename*
        safe_filename = f"practice_{exam_id}.pdf"
        utf8_filename = f"practice_{exam.grade}_{exam.student_name}_{exam_id}.pdf"
        content_disposition = (
            f"attachment; filename={safe_filename}; "
            f"filename*=UTF-8''{quote(utf8_filename)}"
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": content_disposition}
        )
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api-info")
async def api_info():
    """API信息"""
    return {
        "message": "🎓 虾胡闹教育 API运行中",
        "version": "0.5.0",
        "ai_provider": "DeepSeek",
        "ocr_provider": "Baidu",
        "endpoints": {
            "upload": "POST /upload (form-data: grade, student_name, file)",
            "analyze": "POST /analyze/{id}?grade=...&student_name=... - DeepSeek AI分析",
            "generate_practice": "POST /generate-practice/{id}?grade=...&student_name=... - DeepSeek AI生成5道巩固题",
            "export_pdf": "POST /export-practice-pdf/{id}?grade=...&student_name=... - 导出PDF",
            "list": "GET /exams?grade=...&student_name=...",
            "detail": "GET /exams/{id}?grade=...&student_name=...",
            "delete": "DELETE /exams/{id}?grade=...&student_name=..."
        },
        "status": "OCR已接入百度试卷识别+通用识别，AI分析已接入DeepSeek",
        "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
