from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import NoteComment, NoteFavorite, NoteLike, Notification, StudyNote, Subject, User


class NotesService:

    @staticmethod
    def create_note(db: Session, user_id: int, subject_id: int, title: str, content: str, tags: list = None) -> StudyNote:
        note = StudyNote(
            user_id=user_id,
            subject_id=subject_id,
            title=title,
            content=content,
            tags=tags or [],
            status="pending",
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def _notify_author(db: Session, note: StudyNote, action: str, reject_reason: str = None):
        """Create a notification for the note author when note is reviewed."""
        if action == "approve":
            title = f"心得「{note.title[:30]}」已通过审核"
            content = "你的学习心得已通过审核，现在其他用户可以看到它了。"
            notif_type = "note_approved"
        else:
            title = f"心得「{note.title[:30]}」未通过审核"
            reason_text = f"\n驳回原因：{reject_reason}" if reject_reason else ""
            content = f"你的学习心得未通过审核。{reason_text}"
            notif_type = "note_rejected"

        notif = Notification(
            user_id=note.user_id,
            type=notif_type,
            title=title,
            content=content,
            related_id=note.id,
        )
        db.add(notif)

    @staticmethod
    def update_note(db: Session, note_id: int, user_id: int, title: str = None, content: str = None, tags: list = None) -> Optional[StudyNote]:
        note = db.query(StudyNote).filter(StudyNote.id == note_id, StudyNote.user_id == user_id).first()
        if not note:
            return None
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags
        if note.status in ("rejected", "published"):
            note.status = "pending"
            note.reject_reason = None
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def delete_note(db: Session, note_id: int, user_id: int, is_admin: bool = False) -> bool:
        query = db.query(StudyNote).filter(StudyNote.id == note_id)
        if not is_admin:
            query = query.filter(StudyNote.user_id == user_id)
        note = query.first()
        if not note:
            return False
        db.query(NoteComment).filter(NoteComment.note_id == note_id).delete()
        db.query(NoteFavorite).filter(NoteFavorite.note_id == note_id).delete()
        db.query(NoteLike).filter(NoteLike.note_id == note_id).delete()
        db.delete(note)
        db.commit()
        return True

    @staticmethod
    def get_note(db: Session, note_id: int) -> Optional[StudyNote]:
        return db.query(StudyNote).filter(StudyNote.id == note_id).first()

    @staticmethod
    def get_my_counts(db: Session, user_id: int) -> dict:
        from sqlalchemy import func
        rows = db.query(
            StudyNote.status, func.count(StudyNote.id)
        ).filter(
            StudyNote.user_id == user_id
        ).group_by(StudyNote.status).all()
        counts = {"pending": 0, "published": 0, "rejected": 0}
        for status, count in rows:
            if status in counts:
                counts[status] = count
        return counts

    @staticmethod
    def list_notes(
        db: Session,
        page: int = 1,
        size: int = 20,
        subject_id: int = None,
        keyword: str = None,
        status: str = None,
        user_id: int = None,
        only_published: bool = True,
    ):
        query = db.query(
            StudyNote.id, StudyNote.user_id, StudyNote.subject_id,
            StudyNote.title, StudyNote.content, StudyNote.tags,
            StudyNote.status, StudyNote.is_pinned, StudyNote.like_count,
            StudyNote.favorite_count, StudyNote.comment_count,
            StudyNote.created_at, StudyNote.updated_at,
            User.username,
        ).join(User, StudyNote.user_id == User.id)

        if only_published:
            query = query.filter(StudyNote.status == "published")
        elif status:
            query = query.filter(StudyNote.status == status)

        if subject_id:
            query = query.filter(StudyNote.subject_id == subject_id)
        if user_id:
            query = query.filter(StudyNote.user_id == user_id)
        if keyword:
            query = query.filter(
                or_(StudyNote.title.like(f"%{keyword}%"), StudyNote.content.like(f"%{keyword}%"))
            )

        total = query.count()
        items = query.order_by(
            StudyNote.is_pinned.desc(),
            StudyNote.created_at.desc(),
        ).offset((page - 1) * size).limit(size).all()
        return items, total

    @staticmethod
    def review_note(db: Session, note_id: int, action: str, reject_reason: str = None) -> Optional[StudyNote]:
        note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
        if not note:
            return None
        if action == "approve":
            note.status = "published"
            note.reject_reason = None
        elif action == "reject":
            note.status = "rejected"
            note.reject_reason = reject_reason
        NotesService._notify_author(db, note, action, reject_reason)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def ai_review_all_pending(db: Session) -> dict:
        from app.common.llm_client import chat
        import json, re

        pending_notes = db.query(StudyNote).filter(StudyNote.status == "pending").all()
        results = {"approved": 0, "rejected": 0, "failed": 0, "details": []}

        for note in pending_notes:
            subject = db.query(Subject).filter(Subject.id == note.subject_id).first()
            subject_name = subject.name if subject else "未知"

            prompt = f"""你是一个学习心得审核助手。请根据以下心得内容，判断是否应该通过审核。

审核标准：
1. 内容是否与学习相关，是否属于有效的学习心得
2. 内容质量是否合格（有实际学习内容，不是无意义文字）
3. 语言表达是否清晰、专业
4. 是否有违规内容（广告、政治敏感、人身攻击等）

心得标题：{note.title}
所属科目：{subject_name}
心得作者ID：{note.user_id}
心得内容：
{note.content[:3000]}

请给出审核建议，严格按照以下JSON格式返回：
{{
  "suggested_action": "approve" 或 "reject",
  "confidence": 0-1之间的小数,
  "reasons": ["理由1", "理由2"],
  "quality_score": 1-10之间的整数评分,
  "summary": "对心得的简要评价"
}}"""

            try:
                response = chat(
                    messages=[
                        {"role": "system", "content": "你是一个严格但公平的心得审核助手，只返回纯JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1024,
                )
                match = re.search(r"\{.*\}", response, re.DOTALL)
                data = json.loads(match.group()) if match else None
                if not data:
                    results["failed"] += 1
                    results["details"].append({"id": note.id, "title": note.title, "error": "AI返回无法解析"})
                    continue

                action = data.get("suggested_action", "reject")
                if action == "approve":
                    note.status = "published"
                    note.reject_reason = None
                    NotesService._notify_author(db, note, "approve")
                    results["approved"] += 1
                else:
                    reasons = data.get("reasons", [])
                    reason_text = reasons[:2]
                    note.status = "rejected"
                    note.reject_reason = "；".join(reason_text) if reason_text else "AI审核未通过"
                    NotesService._notify_author(db, note, "reject", note.reject_reason)
                    results["rejected"] += 1
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"id": note.id, "title": note.title, "error": str(e)})

        db.commit()
        return results

    @staticmethod
    def batch_review(db: Session, note_ids: list[int], action: str, reject_reason: str = None) -> dict:
        """Batch review notes. Returns {approved: N, rejected: N, failed: N}."""
        results = {"approved": 0, "rejected": 0, "failed": 0}
        for note_id in note_ids:
            note = NotesService.review_note(db, note_id, action, reject_reason)
            if note:
                results["approved" if action == "approve" else "rejected"] += 1
            else:
                results["failed"] += 1
        return results

    @staticmethod
    def toggle_pin(db: Session, note_id: int) -> Optional[StudyNote]:
        note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
        if not note:
            return None
        note.is_pinned = 1 - note.is_pinned
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def toggle_field(db: Session, note_id: int, user_id: int, field: str):
        model_map = {"like": NoteLike, "favorite": NoteFavorite}
        count_field = {"like": "like_count", "favorite": "favorite_count"}
        model = model_map.get(field)
        if not model:
            return None, 0

        note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
        if not note:
            return None, 0

        existing = db.query(model).filter(
            model.note_id == note_id, model.user_id == user_id
        ).first()

        if existing:
            db.delete(existing)
            setattr(note, count_field[field], getattr(note, count_field[field]) - 1)
            db.commit()
            return "removed", getattr(note, count_field[field])
        else:
            db.add(model(note_id=note_id, user_id=user_id))
            setattr(note, count_field[field], getattr(note, count_field[field]) + 1)
            db.commit()
            return "added", getattr(note, count_field[field])

    @staticmethod
    def add_comment(db: Session, note_id: int, user_id: int, content: str) -> Optional[NoteComment]:
        note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
        if not note:
            return None
        comment = NoteComment(note_id=note_id, user_id=user_id, content=content)
        db.add(comment)
        note.comment_count += 1
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def get_comments(db: Session, note_id: int):
        return db.query(
            NoteComment.id, NoteComment.note_id, NoteComment.user_id,
            NoteComment.content, NoteComment.created_at,
            User.username,
        ).join(User, NoteComment.user_id == User.id).filter(
            NoteComment.note_id == note_id
        ).order_by(NoteComment.created_at).all()
