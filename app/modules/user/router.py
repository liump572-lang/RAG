from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.common.response import success_response, error_response
from app.middleware.auth import get_current_user
from app.models import User
from app.modules.user.schemas import CreateUserInput, UpdateUserInput
from app.modules.user import service as user_service

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    return current_user


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = None,
    role: str = None,
    status: str = None,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    result = user_service.list_users(db, page, size, keyword, role, status)
    return success_response(data=result)


@router.post("")
def create_user(
    input: CreateUserInput,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_service.create_user(db, input)
    return success_response(data=user)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    input: UpdateUserInput,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_service.update_user(db, user_id, input)
    return success_response(data=user)


@router.put("/{user_id}/status")
def toggle_user_status(
    user_id: int,
    target_status: str = Query(pattern="^(active|disabled)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    user_service.toggle_status(db, user_id, target_status, current_user.id)
    return success_response(message="状态已更新")


@router.put("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    new_password = user_service.reset_password(db, user_id)
    return success_response(data={"new_password": new_password})
