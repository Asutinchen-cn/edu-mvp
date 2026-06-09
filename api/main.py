from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel, Field
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
from dotenv import load_dotenv

load_dotenv()

# 数据库配置 - Railway 使用 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

# 百度 OCR 配置
BAIDU_OCR_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
BAIDU_OCR_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")

# 五年级单元复习卷：仅保存公开教材目录范围和人工整理知识点，不保存教材原文
CURRICULUM_UNITS = [
    {
        "id": "math-5a-review",
        "subject": "math",
        "semester": "first",
        "title": "一、复习与提高",
        "knowledge_points": ["符号表示数", "小数意义与性质", "小数大小比较", "小数加减法复习"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5a-decimal-multiply-divide",
        "subject": "math",
        "semester": "first",
        "title": "二、小数乘除法",
        "knowledge_points": ["小数乘整数", "小数乘小数", "连乘乘加乘减", "小数除法", "循环小数", "积与商的近似数"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5a-statistics",
        "subject": "math",
        "semester": "first",
        "title": "三、统计",
        "knowledge_points": ["平均数", "平均数计算", "平均数应用", "数据分析"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5a-equations-1",
        "subject": "math",
        "semester": "first",
        "title": "四、简易方程（一）",
        "knowledge_points": ["用字母表示数", "化简与求值", "方程", "列方程解决问题（一）"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5a-geometry-practice",
        "subject": "math",
        "semester": "first",
        "title": "五、几何小实践",
        "knowledge_points": ["平行四边形", "平行四边形面积", "三角形面积", "梯形", "梯形面积", "组合图形面积"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5a-summary",
        "subject": "math",
        "semester": "first",
        "title": "六、整理与提高",
        "knowledge_points": ["小数四则混合运算", "小数应用", "列方程解决问题（二）", "图形面积综合", "时间的计算", "编码"],
        "source_note": "上海五年级第一学期数学（试用本）目录",
    },
    {
        "id": "math-5b-review",
        "subject": "math",
        "semester": "second",
        "title": "一、复习与提高",
        "knowledge_points": ["小数四则混合运算", "方程复习", "面积的估测（2）", "自然数"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "math-5b-positive-negative",
        "subject": "math",
        "semester": "second",
        "title": "二、正数和负数的初步认识",
        "knowledge_points": ["正数和负数", "数轴", "相反意义的量", "正负数大小比较"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "math-5b-equations-2",
        "subject": "math",
        "semester": "second",
        "title": "三、简易方程（二）",
        "knowledge_points": ["列方程解决问题（三）", "列方程解决问题（四）", "等量关系", "方程综合应用"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "math-5b-geometry-practice",
        "subject": "math",
        "semester": "second",
        "title": "四、几何小实践",
        "knowledge_points": ["体积", "体积单位", "长方体与正方体的认识", "长方体与正方体体积", "组合体体积", "表面积", "体积与容积", "体积与质量"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "math-5b-problem-solving",
        "subject": "math",
        "semester": "second",
        "title": "五、问题解决",
        "knowledge_points": ["行程问题", "表面积的变化", "体积与重量", "可能性", "可能性的大小", "可能情况的个数"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "math-5b-final-review",
        "subject": "math",
        "semester": "second",
        "title": "六、总复习",
        "knowledge_points": ["数与运算", "方程与代数", "图形与几何", "统计初步"],
        "source_note": "上海五年级第二学期数学（试用本）目录",
    },
    {
        "id": "english-5a-m1u1-birthday",
        "subject": "english",
        "semester": "first",
        "title": "Module 1 Unit 1 My birthday",
        "knowledge_points": ["months and dates", "ordinal numbers", "When is your birthday", "party time expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m1u2-school-way",
        "subject": "english",
        "semester": "first",
        "title": "Module 1 Unit 2 My way to school",
        "knowledge_points": ["transport words", "How do you come to school", "by and on foot", "road safety expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m1u3-future",
        "subject": "english",
        "semester": "first",
        "title": "Module 1 Unit 3 My future",
        "knowledge_points": ["jobs", "want to be", "future dreams", "simple descriptions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m2u1-grandparents",
        "subject": "english",
        "semester": "first",
        "title": "Module 2 Unit 1 Grandparents",
        "knowledge_points": ["family activities", "visit and phone expressions", "present simple", "frequency expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m2u2-friends",
        "subject": "english",
        "semester": "first",
        "title": "Module 2 Unit 2 Friends",
        "knowledge_points": ["friend descriptions", "same and different", "hobbies", "comparative descriptions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m2u3-moving-home",
        "subject": "english",
        "semester": "first",
        "title": "Module 2 Unit 3 Moving home",
        "knowledge_points": ["home and rooms", "why questions", "place descriptions", "moving home expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m3u1-city",
        "subject": "english",
        "semester": "first",
        "title": "Module 3 Unit 1 Around the city",
        "knowledge_points": ["city places", "asking the way", "directions", "prepositions of place"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m3u2-clothes",
        "subject": "english",
        "semester": "first",
        "title": "Module 3 Unit 2 Buying new clothes",
        "knowledge_points": ["clothes words", "shopping dialogues", "which questions", "preferences"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m3u3-doctor",
        "subject": "english",
        "semester": "first",
        "title": "Module 3 Unit 3 Seeing the doctor",
        "knowledge_points": ["illness words", "should and should not", "advice", "doctor-patient dialogues"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m4u1-water",
        "subject": "english",
        "semester": "first",
        "title": "Module 4 Unit 1 Water",
        "knowledge_points": ["water vocabulary", "uses of water", "where questions", "process descriptions"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m4u2-wind",
        "subject": "english",
        "semester": "first",
        "title": "Module 4 Unit 2 Wind",
        "knowledge_points": ["weather and wind words", "sound and movement", "adjectives", "observing nature"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5a-m4u3-fire",
        "subject": "english",
        "semester": "first",
        "title": "Module 4 Unit 3 Fire",
        "knowledge_points": ["fire safety", "must and must not", "emergency expressions", "rules"],
        "source_note": "English (Oxford Shanghai Edition) 5A textbook contents",
    },
    {
        "id": "english-5b-m1u1-mess",
        "subject": "english",
        "semester": "second",
        "title": "Module 1 Unit 1 What a mess!",
        "knowledge_points": ["room objects", "tidying up", "whose questions", "possessive nouns"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m1u2-grow",
        "subject": "english",
        "semester": "second",
        "title": "Module 1 Unit 2 Watch it grow!",
        "knowledge_points": ["plants and growth", "life cycle", "changes over time", "sequence expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m1u3-noisy",
        "subject": "english",
        "semester": "second",
        "title": "Module 1 Unit 3 How noisy!",
        "knowledge_points": ["sounds", "noise descriptions", "How questions", "adjectives"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m2u1-food-drinks",
        "subject": "english",
        "semester": "second",
        "title": "Module 2 Unit 1 Food and drinks",
        "knowledge_points": ["food and drinks", "ordering food", "countable and uncountable nouns", "healthy eating"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m2u2-films",
        "subject": "english",
        "semester": "second",
        "title": "Module 2 Unit 2 Films",
        "knowledge_points": ["film types", "likes and reasons", "story descriptions", "opinion expressions"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m2u3-school-subjects",
        "subject": "english",
        "semester": "second",
        "title": "Module 2 Unit 3 School subjects",
        "knowledge_points": ["school subjects", "timetable expressions", "favourite subjects", "because clauses"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m3u1-signs",
        "subject": "english",
        "semester": "second",
        "title": "Module 3 Unit 1 Signs",
        "knowledge_points": ["public signs", "must and must not", "rules", "place-based instructions"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m3u2-weather",
        "subject": "english",
        "semester": "second",
        "title": "Module 3 Unit 2 Weather",
        "knowledge_points": ["weather words", "weather reports", "temperature expressions", "plans in weather"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m3u3-changes",
        "subject": "english",
        "semester": "second",
        "title": "Module 3 Unit 3 Changes",
        "knowledge_points": ["changes", "before and now", "past and present descriptions", "comparisons"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m4u1-museums",
        "subject": "english",
        "semester": "second",
        "title": "Module 4 Unit 1 Museums",
        "knowledge_points": ["museum vocabulary", "visiting rules", "past experiences", "information reading"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m4u2-holidays",
        "subject": "english",
        "semester": "second",
        "title": "Module 4 Unit 2 Western holidays",
        "knowledge_points": ["western holidays", "holiday customs", "dates and activities", "festival descriptions"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
    {
        "id": "english-5b-m4u3-story",
        "subject": "english",
        "semester": "second",
        "title": "Module 4 Unit 3 Story time",
        "knowledge_points": ["story reading", "sequence", "characters and actions", "retelling"],
        "source_note": "English (Oxford Shanghai Edition) 5B textbook contents",
    },
]

SUBJECT_LABELS = {"math": "数学", "english": "英语"}
SEMESTER_LABELS = {"first": "第一学期", "second": "第二学期"}
DIFFICULTY_LABELS = {"basic": "基础", "advanced": "提高", "challenge": "挑战"}

# 数据模型
class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    grade = Column(String(50), index=True, nullable=False, default="未分类")
    subject = Column(String(20), index=True, nullable=False, default="math")
    student_name = Column(String(100), index=True)
    image_path = Column(Text)
    ocr_text = Column(Text)
    ai_analysis = Column(Text)
    weak_points = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建表
Base.metadata.create_all(bind=engine)

# 兼容旧库：若已有 exams 表但无新增字段，启动时自动补列
try:
    inspector = inspect(engine)
    if inspector.has_table("exams"):
        cols = {c["name"] for c in inspector.get_columns("exams")}
        with engine.begin() as conn:
            if "grade" not in cols:
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
            if "subject" not in cols:
                if "postgresql" in DATABASE_URL:
                    conn.execute(text("ALTER TABLE exams ADD COLUMN IF NOT EXISTS subject VARCHAR(20)"))
                    conn.execute(text("UPDATE exams SET subject = 'math' WHERE subject IS NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_subject ON exams (subject)"))
                else:
                    conn.execute(text("ALTER TABLE exams ADD COLUMN subject VARCHAR(20)"))
                    conn.execute(text("UPDATE exams SET subject = 'math' WHERE subject IS NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exams_subject ON exams (subject)"))
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

async def call_deepseek(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    json_mode: bool = False,
    timeout_seconds: float = 60.0,
) -> str:
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY")
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    timeout = httpx.Timeout(timeout_seconds, connect=10.0, read=timeout_seconds, write=timeout_seconds, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class UnitWorksheetRequest(BaseModel):
    subject: str
    semester: str
    unit_ids: list[str] = Field(min_length=1)
    knowledge_points: list[str] = Field(min_length=1)
    difficulty: str
    question_count: int = Field(ge=3, le=20)
    title: str = Field(min_length=1, max_length=80)
    include_explanations: bool = True


def _strip_json_fence(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1])
    value = value.strip()
    start = value.find("{")
    end = value.rfind("}")
    if start != -1 and end != -1 and end > start:
        value = value[start : end + 1]
    return value.strip()


def _unique_values(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _unit_exam_profile(body: UnitWorksheetRequest, selected_units: list) -> dict:
    unit_titles = [u["title"] for u in selected_units]
    selected_points = _unique_values(body.knowledge_points)
    if body.subject == "math":
        common_mistakes = []
        for point in selected_points:
            if any(key in point for key in ["小数", "近似", "循环"]):
                common_mistakes.append("小数点位置、位数处理或近似数保留错误")
            elif any(key in point for key in ["方程", "等量"]):
                common_mistakes.append("等量关系找错，解方程后没有代入检验")
            elif any(key in point for key in ["面积", "体积", "容积", "表面积", "几何"]):
                common_mistakes.append("公式套用、单位换算或图形条件识别错误")
            elif any(key in point for key in ["平均", "统计"]):
                common_mistakes.append("把平均数当成最大值或总数，忽视数据个数")
            elif any(key in point for key in ["正数", "负数", "数轴"]):
                common_mistakes.append("正负号意义混淆，数轴方向判断错误")
            else:
                common_mistakes.append(f"{point} 的概念理解与迁移应用不稳定")
        return {
            "unit_titles": unit_titles,
            "exam_focus": [f"理解并运用“{point}”解决单元常规题和情境题" for point in selected_points],
            "skill_targets": ["概念辨析", "基本计算", "方法选择", "易错校验", "情境建模"],
            "common_mistakes": _unique_values(common_mistakes)[:6],
            "answer_requirements": ["写清关键步骤", "指出易错原因", "给出可复习的考点提示"],
        }

    common_mistakes = []
    for point in selected_points:
        lower_point = point.lower()
        if any(key in lower_point for key in ["date", "holiday", "festival", "birthday"]):
            common_mistakes.append("日期、节日活动和文化习俗搭配不准确")
        elif any(key in lower_point for key in ["must", "rule", "sign", "museum"]):
            common_mistakes.append("must / mustn't 与公共场所规则混用")
        elif any(key in lower_point for key in ["whose", "possessive"]):
            common_mistakes.append("物主代词和名词所有格使用错误")
        elif any(key in lower_point for key in ["story", "sequence", "retelling"]):
            common_mistakes.append("故事顺序、人物动作和复述逻辑不清")
        elif any(key in lower_point for key in ["weather", "temperature"]):
            common_mistakes.append("天气表达和活动计划的语境不匹配")
        elif any(key in lower_point for key in ["countable", "uncountable", "food"]):
            common_mistakes.append("可数/不可数名词和数量表达混淆")
        else:
            common_mistakes.append(f"{point} 缺少语境化理解和完整句表达")
    return {
        "unit_titles": unit_titles,
        "exam_focus": [f"在真实语境中理解并使用 {point}" for point in selected_points],
        "skill_targets": ["词汇语境", "核心句型", "语法功能", "阅读信息提取", "短句表达"],
        "common_mistakes": _unique_values(common_mistakes)[:6],
        "answer_requirements": ["说明考查语言功能", "解释干扰选项", "给出可模仿的正确表达"],
    }


def _question_plan(body: UnitWorksheetRequest) -> list[dict]:
    if body.subject == "math":
        if body.difficulty == "basic":
            cycle = [
                ("概念辨析", "判断学生是否真正理解核心概念"),
                ("基础计算", "检查单步算法和书写准确性"),
                ("常规应用", "把单一考点放入直接情境"),
            ]
        elif body.difficulty == "advanced":
            cycle = [
                ("基础计算", "检查熟练度"),
                ("方法辨析", "比较不同方法并识别易错步骤"),
                ("应用建模", "根据题意建立数量关系"),
                ("易错校验", "暴露小数点、单位或等量关系错误"),
            ]
        else:
            cycle = [
                ("综合应用", "整合两个以上考点解决问题"),
                ("方法解释", "说明为什么这样列式或判断"),
                ("易错辨析", "识别看似合理的错误做法"),
                ("迁移建模", "换情境后仍能使用本单元方法"),
            ]
    else:
        if body.difficulty == "basic":
            cycle = [
                ("词汇语境", "在句子中识别和使用本单元词汇"),
                ("核心句型", "检查目标句型的基本使用"),
                ("短文信息", "从短文中定位明确信息"),
            ]
        elif body.difficulty == "advanced":
            cycle = [
                ("词汇语境", "辨析词汇在真实语境中的用法"),
                ("句型语法", "检查本单元核心句型和语法功能"),
                ("阅读理解", "提取信息并作简单推断"),
                ("表达任务", "用 2-4 句完成主题表达"),
            ]
        else:
            cycle = [
                ("阅读推断", "整合短文信息完成判断"),
                ("语境改写", "在新语境中转换或补全句子"),
                ("表达任务", "有条理地输出主题短文"),
                ("易错辨析", "识别语法或搭配干扰项"),
            ]

    return [
        {
            "number": index,
            "planned_type": cycle[(index - 1) % len(cycle)][0],
            "teaching_intent": cycle[(index - 1) % len(cycle)][1],
            "knowledge_point": body.knowledge_points[(index - 1) % len(body.knowledge_points)],
        }
        for index in range(1, body.question_count + 1)
    ]


def _validate_generated_questions(body: UnitWorksheetRequest, questions: list) -> list:
    if len(questions) != body.question_count:
        raise ValueError("生成题目数量与设置不一致")

    normalized = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"第 {index} 题格式不正确")
        question.setdefault("id", f"q{index}")
        question.setdefault("type", "选择题")
        question.setdefault("options", [])
        question.setdefault("knowledge_points", [])
        question.setdefault("exam_focus", "")
        question.setdefault("common_mistake", "")
        question.setdefault("teaching_intent", "")
        if question.get("unit_id") not in body.unit_ids:
            question["unit_id"] = body.unit_ids[(index - 1) % len(body.unit_ids)]
        if not str(question.get("question", "")).strip():
            raise ValueError(f"第 {index} 题缺少题干")
        if not str(question.get("answer", "")).strip():
            raise ValueError(f"第 {index} 题缺少答案")
        if not str(question.get("explanation", "")).strip():
            raise ValueError(f"第 {index} 题缺少解析")
        options = question.get("options") or []
        if options and len(options) != 4:
            raise ValueError(f"第 {index} 题选择题选项必须为 4 个")
        normalized.append(question)
    return normalized


def _fallback_unit_worksheet(body: UnitWorksheetRequest, selected_units: list | None = None) -> list:
    selected_units = selected_units or [u for u in CURRICULUM_UNITS if u["id"] in body.unit_ids]
    profile = _unit_exam_profile(body, selected_units)
    plan = _question_plan(body)
    questions = []
    for index in range(1, body.question_count + 1):
        planned = plan[index - 1]
        point = planned["knowledge_point"]
        unit_id = body.unit_ids[(index - 1) % len(body.unit_ids)]
        common_mistake = profile["common_mistakes"][(index - 1) % len(profile["common_mistakes"])]
        if body.subject == "english":
            if planned["planned_type"] in ["词汇语境", "易错辨析"]:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"Choose the best answer in context.\\nThe class is reviewing '{point}'. Which sentence is correct and natural?",
                    "options": [
                        "A. We should read the signs carefully.",
                        "B. We should reads the signs carefully.",
                        "C. We reading the signs carefully.",
                        "D. We read the signs carefully yesterday tomorrow.",
                    ],
                    "answer": "A",
                    "explanation": "本题考查语境中的正确句型。should 后接动词原形，A 的语法和语境都正确。",
                    "knowledge_points": [point],
                    "exam_focus": f"在语境中使用 {point}",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
            elif planned["planned_type"] in ["核心句型", "句型语法", "语境改写"]:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"Rewrite the sentence to check '{point}'.\\nThere are some signs in the museum. (改为否定句)",
                    "options": [],
                    "answer": "There aren't any signs in the museum.",
                    "explanation": "本题考查句型转换。There be 句型否定式在 be 后加 not，some 在否定句中通常改为 any。",
                    "knowledge_points": [point],
                    "exam_focus": f"用目标句型表达 {point}",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
            else:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"Read and answer.\\nKitty visits a small museum with her parents. They read the signs and speak quietly. The guide tells them about a special holiday show. What should visitors do in the museum?",
                    "options": [
                        "A. Run in the hall.",
                        "B. Speak quietly.",
                        "C. Eat beside the pictures.",
                        "D. Touch everything.",
                    ],
                    "answer": "B",
                    "explanation": "本题考查阅读信息提取。短文中提到 They read the signs and speak quietly，因此应选择 B。",
                    "knowledge_points": [point],
                    "exam_focus": f"阅读中提取 {point} 相关信息",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
        else:
            if planned["planned_type"] in ["概念辨析", "易错校验", "易错辨析", "方法解释"]:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"围绕“{point}”判断：计算 2.4×3 时，可以先算 24×3，再把结果缩小到原来的十分之一。这个说法对吗？",
                    "options": ["A. 对", "B. 错", "C. 无法判断", "D. 只在整数乘法中成立"],
                    "answer": "A",
                    "explanation": "本题考查小数乘法算理。24×3=72，2.4 比 24 缩小到十分之一，所以积也要缩小到十分之一，结果是 7.2。",
                    "knowledge_points": [point],
                    "exam_focus": f"辨析 {point} 的核心方法",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
            elif planned["planned_type"] in ["基础计算", "方法辨析"]:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"计算并验算：3.6÷0.6。本题用于检查“{point}”。",
                    "options": [],
                    "answer": "6",
                    "explanation": "本题考查小数除法转化。把除数和被除数同时扩大 10 倍，变成 36÷6=6，验算 0.6×6=3.6。",
                    "knowledge_points": [point],
                    "exam_focus": f"准确运用 {point} 进行计算",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
            else:
                question = {
                    "id": f"q{index}",
                    "unit_id": unit_id,
                    "type": planned["planned_type"],
                    "question": f"一盒彩笔 4.8 元，买 5 盒需要多少元？请列式计算，并说明这道题和“{point}”有什么关系。",
                    "options": [],
                    "answer": "4.8×5=24（元）",
                    "explanation": "本题考查情境建模。求 5 个 4.8 是多少，用乘法计算；列式后还要关注小数点位置。",
                    "knowledge_points": [point],
                    "exam_focus": f"把 {point} 迁移到生活情境",
                    "common_mistake": common_mistake,
                    "teaching_intent": planned["teaching_intent"],
                }
        questions.append(question)
    return questions


def _validate_unit_request(body: UnitWorksheetRequest) -> list:
    if body.subject not in SUBJECT_LABELS:
        raise ValueError("学科参数不正确")
    if body.semester not in SEMESTER_LABELS:
        raise ValueError("学期参数不正确")
    if body.difficulty not in DIFFICULTY_LABELS:
        raise ValueError("难度参数不正确")

    selected_units = [u for u in CURRICULUM_UNITS if u["id"] in body.unit_ids]
    if len(selected_units) != len(body.unit_ids):
        raise ValueError("包含未知单元")
    if any(u["subject"] != body.subject or u["semester"] != body.semester for u in selected_units):
        raise ValueError("单元与当前学科或学期不匹配")

    allowed_points = {p for unit in selected_units for p in unit["knowledge_points"]}
    if any(p not in allowed_points for p in body.knowledge_points):
        raise ValueError("知识点与所选单元不匹配")
    return selected_units


async def ai_generate_unit_worksheet(body: UnitWorksheetRequest, selected_units: list) -> list:
    """按上海五年级教材目录范围和知识点生成原创复习题。"""
    model_question_count = min(body.question_count, 6)
    model_body = body.copy(update={"question_count": model_question_count})
    exam_profile = _unit_exam_profile(body, selected_units)
    question_plan = _question_plan(model_body)
    prompt = f"""你是一位熟悉上海小学五年级教学节奏的命题老师。
你的任务不是随机出练习题，而是按“单元诊断型复习卷”的方式命题。
只依据下面给出的单元名称、考点画像和题组计划生成原创题目，不引用或复刻教材原文。

学科：{SUBJECT_LABELS[body.subject]}
学期：{SEMESTER_LABELS[body.semester]}
单元：{"、".join(u["title"] for u in selected_units)}
知识点：{"、".join(body.knowledge_points)}
难度：{DIFFICULTY_LABELS[body.difficulty]}
题量：{model_body.question_count}

考点画像：
{json.dumps(exam_profile, ensure_ascii=False)}

题组计划：
{json.dumps(question_plan, ensure_ascii=False)}

要求：
1. 必须逐题遵守“题组计划”的 planned_type、teaching_intent 和 knowledge_point。
2. 数学题要体现概念辨析、基本计算、方法辨析、易错校验、应用建模中的一种，不出奥数题，不超出五年级范围。
3. 英语题要围绕语言功能：词汇语境、核心句型、语法功能、阅读信息提取、短句表达。不要出脱离单元主题的百科常识题。
4. 选择题必须有4个互不重复的选项；非选择题 options 返回空数组。
5. 每道题必须有明确答案和教师式解析：说明考点、解题步骤或语言规则、易错提醒。
6. 每道题都必须填写 exam_focus、common_mistake、teaching_intent。
7. unit_id 必须从这些值中选择：{", ".join(body.unit_ids)}
8. 只返回 JSON 对象，不要输出 Markdown。

返回格式：
{{
  "questions": [
    {{
      "id": "q1",
      "unit_id": "{body.unit_ids[0]}",
      "type": "选择题",
      "question": "题目内容",
      "options": ["A. 选项", "B. 选项", "C. 选项", "D. 选项"],
      "answer": "A",
      "explanation": "解析",
      "knowledge_points": ["知识点"],
      "exam_focus": "本题考查的核心考点",
      "common_mistake": "本题针对的典型错误",
      "teaching_intent": "为什么要出这道题"
    }}
  ]
}}"""
    last_error = None
    max_attempts = 1 if body.question_count > model_question_count else 2
    for attempt in range(max_attempts):
        retry_note = (
            "\n上一次输出未通过校验。请务必严格返回指定题量和字段。"
            if attempt
            else ""
        )
        try:
            raw = await call_deepseek(
                prompt + retry_note,
                temperature=0.3 if attempt else 0.5,
                max_tokens=6000,
                json_mode=True,
                timeout_seconds=35.0,
            )
            result = json.loads(_strip_json_fence(raw))
            questions = result.get("questions", [])
            questions = _validate_generated_questions(model_body, questions)
            if body.question_count > model_question_count:
                fallback_questions = _fallback_unit_worksheet(body, selected_units)
                questions.extend(fallback_questions[model_question_count:])
            return _validate_generated_questions(body, questions)
        except Exception as e:
            last_error = e
    print(f"Unit worksheet AI fallback: {last_error}")
    return _fallback_unit_worksheet(body, selected_units)

# ===== AI 分析（DeepSeek） =====

async def ai_analyze(ocr_text: str, subject: str, grade: str) -> dict:
    """使用 DeepSeek 进行错题分析"""
    subject_label = SUBJECT_LABELS.get(subject, "未知学科")
    subject_rules = (
        "这是英语试卷。请只分析英语相关问题，例如词汇理解、句型语法、阅读信息提取、拼写、时态、介词、物主代词、表达完整性。不要输出数学知识点。"
        if subject == "english"
        else "这是数学试卷。请只分析数学相关问题，例如概念理解、计算方法、审题、单位换算、方程关系、图形与统计。不要输出英语语法或词汇问题。"
    )
    prompt = f"""你是一位资深{grade}{subject_label}教师。请根据以下试卷 OCR 内容，进行错题诊断。

学科：{subject_label}
年级：{grade}
分析边界：{subject_rules}

试卷OCR识别内容：
{ocr_text}

要求：
1. 只根据 OCR 中能看见的题目、作答、批改痕迹进行分析，不要编造不存在的错题。
2. 如果 OCR 信息不足，请在 root_cause 说明“识别内容不足”，weak_points 给出可确认的少量方向。
3. weak_points 必须符合当前学科；英语卷不得出现“小数、面积、分数”等数学知识点。
4. recommendations 要能直接指导家长或学生复习。

请按以下JSON格式返回分析结果（不要包含其他文字，只返回JSON）：
{{
    "subject": "{subject}",
    "wrong_questions": [
        {{"question": "错题内容摘要", "error_type": "错误类型", "student_answer": "学生作答", "correct_answer": "正确答案"}},
        {{"question": "错题内容摘要", "error_type": "错误类型", "student_answer": "学生作答", "correct_answer": "正确答案"}}
    ],
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
        result = await call_deepseek(prompt, max_tokens=3000, json_mode=True)
        analysis = json.loads(_strip_json_fence(result))
        analysis.setdefault("subject", subject)
        analysis.setdefault("wrong_questions", [])
        analysis.setdefault("error_types", [])
        analysis.setdefault("weak_points", [])
        analysis.setdefault("root_cause", "")
        analysis.setdefault("recommendations", [])
        return analysis
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return {
            "subject": subject,
            "wrong_questions": [],
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
5. 选择题的4个选项必须各不相同，不能有重复或近似的选项，干扰项要有区分度

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
    subject: str = Form("math"),
    file: UploadFile = File(...)
):
    """上传试卷图片（按 年级 + 学生名 隔离）"""
    try:
        db = SessionLocal()

        student_name = (student_name or "").strip()
        grade = (grade or "").strip()
        subject = (subject or "math").strip()
        if not student_name:
            db.close()
            return JSONResponse({"success": False, "error": "student_name 不能为空"}, status_code=400)
        if not grade:
            db.close()
            return JSONResponse({"success": False, "error": "grade 不能为空"}, status_code=400)
        if subject not in SUBJECT_LABELS:
            db.close()
            return JSONResponse({"success": False, "error": "subject 必须是 math 或 english"}, status_code=400)
        if file.content_type not in {"image/jpeg", "image/png", "application/pdf"}:
            db.close()
            return JSONResponse({"success": False, "error": "仅支持 JPG、PNG 或 PDF 文件"}, status_code=400)

        # 读取文件内容
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            db.close()
            return JSONResponse({"success": False, "error": "文件大小不能超过 10MB"}, status_code=400)

        # 百度 OCR 识别
        ocr_result = await baidu_ocr(content)

        # 创建记录
        exam = Exam(
            grade=grade,
            subject=subject,
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
            "subject": subject,
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
        analysis = await ai_analyze(exam.ocr_text or "", exam.subject or "math", exam.grade or grade or "")

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
            "subject": exam.subject,
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
            "subject": e.subject,
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
        "subject": exam.subject,
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

        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    return pdf.output()


def generate_unit_worksheet_pdf(body: UnitWorksheetRequest, questions: list, include_answers: bool) -> bytes:
    """生成按单元筛选的题目卷或答案解析卷。"""
    from fpdf import FPDF

    def safe_multicell(pdf_obj, text_value, h=7, align="J"):
        text_value = str(text_value or "").strip()
        if not text_value:
            return
        pdf_obj.set_x(pdf_obj.l_margin)
        width = pdf_obj.w - pdf_obj.l_margin - pdf_obj.r_margin
        pdf_obj.multi_cell(width, h, text_value, align=align)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansCJKsc-Regular.otf")
    )
    pdf.add_font("zh", "", font_path)
    pdf.add_font("zh", "B", font_path)
    pdf.set_font("zh", "B", 17)
    safe_multicell(pdf, body.title, h=10, align="C")
    pdf.set_font("zh", "", 10)
    subtitle = (
        f"{SUBJECT_LABELS[body.subject]} · {SEMESTER_LABELS[body.semester]} · "
        f"{DIFFICULTY_LABELS[body.difficulty]} · {'答案解析卷' if include_answers else '题目卷'}"
    )
    safe_multicell(pdf, subtitle, align="C")
    pdf.ln(4)

    for index, question in enumerate(questions, start=1):
        pdf.set_font("zh", "B", 11)
        safe_multicell(pdf, f"{index}. [{question.get('type', '')}]")
        pdf.set_font("zh", "", 11)
        safe_multicell(pdf, question.get("question", ""))
        for option in question.get("options") or []:
            safe_multicell(pdf, option)
        if not include_answers and not question.get("options"):
            safe_multicell(pdf, "答：____________________________________________")
        if include_answers:
            pdf.set_text_color(20, 100, 55)
            safe_multicell(pdf, f"答案：{question.get('answer', '')}")
            if body.include_explanations:
                pdf.set_text_color(70, 78, 90)
                if question.get("exam_focus"):
                    safe_multicell(pdf, f"考点：{question.get('exam_focus', '')}")
                if question.get("common_mistake"):
                    safe_multicell(pdf, f"易错提醒：{question.get('common_mistake', '')}")
                if question.get("teaching_intent"):
                    safe_multicell(pdf, f"命题意图：{question.get('teaching_intent', '')}")
                safe_multicell(pdf, f"解析：{question.get('explanation', '')}")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
    return bytes(pdf.output())


@app.get("/curriculum-units")
async def curriculum_units():
    """返回可用于单元复习卷的公开目录范围与人工整理知识点。"""
    return {"units": CURRICULUM_UNITS}


@app.post("/generate-unit-worksheet")
async def generate_unit_worksheet(body: UnitWorksheetRequest):
    """按单元、知识点、难度和题量生成题目卷与答案解析卷。"""
    try:
        selected_units = _validate_unit_request(body)
        questions = await ai_generate_unit_worksheet(body, selected_units)
        question_pdf = generate_unit_worksheet_pdf(body, questions, include_answers=False)
        answer_pdf = generate_unit_worksheet_pdf(body, questions, include_answers=True)
        prefix = (
            f"五年级{SUBJECT_LABELS[body.subject]}-"
            f"{SEMESTER_LABELS[body.semester]}-{DIFFICULTY_LABELS[body.difficulty]}"
        )
        return {
            "success": True,
            "questions": [
                {
                    "number": index,
                    "type": question.get("type", ""),
                    "question": question.get("question", ""),
                    "knowledge_points": question.get("knowledge_points", []),
                    "exam_focus": question.get("exam_focus", ""),
                    "common_mistake": question.get("common_mistake", ""),
                    "teaching_intent": question.get("teaching_intent", ""),
                }
                for index, question in enumerate(questions, start=1)
            ],
            "question_pdf": {
                "filename": f"{prefix}-题目卷.pdf",
                "data_url": f"data:application/pdf;base64,{base64.b64encode(question_pdf).decode('ascii')}",
            },
            "answer_pdf": {
                "filename": f"{prefix}-答案解析卷.pdf",
                "data_url": f"data:application/pdf;base64,{base64.b64encode(answer_pdf).decode('ascii')}",
            },
        }
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"生成失败：{str(e)[:180]}"}, status_code=500)

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
        "version": "0.6.0",
        "ai_provider": "DeepSeek",
        "ocr_provider": "Baidu",
        "endpoints": {
            "upload": "POST /upload (form-data: grade, student_name, file)",
            "analyze": "POST /analyze/{id}?grade=...&student_name=... - DeepSeek AI分析",
            "generate_practice": "POST /generate-practice/{id}?grade=...&student_name=... - DeepSeek AI生成5道巩固题",
            "export_pdf": "POST /export-practice-pdf/{id}?grade=...&student_name=... - 导出PDF",
            "curriculum_units": "GET /curriculum-units - 单元复习卷筛选数据",
            "generate_unit_worksheet": "POST /generate-unit-worksheet - 生成单元题目卷与答案解析卷",
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
