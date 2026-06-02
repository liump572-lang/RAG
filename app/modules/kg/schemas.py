from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class KnowledgePointCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    subject_id: int
    description: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)


class KnowledgePointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[int] = None


class KnowledgePointResponse(BaseModel):
    id: int
    name: str
    subject_id: int
    description: Optional[str] = None
    difficulty: int
    outline_path: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    origin: str = "legacy"
    confidence: float = 1.0
    review_status: str = "pending"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelationCreate(BaseModel):
    source_id: int
    target_id: int
    relation_type: str = Field(..., pattern="^(PREREQUISITE|NEXT|RELATED|CONTAINS|CONTRAST|EXAMINED_IN)$")
    description: Optional[str] = None


class RelationResponse(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    relation_type: str
    description: Optional[str] = None
    origin: str = "legacy"
    confidence: float = 1.0
    review_status: str = "pending"

    class Config:
        from_attributes = True


class SubgraphResponse(BaseModel):
    nodes: list
    edges: list


class DocumentGenerateRequest(BaseModel):
    subject_id: int
    doc_type: str = Field(default="study_guide", pattern="^(study_guide|exam_paper|summary|outline)$")
