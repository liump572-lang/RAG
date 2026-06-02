import os
from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.parsers import parse_document
from app.common.utils import generate_filename
from app.config import settings
from app.models import Document, DocumentChunk, Subject


ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md"}
FILE_TYPE_MAP = {
    ".pdf": "pdf", ".docx": "docx", ".pptx": "pptx",
    ".txt": "txt", ".md": "md",
}


class KbService:

    @staticmethod
    def upload(
        db: Session,
        subject_id: int,
        title: str,
        doc_type: str,
        file,
        year: Optional[int] = None,
        question_type: Optional[str] = None,
    ) -> Document:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in FILE_TYPE_MAP:
            raise ValueError(f"Unsupported file type: {ext}")
        file_type = FILE_TYPE_MAP[ext]

        subject_dir = os.path.join(settings.upload_dir, str(subject_id))
        os.makedirs(subject_dir, exist_ok=True)

        stored_name = generate_filename(file_type)
        file_path = os.path.join(subject_dir, stored_name)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        doc = Document(
            subject_id=subject_id,
            title=title,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file_type,
            doc_type=doc_type,
            parse_status="pending",
            year=year,
            question_type=question_type,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        from app.tasks.document_parse import parse_document_task
        parse_document_task.delay(doc.id)
        return doc

    @staticmethod
    def get_document(db: Session, document_id: int) -> Optional[Document]:
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def list_documents(
        db: Session,
        page: int = 1,
        size: int = 20,
        subject_id: Optional[int] = None,
        doc_type: Optional[str] = None,
        file_type: Optional[str] = None,
        parse_status: Optional[str] = None,
        keyword: Optional[str] = None,
    ):
        query = db.query(
            Document.id,
            Document.subject_id,
            Subject.name.label("subject_name"),
            Document.title,
            Document.file_path,
            Document.file_size,
            Document.file_type,
            Document.doc_type,
            Document.parse_status,
            Document.error_msg,
            Document.chunk_count,
            Document.year,
            Document.question_type,
            Document.created_at,
            Document.updated_at,
        ).join(Subject, Document.subject_id == Subject.id, isouter=True)

        if subject_id:
            query = query.filter(Document.subject_id == subject_id)
        if doc_type:
            query = query.filter(Document.doc_type == doc_type)
        if file_type:
            query = query.filter(Document.file_type == file_type)
        if parse_status:
            query = query.filter(Document.parse_status == parse_status)
        if keyword:
            query = query.filter(Document.title.like(f"%{keyword}%"))

        total = query.count()
        items = query.order_by(Document.created_at.desc()).offset((page - 1) * size).limit(size).all()

        return items, total

    @staticmethod
    def delete_document(db: Session, document_id: int) -> bool:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.delete(doc)
        db.commit()

        from app.common.vector_store import delete_document_chunks
        delete_document_chunks(document_id)
        return True

    @staticmethod
    def reparse(db: Session, document_id: int) -> Document:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError("Document not found")

        from app.models import KgExtractionBatch, KgExtractionRun
        doc.parse_revision = (doc.parse_revision or 0) + 1
        active_run_ids = [
            row.id for row in db.query(KgExtractionRun.id).filter(
                KgExtractionRun.document_id == document_id,
                KgExtractionRun.status.in_(("queued", "running")),
            ).all()
        ]
        if active_run_ids:
            db.query(KgExtractionBatch).filter(
                KgExtractionBatch.run_id.in_(active_run_ids),
                KgExtractionBatch.status.in_(("queued", "running")),
            ).update({"status": "stale"}, synchronize_session=False)
            db.query(KgExtractionRun).filter(
                KgExtractionRun.id.in_(active_run_ids)
            ).update({"status": "canceled"}, synchronize_session=False)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        doc.parse_status = "pending"
        doc.error_msg = None
        doc.chunk_count = 0
        db.commit()

        from app.common.vector_store import delete_document_chunks
        delete_document_chunks(document_id)

        from app.tasks.document_parse import parse_document_task
        parse_document_task.delay(document_id)
        return doc

    @staticmethod
    def get_chunks(db: Session, document_id: int):
        return db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()

    @staticmethod
    def parse_and_store(db: Session, document_id: int):
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return {"status": "error", "message": "Document not found"}

        try:
            doc.parse_status = "parsing"
            db.commit()

            raw_text = parse_document(doc.file_path, doc.file_type)

            # ── Clean extracted text ──
            from app.common.parsers.cleaner import clean_parsed_text, extract_structure_metadata
            raw_text = clean_parsed_text(raw_text)

            from app.common.kg_settings import get_kg_settings
            kg_settings = get_kg_settings(db)
            min_chunk_chars = kg_settings["chunk.min_chars"]
            if len(raw_text.strip()) < min_chunk_chars:
                doc.parse_status = "success"
                doc.chunk_count = 0
                doc.error_msg = "文档内容过短，跳过解析"
                db.commit()
                return {"status": "skipped", "reason": "content too short"}

            # ── Extract structure metadata for section context ──
            structure = extract_structure_metadata(raw_text)
            sections_map = {}
            for sec in structure.get("sections", []):
                if sec["heading"]:
                    sections_map[sec["heading"]] = sec

            # ── Chunk with structure-aware sizing ──
            from app.common.parsers.chunker import recursive_character_split
            chunk_size = kg_settings["chunk.size"]
            chunk_overlap = kg_settings["chunk.overlap"]

            chunks = recursive_character_split(raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

            chunks = [c for c in chunks if len(c.strip()) >= min_chunk_chars]
            if not chunks:
                doc.parse_status = "success"
                doc.chunk_count = 0
                db.commit()
                return {"status": "skipped", "reason": "no valid chunks after filtering"}

            # ── Enrich chunks with section context ──
            enriched_chunks = _enrich_chunks_with_context(chunks, structure, doc.title)

            chunk_records = []
            chroma_chunks = []
            for i, chunk_text in enumerate(enriched_chunks):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    content=chunk_text,
                    char_count=len(chunk_text),
                )
                db.add(chunk)
                db.flush()
                chunk_records.append(chunk)
                chroma_chunks.append({
                    "id": chunk.id,
                    "document_id": doc.id,
                    "content": chunk_text,
                    "chunk_index": i,
                })

            from app.common.vector_store import add_chunks
            add_chunks(chroma_chunks)

            doc.chunk_count = len(chunks)
            doc.parse_status = "success"
            db.commit()

            from app.tasks.kg_extract import queue_document_extraction_task
            queue_document_extraction_task.delay(document_id)

            return {"status": "success", "chunk_count": len(chunks), "chunk_size": chunk_size}

        except Exception as e:
            db.rollback()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.parse_status = "failed"
                doc.error_msg = str(e)[:500]
                db.commit()
            raise e


def _enrich_chunks_with_context(chunks: list, structure: dict, doc_title: str) -> list:
    """Enrich chunk content with document title and section context."""
    if not structure or not structure.get("sections"):
        return chunks

    sections = structure["sections"]

    enriched = []
    for chunk in chunks:
        prefix_parts = []

        # Find which section this chunk belongs to
        best_section = None
        best_overlap = 0
        for sec in sections:
            if not sec.get("content"):
                continue
            # Simple overlap: count common words
            chunk_words = set(chunk[:200].split())
            sec_words = set(sec["content"][:200].split())
            overlap = len(chunk_words & sec_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_section = sec

        if best_section and best_section.get("heading"):
            prefix_parts.append(f"[{doc_title} > {best_section['heading']}]")

        if prefix_parts:
            enriched.append("\n".join(prefix_parts) + "\n" + chunk)
        else:
            enriched.append(chunk)

    return enriched
