from datetime import datetime

from app.database import SessionLocal
from app.common.graph_store import create_node, create_relation, delete_node, delete_relation
from app.models import (
    Document, KgExtractionRun, KgRebuild, KgSyncFailure,
    KnowledgePoint, KnowledgeRelation,
)
from app.tasks.celery_app import celery_app


@celery_app.task(name="kg_task.rebuild_all_documents")
def rebuild_all_documents_task(rebuild_id: int):
    """Queue every parsed document once for a versioned graph rebuild."""
    db = SessionLocal()
    try:
        rebuild = db.query(KgRebuild).filter(KgRebuild.id == rebuild_id).first()
        if not rebuild:
            return {"status": "skipped"}
        claimed = db.query(KgRebuild).filter(
            KgRebuild.id == rebuild_id,
            KgRebuild.status.in_(("queued", "failed")),
        ).update({"status": "running", "started_at": datetime.now()}, synchronize_session=False)
        db.commit()
        if claimed != 1:
            return {"status": "skipped"}

        documents = db.query(Document).filter(Document.parse_status == "success").order_by(Document.id).all()
        rebuild = db.query(KgRebuild).filter(KgRebuild.id == rebuild_id).first()
        rebuild.total_documents = len(documents)
        db.commit()

        from app.tasks.kg_extract import queue_document_extraction_task
        for document in documents:
            existing = db.query(KgExtractionRun).filter(
                KgExtractionRun.rebuild_id == rebuild.id,
                KgExtractionRun.document_id == document.id,
            ).first()
            if existing:
                continue
            run = KgExtractionRun(
                rebuild_id=rebuild.id,
                document_id=document.id,
                version=rebuild.version,
                status="queued",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            queue_document_extraction_task.delay(document.id, run.id)

        if not documents:
            rebuild.status = "success"
            rebuild.finished_at = datetime.now()
            db.commit()
        return {"status": "queued", "documents": len(documents)}
    finally:
        db.close()


@celery_app.task(name="kg_task.retry_neo4j_sync")
def retry_neo4j_sync_task(limit: int = 100):
    """Replay failed Neo4j writes from MySQL, which remains the source of truth."""
    db = SessionLocal()
    resolved = 0
    try:
        failures = db.query(KgSyncFailure).filter(KgSyncFailure.status == "pending").order_by(KgSyncFailure.id).limit(limit).all()
        for failure in failures:
            try:
                if failure.entity_type == "node":
                    if failure.operation == "delete":
                        delete_node(failure.entity_id)
                    else:
                        point = db.query(KnowledgePoint).filter(KnowledgePoint.id == failure.entity_id).first()
                        if point:
                            create_node(point.id, point.name, point.subject_id)
                elif failure.entity_type == "relation":
                    if failure.operation == "delete":
                        payload = failure.payload or {}
                        delete_relation(payload["source_id"], payload["target_id"], payload["relation_type"])
                    else:
                        relation = db.query(KnowledgeRelation).filter(KnowledgeRelation.id == failure.entity_id).first()
                        if not relation:
                            continue
                        create_relation(
                            relation.source_node_id,
                            relation.target_node_id,
                            relation.relation_type,
                            relation.description,
                        )
                failure.status = "resolved"
                resolved += 1
            except Exception as exc:
                failure.error_msg = str(exc)[:1000]
        db.commit()
        return {"status": "success", "resolved": resolved}
    finally:
        db.close()
