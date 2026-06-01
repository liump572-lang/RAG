from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import error_response, paginated_response, success_response
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.modules.notification.schemas import NotificationResponse
from app.modules.notification.service import NotificationService

router = APIRouter()


@router.get("")
def list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    unread: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = NotificationService.list_for_user(db, current_user.id, page, size, unread_only=unread)
    data = [NotificationResponse.model_validate(n).model_dump() for n in items]
    return paginated_response(data, total, page, size)


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.unread_count(db, current_user.id)
    return success_response(data={"count": count})


@router.put("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = NotificationService.mark_read(db, notification_id, current_user.id)
    if not notif:
        return error_response(404, "通知不存在")
    return success_response(data=NotificationResponse.model_validate(notif).model_dump())


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.mark_all_read(db, current_user.id)
    return success_response(message=f"已读 {count} 条通知")
