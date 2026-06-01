from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import User, WrongQuestion


class WrongQService:

    @staticmethod
    def create(db: Session, user_id: int, data) -> WrongQuestion:
        wq = WrongQuestion(
            user_id=user_id,
            subject_id=data.subject_id,
            question_content=data.question_content,
            correct_answer=data.correct_answer,
            user_answer=data.user_answer,
            error_reason=data.error_reason,
            difficulty=data.difficulty or 3,
            exam_question_id=data.exam_question_id,
            message_id=data.message_id,
        )
        db.add(wq)
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.wrong_question_count += 1
        db.commit()
        db.refresh(wq)
        return wq

    @staticmethod
    def get(db: Session, wq_id: int, user_id: int) -> Optional[WrongQuestion]:
        return db.query(WrongQuestion).filter(
            WrongQuestion.id == wq_id, WrongQuestion.user_id == user_id
        ).first()

    @staticmethod
    def list(
        db: Session, user_id: int,
        page: int = 1, size: int = 20,
        subject_id: int = None, mastery_status: str = None,
        error_reason: str = None, keyword: str = None,
    ):
        query = db.query(WrongQuestion).filter(WrongQuestion.user_id == user_id)
        if subject_id:
            query = query.filter(WrongQuestion.subject_id == subject_id)
        if mastery_status:
            query = query.filter(WrongQuestion.mastery_status == mastery_status)
        if error_reason:
            query = query.filter(WrongQuestion.error_reason == error_reason)
        if keyword:
            query = query.filter(WrongQuestion.question_content.like(f"%{keyword}%"))
        total = query.count()
        items = query.order_by(WrongQuestion.updated_at.desc()).offset(
            (page - 1) * size
        ).limit(size).all()
        return items, total

    @staticmethod
    def update(db: Session, wq_id: int, user_id: int, data) -> Optional[WrongQuestion]:
        wq = db.query(WrongQuestion).filter(
            WrongQuestion.id == wq_id, WrongQuestion.user_id == user_id
        ).first()
        if not wq:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(wq, key, val)
        db.commit()
        db.refresh(wq)
        return wq

    @staticmethod
    def delete(db: Session, wq_id: int, user_id: int) -> bool:
        wq = db.query(WrongQuestion).filter(
            WrongQuestion.id == wq_id, WrongQuestion.user_id == user_id
        ).first()
        if not wq:
            return False
        db.delete(wq)
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.wrong_question_count > 0:
            user.wrong_question_count -= 1
        db.commit()
        return True

    @staticmethod
    def practice(
        db: Session, user_id: int,
        subject_id: int = None, count: int = 10, mastery_status: str = None,
    ):
        query = db.query(WrongQuestion).filter(WrongQuestion.user_id == user_id)
        if subject_id:
            query = query.filter(WrongQuestion.subject_id == subject_id)
        if mastery_status:
            query = query.filter(WrongQuestion.mastery_status == mastery_status)
        items = query.order_by(WrongQuestion.review_count.asc()).limit(count).all()
        return items

    @staticmethod
    def review(
        db: Session, wq_id: int, user_id: int, is_correct: bool,
        mastery_status: str = None,
    ) -> Optional[WrongQuestion]:
        wq = db.query(WrongQuestion).filter(
            WrongQuestion.id == wq_id, WrongQuestion.user_id == user_id
        ).first()
        if not wq:
            return None
        wq.review_count += 1
        if is_correct:
            wq.mastery_status = mastery_status or "mastered"
            wq.mastered_at = datetime.now()
        else:
            wq.mastery_status = mastery_status or "unmastered"
            wq.mastered_at = None
        db.commit()
        db.refresh(wq)
        return wq

    @staticmethod
    def stats(db: Session, user_id: int) -> dict:
        base = db.query(WrongQuestion).filter(WrongQuestion.user_id == user_id)
        total = base.count()

        by_subject = (
            db.query(
                WrongQuestion.subject_id,
                func.count(WrongQuestion.id).label("count"),
            )
            .filter(WrongQuestion.user_id == user_id)
            .group_by(WrongQuestion.subject_id)
            .all()
        )

        by_reason = (
            db.query(
                WrongQuestion.error_reason,
                func.count(WrongQuestion.id).label("count"),
            )
            .filter(WrongQuestion.user_id == user_id)
            .group_by(WrongQuestion.error_reason)
            .all()
        )

        by_status = (
            db.query(
                WrongQuestion.mastery_status,
                func.count(WrongQuestion.id).label("count"),
            )
            .filter(WrongQuestion.user_id == user_id)
            .group_by(WrongQuestion.mastery_status)
            .all()
        )

        return {
            "total": total,
            "by_subject": [{"subject_id": r.subject_id, "count": r.count} for r in by_subject],
            "by_reason": [{"reason": r.error_reason, "count": r.count} for r in by_reason],
            "by_status": [{"status": r.mastery_status, "count": r.count} for r in by_status],
        }
