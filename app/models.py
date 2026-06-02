from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, Boolean, JSON, DECIMAL,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT, TINYINT, BIGINT
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum("admin", "user"), nullable=False, default="user")
    status = Column(SAEnum("active", "disabled"), nullable=False, default="active")
    total_questions = Column(Integer, default=0)
    wrong_question_count = Column(Integer, default=0)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    conversations = relationship("Conversation", back_populates="user")
    wrong_questions = relationship("WrongQuestion", back_populates="user")
    study_notes = relationship("StudyNote", back_populates="user")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    sort_order = Column(Integer, nullable=False, default=0)
    is_built_in = Column(TINYINT(1), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Document(Base):
    __tablename__ = "documents"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    subject_id = Column(BIGINT, nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BIGINT)
    file_type = Column(SAEnum("pdf", "docx", "pptx", "txt", "md"), nullable=False)
    doc_type = Column(SAEnum("textbook", "exam", "note", "supplement"), nullable=False)
    parse_status = Column(SAEnum("pending", "parsing", "success", "failed"), default="pending")
    error_msg = Column(Text)
    chunk_count = Column(Integer, default=0)
    parse_revision = Column(Integer, nullable=False, default=0)
    year = Column(Integer)
    question_type = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    document_id = Column(BIGINT, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(MEDIUMTEXT, nullable=False)
    char_count = Column(Integer, default=0)
    chroma_id = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    document = relationship("Document", back_populates="chunks")


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    document_id = Column(BIGINT)
    subject_id = Column(BIGINT, nullable=False)
    year = Column(Integer, nullable=False)
    title = Column(String(255))
    question_count = Column(Integer, default=0)
    source = Column(SAEnum("uploaded", "api"), nullable=False, default="uploaded")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    exam_paper_id = Column(BIGINT, nullable=False)
    question_type = Column(SAEnum("choice", "fill", "short_answer", "calculation", "comprehensive"), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON)
    answer = Column(Text)
    analysis = Column(Text)
    knowledge_points = Column(JSON)
    difficulty = Column(TINYINT, default=3)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey("users.id"), nullable=False)
    subject_id = Column(BIGINT)
    title = Column(String(255))
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    conversation_id = Column(BIGINT, ForeignKey("conversations.id"), nullable=False)
    role = Column(SAEnum("user", "assistant", "system"), nullable=False)
    content = Column(MEDIUMTEXT, nullable=False)
    sources = Column(JSON)
    question_type = Column(SAEnum("knowledge", "exam", "note"))
    intent_confidence = Column(DECIMAL(4, 3))
    feedback_score = Column(TINYINT)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    conversation = relationship("Conversation", back_populates="messages")


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey("users.id"), nullable=False)
    exam_question_id = Column(BIGINT)
    message_id = Column(BIGINT)
    subject_id = Column(BIGINT, nullable=False)
    question_content = Column(Text, nullable=False)
    correct_answer = Column(Text)
    user_answer = Column(Text)
    error_reason = Column(SAEnum("knowledge_gap", "misunderstanding", "careless", "other"))
    difficulty = Column(TINYINT, default=3)
    mastery_status = Column(SAEnum("pending", "unmastered", "mastered"), nullable=False, default="pending")
    review_count = Column(Integer, default=0)
    mastered_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="wrong_questions")


class StudyNote(Base):
    __tablename__ = "study_notes"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey("users.id"), nullable=False)
    subject_id = Column(BIGINT, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(MEDIUMTEXT, nullable=False)
    tags = Column(JSON)
    status = Column(SAEnum("pending", "published", "rejected", "unpublished"), nullable=False, default="pending")
    reject_reason = Column(String(255))
    is_pinned = Column(TINYINT(1), nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    favorite_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="study_notes")


class NoteComment(Base):
    __tablename__ = "note_comments"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    note_id = Column(BIGINT, nullable=False)
    user_id = Column(BIGINT, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class NoteFavorite(Base):
    __tablename__ = "note_favorites"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    note_id = Column(BIGINT, nullable=False)
    user_id = Column(BIGINT, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class NoteLike(Base):
    __tablename__ = "note_likes"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    note_id = Column(BIGINT, nullable=False)
    user_id = Column(BIGINT, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(String(255))
    updated_by = Column(BIGINT)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT)
    action = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    level = Column(SAEnum("INFO", "WARN", "ERROR"), nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    detail = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    subject_id = Column(BIGINT, nullable=False)
    description = Column(Text)
    difficulty = Column(TINYINT, default=3)
    outline_path = Column(String(255))
    neo4j_node_id = Column(String(255))
    origin = Column(SAEnum("legacy", "manual", "auto"), nullable=False, default="legacy")
    confidence = Column(DECIMAL(4, 3), nullable=False, default=1.000)
    review_status = Column(SAEnum("pending", "approved", "rejected"), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class KnowledgeRelation(Base):
    __tablename__ = "knowledge_relations"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    source_node_id = Column(BIGINT, nullable=False)
    target_node_id = Column(BIGINT, nullable=False)
    relation_type = Column(SAEnum("PREREQUISITE", "NEXT", "RELATED", "CONTAINS", "CONTRAST", "EXAMINED_IN"), nullable=False)
    description = Column(String(255))
    neo4j_rel_id = Column(String(255))
    origin = Column(SAEnum("legacy", "manual", "auto"), nullable=False, default="legacy")
    confidence = Column(DECIMAL(4, 3), nullable=False, default=1.000)
    review_status = Column(SAEnum("pending", "approved", "rejected"), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KnowledgeRelationEvidence(Base):
    __tablename__ = "knowledge_relation_evidence"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    relation_id = Column(BIGINT)
    document_id = Column(BIGINT, nullable=False)
    chunk_id = Column(BIGINT)
    source_name = Column(String(100), nullable=False)
    target_name = Column(String(100), nullable=False)
    relation_type = Column(String(30), nullable=False)
    evidence_text = Column(Text)
    confidence = Column(DECIMAL(4, 3), nullable=False, default=0.800)
    prompt_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KnowledgeRelationCandidate(Base):
    __tablename__ = "knowledge_relation_candidates"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    source_node_id = Column(BIGINT, nullable=False)
    target_node_id = Column(BIGINT, nullable=False)
    relation_type = Column(String(30), nullable=False)
    description = Column(String(255))
    evidence_text = Column(Text)
    confidence = Column(DECIMAL(4, 3), nullable=False, default=0.500)
    document_id = Column(BIGINT)
    chunk_id = Column(BIGINT)
    prompt_version = Column(String(50), nullable=False)
    status = Column(SAEnum("pending", "approved", "rejected"), nullable=False, default="pending")
    reviewed_by = Column(BIGINT)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KnowledgePointSource(Base):
    __tablename__ = "knowledge_point_sources"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    knowledge_point_id = Column(BIGINT, nullable=False)
    document_id = Column(BIGINT, nullable=False)
    chunk_id = Column(BIGINT)
    raw_name = Column(String(100), nullable=False)
    canonical_name = Column(String(100), nullable=False)
    evidence_text = Column(Text)
    extraction_batch = Column(String(100))
    confidence = Column(DECIMAL(4, 3), nullable=False, default=0.800)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KgExtractionRun(Base):
    __tablename__ = "kg_extraction_runs"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    rebuild_id = Column(BIGINT)
    document_id = Column(BIGINT, nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(SAEnum("queued", "running", "success", "failed", "canceled"), nullable=False, default="queued")
    model = Column(String(100))
    batch_count = Column(Integer, nullable=False, default=0)
    processed_batches = Column(Integer, nullable=False, default=0)
    entity_count = Column(Integer, nullable=False, default=0)
    relation_count = Column(Integer, nullable=False, default=0)
    error_msg = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KgExtractionBatch(Base):
    __tablename__ = "kg_extraction_batches"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    run_id = Column(BIGINT, nullable=False)
    document_id = Column(BIGINT, nullable=False)
    parse_revision = Column(Integer, nullable=False, default=0)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    status = Column(SAEnum("queued", "dispatched", "running", "success", "failed", "stale", "canceled"), nullable=False, default="queued")
    retry_count = Column(Integer, nullable=False, default=0)
    entity_count = Column(Integer, nullable=False, default=0)
    relation_count = Column(Integer, nullable=False, default=0)
    result_json = Column(JSON)
    error_msg = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KgRebuild(Base):
    __tablename__ = "kg_rebuilds"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False, unique=True)
    status = Column(SAEnum("queued", "running", "success", "partial_failed", "failed"), nullable=False, default="queued")
    total_documents = Column(Integer, nullable=False, default=0)
    completed_documents = Column(Integer, nullable=False, default=0)
    failed_documents = Column(Integer, nullable=False, default=0)
    error_msg = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class KgSyncFailure(Base):
    __tablename__ = "kg_sync_failures"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    operation = Column(String(50), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(BIGINT)
    payload = Column(JSON)
    error_msg = Column(Text)
    status = Column(SAEnum("pending", "resolved"), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey("users.id"), nullable=False)
    type = Column(SAEnum("note_approved", "note_rejected", "system"), nullable=False, default="system")
    title = Column(String(255), nullable=False)
    content = Column(Text)
    related_id = Column(BIGINT)
    is_read = Column(TINYINT(1), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ThirdPartyApi(Base):
    __tablename__ = "third_party_apis"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    api_url = Column(String(500), nullable=False)
    api_token = Column(String(500))
    sync_interval = Column(Integer, default=3600)
    is_enabled = Column(TINYINT(1), nullable=False, default=1)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
