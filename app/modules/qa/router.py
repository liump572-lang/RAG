from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.common.response import error_response, paginated_response, success_response
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Conversation, Message, User
from app.modules.qa.schemas import AskInput, ConversationResponse, FeedbackInput, MessageResponse
from app.modules.qa.service import QaService
from app.modules.wrong_q.schemas import WrongQuestionCreate
from app.modules.wrong_q.service import WrongQService

router = APIRouter()


@router.post("/ask")
def ask_question(
    body: AskInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generator, conv_id = QaService.ask_stream(
        db, current_user.id, body.question, body.conversation_id, body.subject_id,
    )
    return EventSourceResponse(generator())


@router.get("/conversations")
def list_conversations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = QaService.list_conversations(db, current_user.id, page, size)
    data = [ConversationResponse.model_validate(c) for c in items]
    return paginated_response([d.model_dump() for d in data], total, page, size)


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv, msgs = QaService.get_messages(db, conversation_id, current_user.id)
    if not conv:
        return error_response(404, "对话不存在")
    return success_response(data={
        "conversation": ConversationResponse.model_validate(conv).model_dump(),
        "messages": [MessageResponse.model_validate(m).model_dump() for m in msgs],
    })


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = QaService.delete_conversation(db, conversation_id, current_user.id)
    if not ok:
        return error_response(404, "对话不存在")
    return success_response(message="对话已删除")


@router.post("/feedback/{message_id}")
def submit_feedback(
    message_id: int,
    body: FeedbackInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = QaService.submit_feedback(db, message_id, current_user.id, body.score)
    if not msg:
        return error_response(404, "消息不存在")
    if body.add_to_wrong:
        conv = db.query(Conversation).filter(Conversation.id == msg.conversation_id).first()
        question_msg = db.query(Message).filter(
            Message.conversation_id == msg.conversation_id,
            Message.role == "user",
            Message.id < msg.id,
        ).order_by(Message.id.desc()).first()
        WrongQService.create(db, current_user.id, WrongQuestionCreate(
            subject_id=conv.subject_id if conv else 1,
            question_content=question_msg.content if question_msg else "",
            correct_answer=body.correct_answer or msg.content,
            user_answer=body.user_answer,
            error_reason=body.error_reason,
            difficulty=body.difficulty or 3,
            message_id=message_id,
        ))
    return success_response(message="反馈已提交")
