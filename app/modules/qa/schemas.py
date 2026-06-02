from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AskInput(BaseModel):
    conversation_id: Optional[int] = Field(default=None, description="对话ID，为空则创建新对话")
    subject_id: Optional[int] = Field(default=None, description="科目ID")
    question: str = Field(..., min_length=1, max_length=50000, description="用户问题")


class AskOutput(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: List[dict] = []


class ConversationResponse(BaseModel):
    id: int
    title: str
    message_count: int
    subject_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list] = None
    question_type: Optional[str] = None
    feedback_score: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    subject_id: Optional[int] = None
    title: str = "新对话"


class FeedbackInput(BaseModel):
    score: int = Field(..., ge=1, le=5, description="评分 1-5")
    add_to_wrong: bool = Field(default=False, description="是否加入错题本")
    correct_answer: Optional[str] = Field(default=None, description="正确答案")
    user_answer: Optional[str] = Field(default=None, description="用户答案")
    error_reason: Optional[str] = Field(default=None, description="错误原因")
    difficulty: Optional[int] = Field(default=3, ge=1, le=5, description="难度 1-5")
