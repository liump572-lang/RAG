from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NoteCreate(BaseModel):
    subject_id: int
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    tags: Optional[List[str]] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    subject_id: int
    title: str
    content: str
    tags: Optional[list] = None
    status: str
    reject_reason: Optional[str] = None
    is_pinned: bool
    like_count: int
    favorite_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: int
    note_id: int
    user_id: int
    username: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewInput(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    reject_reason: Optional[str] = None


class BatchReviewInput(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(approve|reject)$")
    reject_reason: str | None = None


class AiReviewResponse(BaseModel):
    suggested_action: str
    confidence: float
    reasons: list[str]
    quality_score: int
    summary: str
