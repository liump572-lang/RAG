from app.database import SessionLocal
from app.modules.kb.service import KbService
from app.tasks.celery_app import celery_app


@celery_app.task(name="kb_task.parse_document", bind=True, max_retries=3, default_retry_delay=30)
def parse_document_task(self, document_id: int):
    db = SessionLocal()
    try:
        result = KbService.parse_and_store(db, document_id)
        return result
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
