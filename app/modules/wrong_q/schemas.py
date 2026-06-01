from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WrongQuestionCreate(BaseModel):
    subject_id: int
    question_content: str
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    error_reason: Optional[str] = None
    difficulty: Optional[int] = Field(default=3, ge=1, le=5)
    exam_question_id: Optional[int] = None
    message_id: Optional[int] = None


class WrongQuestionUpdate(BaseModel):
    subject_id: Optional[int] = None
    question_content: Optional[str] = None
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    error_reason: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    mastery_status: Optional[str] = None


class WrongQuestionResponse(BaseModel):
    id: int
    user_id: int
    subject_id: int
    question_content: str
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    error_reason: Optional[str] = None
    difficulty: int
    mastery_status: str
    review_count: int
    mastered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WrongQuestionListRow(BaseModel):
    id: int
    subject_id: int
    question_content: str
    error_reason: Optional[str] = None
    difficulty: int
    mastery_status: str
    review_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PracticeRequest(BaseModel):
    subject_id: Optional[int] = None
    count: int = Field(default=10, ge=1, le=50)
    mastery_status: Optional[str] = None


class ReviewInput(BaseModel):
    is_correct: bool
    mastery_status: Optional[str] = None


class StatsOutput(BaseModel):
    total: int
    by_subject: List[dict]
    by_reason: List[dict]
    by_status: List[dict]
