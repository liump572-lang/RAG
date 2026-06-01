import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.database import engine, Base, get_db
from app.common.response import error_response, success_response
from sqlalchemy import func
from app.models import Conversation, Document, KnowledgePoint, Subject, StudyNote, User, WrongQuestion
from app.middleware.auth import get_current_user
from app.modules.auth.router import router as auth_router
from app.modules.user.router import router as user_router
from app.modules.kb.router import router as kb_router
from app.modules.qa.router import router as qa_router
from app.modules.kg.router import router as kg_router
from app.modules.notes.router import router as notes_router
from app.modules.wrong_q.router import router as wrong_q_router
from app.modules.notification.router import router as notification_router
from app.modules.system.router import router as system_router

app = FastAPI(
    title="计算机学科知识点智能问答系统",
    description="基于 RAG 架构的智能问答系统 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(user_router, prefix="/api/v1/admin/users", tags=["用户管理"])
app.include_router(kb_router, prefix="/api/v1/kb", tags=["知识库"])
app.include_router(qa_router, prefix="/api/v1/qa", tags=["智能问答"])
app.include_router(kg_router, prefix="/api/v1/kg", tags=["知识图谱"])
app.include_router(notes_router, prefix="/api/v1/notes", tags=["学习心得"])
app.include_router(wrong_q_router, prefix="/api/v1/wq", tags=["错题本"])
app.include_router(system_router, prefix="/api/v1/admin/system", tags=["系统设置"])
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["消息通知"])


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/v1/health")
def health_check():
    return success_response(data={"status": "ok", "version": "1.0.0"})


@app.get("/api/v1/subjects")
def list_subjects(db: Session = Depends(get_db)):
    subjects = db.query(Subject).order_by(Subject.sort_order).all()
    data = [{"id": s.id, "name": s.name, "description": s.description, "is_built_in": bool(s.is_built_in)} for s in subjects]
    return success_response(data=data)


class SubjectCreate(BaseModel):
    name: str
    description: str = ""


class SubjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


@app.post("/api/v1/admin/subjects")
def create_subject(
    body: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    existing = db.query(Subject).filter(Subject.name == body.name).first()
    if existing:
        return error_response(400, "该科目已存在")
    max_sort = db.query(func.max(Subject.sort_order)).scalar() or 0
    subject = Subject(name=body.name, description=body.description, sort_order=max_sort + 1)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return success_response(data={"id": subject.id, "name": subject.name, "description": subject.description, "is_built_in": False})


@app.put("/api/v1/admin/subjects/{subject_id}")
def update_subject(
    subject_id: int,
    body: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return error_response(404, "科目不存在")
    if body.name is not None:
        dup = db.query(Subject).filter(Subject.name == body.name, Subject.id != subject_id).first()
        if dup:
            return error_response(400, "科目名称已存在")
        subject.name = body.name
    if body.description is not None:
        subject.description = body.description
    if body.sort_order is not None:
        subject.sort_order = body.sort_order
    db.commit()
    db.refresh(subject)
    return success_response(data={"id": subject.id, "name": subject.name, "description": subject.description, "is_built_in": bool(subject.is_built_in), "sort_order": subject.sort_order})


@app.delete("/api/v1/admin/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return error_response(404, "科目不存在")
    if subject.is_built_in:
        return error_response(400, "内置科目不可删除")
    doc_count = db.query(func.count(Document.id)).filter(Document.subject_id == subject_id).scalar()
    if doc_count > 0:
        return error_response(400, f"该科目下还有 {doc_count} 个文档，请先删除或迁移")
    db.delete(subject)
    db.commit()
    return success_response(data={"id": subject_id})


@app.get("/api/v1/admin/dashboard")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    total_users = db.query(func.count(User.id)).scalar()
    total_docs = db.query(func.count(Document.id)).scalar()
    total_convs = db.query(func.count(Conversation.id)).scalar()
    total_points = db.query(func.count(KnowledgePoint.id)).scalar()
    total_notes = db.query(func.count(StudyNote.id)).scalar()
    total_wrong = db.query(func.count(WrongQuestion.id)).scalar()

    docs_by_subject = (
        db.query(Subject.id, Subject.name, func.count(Document.id))
        .outerjoin(Document, Subject.id == Document.subject_id)
        .group_by(Subject.id, Subject.name)
        .order_by(Subject.sort_order)
        .all()
    )

    docs_by_type = (
        db.query(Document.doc_type, func.count(Document.id))
        .group_by(Document.doc_type)
        .all()
    )

    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    recent_convs = (
        db.query(func.date(Conversation.created_at), func.count(Conversation.id))
        .filter(Conversation.created_at >= week_ago)
        .group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
        .all()
    )

    return success_response(data={
        "total_users": total_users,
        "total_documents": total_docs,
        "total_conversations": total_convs,
        "total_knowledge_points": total_points,
        "total_notes": total_notes,
        "total_wrong_questions": total_wrong,
        "docs_by_subject": [{"subject_id": r[0], "name": r[1], "count": r[2]} for r in docs_by_subject],
        "docs_by_type": [{"type": r[0], "count": r[1]} for r in docs_by_type],
        "recent_conversations": [{"date": str(r[0]), "count": r[1]} for r in recent_convs],
    })


@app.get("/")
def root():
    return {"message": "计算机学科知识点智能问答系统 API", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
