from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.response import error_response, paginated_response, success_response
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.modules.wrong_q.schemas import (
    PracticeRequest,
    ReviewInput,
    WrongQuestionCreate,
    WrongQuestionResponse,
    WrongQuestionUpdate,
)
from app.modules.wrong_q.service import WrongQService

router = APIRouter()


def require_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "user":
        raise HTTPException(status_code=403, detail={"message": "管理员不使用错题本"})
    return current_user


@router.post("")
def create_wq(
    body: WrongQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    wq = WrongQService.create(db, current_user.id, body)
    return success_response(data=WrongQuestionResponse.model_validate(wq).model_dump())


@router.get("")
def list_wq(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    subject_id: Optional[int] = Query(None),
    mastery_status: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    items, total = WrongQService.list(
        db, current_user.id, page, size,
        subject_id, mastery_status, error_reason, keyword,
    )
    data = [WrongQuestionResponse.model_validate(wq).model_dump() for wq in items]
    return paginated_response(data, total, page, size)


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    data = WrongQService.stats(db, current_user.id)
    return success_response(data=data)


@router.get("/practice")
def get_practice(
    subject_id: Optional[int] = Query(None),
    count: int = Query(10, ge=1, le=50),
    mastery_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    items = WrongQService.practice(db, current_user.id, subject_id, count, mastery_status)
    data = [WrongQuestionResponse.model_validate(wq).model_dump() for wq in items]
    return success_response(data=data)


@router.get("/{wq_id}")
def get_wq(
    wq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    wq = WrongQService.get(db, wq_id, current_user.id)
    if not wq:
        return error_response(404, "记录不存在")
    return success_response(data=WrongQuestionResponse.model_validate(wq).model_dump())


@router.put("/{wq_id}")
def update_wq(
    wq_id: int,
    body: WrongQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    wq = WrongQService.update(db, wq_id, current_user.id, body)
    if not wq:
        return error_response(404, "记录不存在")
    return success_response(data=WrongQuestionResponse.model_validate(wq).model_dump())


@router.delete("/{wq_id}")
def delete_wq(
    wq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    ok = WrongQService.delete(db, wq_id, current_user.id)
    if not ok:
        return error_response(404, "记录不存在")
    return success_response(message="已删除")


@router.post("/{wq_id}/review")
def review_wq(
    wq_id: int,
    body: ReviewInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    wq = WrongQService.review(db, wq_id, current_user.id, body.is_correct, body.mastery_status)
    if not wq:
        return error_response(404, "记录不存在")
    return success_response(data=WrongQuestionResponse.model_validate(wq).model_dump())
