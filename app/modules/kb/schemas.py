from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    subject_id: int
    title: str = Field(..., max_length=255)
    doc_type: str = Field(..., pattern="^(textbook|exam|note|supplement)$")
    year: Optional[int] = None
    question_type: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    year: Optional[int] = None
    question_type: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    subject_id: int
    subject_name: Optional[str] = None
    title: str
    file_path: str
    file_size: Optional[int] = None
    file_type: str
    doc_type: str
    parse_status: str
    error_msg: Optional[str] = None
    chunk_count: int
    year: Optional[int] = None
    question_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    char_count: int

    class Config:
        from_attributes = True


class DocumentFilter(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    subject_id: Optional[int] = None
    doc_type: Optional[str] = None
    file_type: Optional[str] = None
    parse_status: Optional[str] = None
    keyword: Optional[str] = None
