from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
import httpx
import base64
from datetime import datetime

# 数据库配置 - Railway 使用 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    student_name = Column(String(100))
    image_path = Column(Text)
    ocr_text = Column(Text)
    ai_analysis = Column(Text)
    weak_points = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI教育平台MVP API")
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
    """调用百度通用文字识别（高精度版）"""
    try:
        token = await get_baidu_access_token()
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # 优先用高精度版，失败回退标准版
        for api_url in [
            "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic",
            "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        ]:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    api_url,
                    params={"access_token": token},
                    data={"image": img_b64, "language_type": "CHN_ENG"}
                )
                data = resp.json()
                
                if "words_result" in data:
                    words = [item["words"] for item in data["words_result"]]
                    full_text = "\n".join(words)
                    if full_text.strip():
                        return full_text
                
                # 如果是额度用完，换标准版
                if "高精度" in data.get("error_msg", ""):
                    continue
                    
        # 都失败了，回退 mock
        return f"[OCR识别失败，使用模拟数据] 识别到数学题目3道，填空题5道"
        
    except Exception as e:
        print(f"Baidu OCR error: {e}")
        return f"[OCR服务异常] {str(e)[:50]}，请稍后重试"

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
async def upload_exam(student_name: str = Form(...), file: UploadFile = File(...)):
    """上传试卷图片"""
    try:
        from sqlalchemy.orm import Session
        db = SessionLocal()
        
        # 读取文件内容
        content = await file.read()
        
        # 百度 OCR 识别
        ocr_result = await baidu_ocr(content)
        
        # 创建记录
        exam = Exam(
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
            "student": student_name,
            "ocr_preview": ocr_result[:200] + "..." if len(ocr_result) > 200 else ocr_result,
            "next_step": f"POST /analyze/{exam.id} 进行AI分析"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/analyze/{exam_id}")
async def analyze_exam(exam_id: int):
    """AI分析错题（DeepSeek）"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)
        
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
            "analysis": analysis,
            "summary": {
                "weak_points": analysis.get("weak_points", []),
                "recommendations": analysis.get("recommendations", [])[:3]
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/exams")
async def list_exams(limit: int = 10):
    """获取最近上传的试卷列表"""
    db = SessionLocal()
    exams = db.query(Exam).order_by(Exam.created_at.desc()).limit(limit).all()
    db.close()
    
    return JSONResponse({
        "exams": [{
            "id": e.id,
            "student": e.student_name,
            "image": e.image_path,
            "ocr_preview": e.ocr_text[:50] + "..." if e.ocr_text else None,
            "weak_points": json.loads(e.weak_points) if e.weak_points else None,
            "created": e.created_at.isoformat() if e.created_at else None
        } for e in exams]
    })

@app.get("/exams/{exam_id}")
async def get_exam(exam_id: int):
    """获取单个试卷详情"""
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    db.close()
    
    if not exam:
        return JSONResponse({"error": "试卷不存在"}, status_code=404)
    
    return JSONResponse({
        "id": exam.id,
        "student": exam.student_name,
        "image": exam.image_path,
        "ocr_text": exam.ocr_text,
        "ai_analysis": json.loads(exam.ai_analysis) if exam.ai_analysis else None,
        "weak_points": json.loads(exam.weak_points) if exam.weak_points else None,
        "recommendations": json.loads(exam.recommendations) if exam.recommendations else None,
        "created": exam.created_at.isoformat() if exam.created_at else None
    })

@app.delete("/exams/{exam_id}")
async def delete_exam(exam_id: int):
    """删除试卷"""
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam:
        db.delete(exam)
        db.commit()
    db.close()
    return JSONResponse({"success": True, "message": "已删除"})

@app.get("/")
async def root():
    """返回前端页面"""
    web_path = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
    if os.path.exists(web_path):
        return FileResponse(web_path)
    return JSONResponse({"message": "API运行中，前端文件未找到"})

@app.post("/generate-practice/{exam_id}")
async def generate_practice(exam_id: int):
    """根据薄弱知识点生成5道巩固练习题（DeepSeek AI 生成）"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)
        
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
            "weak_points": weak_points,
            "questions": questions,
            "total": len(questions),
            "note": "由 DeepSeek AI 动态生成"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api-info")
async def api_info():
    """API信息"""
    return {
        "message": "🎓 AI教育平台MVP API运行中",
        "version": "0.3.0",
        "ai_provider": "DeepSeek",
        "ocr_provider": "Baidu",
        "endpoints": {
            "upload": "POST /upload (form-data: student_name, file)",
            "analyze": "POST /analyze/{id} - DeepSeek AI分析",
            "generate_practice": "POST /generate-practice/{id} - DeepSeek AI生成5道巩固题",
            "list": "GET /exams",
            "detail": "GET /exams/{id}",
            "delete": "DELETE /exams/{id}"
        },
        "status": "OCR已接入百度识别，AI分析已接入DeepSeek",
        "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
