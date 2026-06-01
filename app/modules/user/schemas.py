from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class CreateUserInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UpdateUserInput(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    status: str
    total_questions: int = 0
    wrong_question_count: int = 0
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
