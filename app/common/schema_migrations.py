from sqlalchemy import inspect, text

from app.database import engine


KG_REBUILD_VERSION = "kg-v2-20260602"


def ensure_kg_schema():
    """Apply small idempotent schema additions for existing Docker volumes."""
    inspector = inspect(engine)
    columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("knowledge_points", "knowledge_relations")
        if inspector.has_table(table)
    }
    additions = {
        "knowledge_points": {
            "origin": "ENUM('legacy','manual','auto') NOT NULL DEFAULT 'legacy'",
            "confidence": "DECIMAL(4,3) NOT NULL DEFAULT 1.000",
            "review_status": "ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'",
        },
        "knowledge_relations": {
            "origin": "ENUM('legacy','manual','auto') NOT NULL DEFAULT 'legacy'",
            "confidence": "DECIMAL(4,3) NOT NULL DEFAULT 1.000",
            "review_status": "ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'",
        },
    }
    with engine.begin() as connection:
        for table, table_additions in additions.items():
            for column, definition in table_additions.items():
                if column not in columns.get(table, set()):
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def enqueue_auto_rebuild():
    """Create one rebuild record per schema version and enqueue it exactly once."""
    from app.database import SessionLocal
    from app.models import KgRebuild
    from app.tasks.kg_rebuild import rebuild_all_documents_task

    db = SessionLocal()
    try:
        existing = db.query(KgRebuild).filter(KgRebuild.version == KG_REBUILD_VERSION).first()
        if existing:
            if existing.status == "queued":
                rebuild_all_documents_task.apply_async(args=[existing.id], countdown=10)
            return existing
        rebuild = KgRebuild(version=KG_REBUILD_VERSION, status="queued")
        db.add(rebuild)
        db.commit()
        db.refresh(rebuild)
        rebuild_all_documents_task.apply_async(args=[rebuild.id], countdown=10)
        return rebuild
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()
