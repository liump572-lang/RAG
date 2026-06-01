from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification


class NotificationService:

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        type_: str,
        title: str,
        content: Optional[str] = None,
        related_id: Optional[int] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type_,
            title=title,
            content=content,
            related_id=related_id,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def list_for_user(
        db: Session,
        user_id: int,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False,
    ):
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == 0)

        total = query.count()
        items = query.order_by(Notification.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    @staticmethod
    def mark_read(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ).first()
        if notif:
            notif.is_read = 1
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_read(db: Session, user_id: int) -> int:
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == 0,
        ).update({"is_read": 1})
        db.commit()
        return count

    @staticmethod
    def unread_count(db: Session, user_id: int) -> int:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == 0,
        ).count()
