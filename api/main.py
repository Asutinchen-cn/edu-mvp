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
from datetime import datetime

# 数据库配置 - Railway 使用 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# 简易OCR模拟（后续接入百度OCR）
def mock_ocr(image_path: str) -> str:
    return f"[OCR结果] 识别到数学题目3道，填空题5道"

# AI分析模拟（后续接入混元API）
def mock_analyze(ocr_text: str) -> dict:
    return {
        "error_types": ["计算错误", "概念不清"],
        "weak_points": ["二次函数", "不等式求解"],
        "root_cause": "对二次函数图像性质理解不透彻，导致最值判断失误",
        "recommendations": [
            "复习二次函数顶点式与一般式的转换",
            "练习3道二次函数最值题目",
            "观看二次函数图像动画演示"
        ]
    }

# 生成巩固练习题（根据薄弱知识点）
def generate_practice_questions(weak_points: list) -> list:
    """根据薄弱知识点生成5道巩固练习题"""
    # 模拟题库 - 实际可接入真实题库或AI生成
    question_bank = {
        "二次函数": [
            {
                "id": 1,
                "type": "选择题",
                "question": "二次函数 y = x² - 4x + 3 的顶点坐标是？",
                "options": ["(2, -1)", "(-2, 1)", "(2, 1)", "(-2, -1)"],
                "answer": "A",
                "hint": "使用顶点公式 x = -b/2a"
            },
            {
                "id": 2,
                "type": "填空题",
                "question": "若二次函数 y = ax² + bx + c 的图像开口向上，则 a ____ 0",
                "answer": ">",
                "hint": "开口方向由二次项系数决定"
            },
            {
                "id": 3,
                "type": "解答题",
                "question": "求二次函数 y = -2x² + 8x - 5 的最大值及对应的x值",
                "answer": "当x=2时，最大值y=3",
                "hint": "开口向下，顶点处取最大值"
            }
        ],
        "不等式求解": [
            {
                "id": 4,
                "type": "选择题",
                "question": "不等式 2x - 5 > 3 的解集是？",
                "options": ["x > 4", "x < 4", "x > 1", "x < 1"],
                "answer": "A",
                "hint": "移项后两边同除以2"
            },
            {
                "id": 5,
                "type": "填空题",
                "question": "若 |x - 3| < 5，则 x 的取值范围是 ____",
                "answer": "-2 < x < 8",
                "hint": "绝对值不等式转化为复合不等式"
            }
        ],
        "默认": [
            {
                "id": 6,
                "type": "选择题",
                "question": "以下哪个是函数 y = x² 的性质？",
                "options": ["关于y轴对称", "关于原点对称", "单调递增", "单调递减"],
                "answer": "A",
                "hint": "二次函数的对称性"
            }
        ]
    }
    
    questions = []
    # 根据薄弱知识点组卷
    for point in weak_points:
        if point in question_bank:
            questions.extend(question_bank[point])
    
    # 如果不足5道，补充默认题目
    while len(questions) < 5:
        questions.extend(question_bank["默认"])
    
    # 返回前5道
    return questions[:5]

@app.post("/upload")
async def upload_exam(student_name: str = Form(...), file: UploadFile = File(...)):
    """上传试卷图片"""
    try:
        from sqlalchemy.orm import Session
        db = SessionLocal()
        
        # 读取文件内容
        content = await file.read()
        
        # OCR识别
        ocr_result = mock_ocr("")
        
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
            "ocr_preview": ocr_result[:100] + "...",
            "next_step": f"POST /analyze/{exam.id} 进行AI分析"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/analyze/{exam_id}")
async def analyze_exam(exam_id: int):
    """AI分析错题"""
    try:
        db = SessionLocal()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            db.close()
            return JSONResponse({"error": "试卷不存在"}, status_code=404)
        
        # AI分析
        analysis = mock_analyze(exam.ocr_text)
        
        # 更新记录
        exam.ai_analysis = json.dumps(analysis, ensure_ascii=False)
        exam.weak_points = json.dumps(analysis["weak_points"], ensure_ascii=False)
        exam.recommendations = json.dumps(analysis["recommendations"], ensure_ascii=False)
        db.commit()
        db.close()
        
        return JSONResponse({
            "success": True,
            "exam_id": exam_id,
            "analysis": analysis,
            "summary": {
                "weak_points": analysis["weak_points"],
                "recommendations": analysis["recommendations"][:3]
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
    """根据薄弱知识点生成5道巩固练习题"""
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
        
        # 生成练习题
        questions = generate_practice_questions(weak_points)
        
        db.close()
        
        return JSONResponse({
            "success": True,
            "exam_id": exam_id,
            "weak_points": weak_points,
            "questions": questions,
            "total": len(questions),
            "note": "当前为模拟题库，后续可接入AI生成真实题目"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api-info")
async def api_info():
    """API信息"""
    return {
        "message": "🎓 AI教育平台MVP API运行中",
        "version": "0.1.0",
        "endpoints": {
            "upload": "POST /upload (form-data: student_name, file)",
            "analyze": "POST /analyze/{id}",
            "generate_practice": "POST /generate-practice/{id} - 生成5道巩固题",
            "list": "GET /exams",
            "detail": "GET /exams/{id}",
            "delete": "DELETE /exams/{id}"
        },
        "status": "OCR和AI分析当前为模拟模式，可接入真实API",
        "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
