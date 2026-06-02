from datetime import datetime

from sqlalchemy import inspect, text

from app.database import engine


KG_REBUILD_VERSION = "kg-v4-parallel-extraction"
PREVIOUS_KG_REBUILD_VERSION = "kg-v3-physical-semantic"


def ensure_kg_schema():
    """Apply small idempotent schema additions for existing Docker volumes."""
    inspector = inspect(engine)
    columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("documents", "knowledge_points", "knowledge_relations", "kg_extraction_runs")
        if inspector.has_table(table)
    }
    additions = {
        "documents": {
            "parse_revision": "INT NOT NULL DEFAULT 0",
        },
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
        "kg_extraction_runs": {
            "status": "ENUM('queued','running','success','failed','canceled') NOT NULL DEFAULT 'queued'",
        },
    }
    with engine.begin() as connection:
        for table, table_additions in additions.items():
            for column, definition in table_additions.items():
                if column not in columns.get(table, set()):
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        if inspector.has_table("kg_extraction_runs"):
            connection.execute(text("""
                ALTER TABLE kg_extraction_runs
                MODIFY COLUMN status ENUM('queued','running','success','failed','canceled')
                NOT NULL DEFAULT 'queued'
            """))
        if inspector.has_table("kg_extraction_batches"):
            connection.execute(text("""
                ALTER TABLE kg_extraction_batches
                MODIFY COLUMN status ENUM('queued','dispatched','running','success','failed','stale','canceled')
                NOT NULL DEFAULT 'queued'
            """))
        defaults = {
            "chunk.min_chars": ("120", "文档最小切块大小"),
            "chunk.size": ("512", "文档目标切块大小"),
            "chunk.overlap": ("128", "文档切块重叠量"),
            "kg.relation_candidate_threshold": ("0.2", "关系候选保留阈值"),
            "kg.relation_auto_threshold": ("0.8", "关系自动入图阈值"),
            "kg.batch_chunks": ("20", "每个并行抽取分段包含的切块数"),
            "kg.max_parallel_batches": ("8", "图谱抽取最大并行分段数"),
            "kg.batch_retry_limit": ("2", "图谱抽取分段失败重试次数"),
            "kg.cross_relation_top_k": ("30", "跨文档关系候选召回数量"),
        }
        for key, (value, description) in defaults.items():
            connection.execute(text("""
                INSERT IGNORE INTO system_configs (config_key, config_value, description)
                VALUES (:key, :value, :description)
            """), {"key": key, "value": value, "description": description})


def enqueue_auto_rebuild():
    """Create one rebuild record per schema version and enqueue it exactly once."""
    from app.database import SessionLocal
    from app.models import KgRebuild
    from app.tasks.kg_rebuild import rebuild_all_documents_task

    db = SessionLocal()
    try:
        previous = db.query(KgRebuild).filter(KgRebuild.version == PREVIOUS_KG_REBUILD_VERSION).first()
        if previous and previous.status not in {"success", "partial_failed", "failed"}:
            from app.models import KgExtractionRun
            db.query(KgExtractionRun).filter(
                KgExtractionRun.rebuild_id == previous.id,
                KgExtractionRun.status.in_(("queued", "running")),
            ).update({"status": "canceled"}, synchronize_session=False)
            previous.status = "partial_failed"
            previous.finished_at = datetime.now()
            db.commit()
        existing = db.query(KgRebuild).filter(KgRebuild.version == KG_REBUILD_VERSION).first()
        if existing:
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
