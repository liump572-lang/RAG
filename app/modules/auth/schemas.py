from pydantic import BaseModel, Field
from typing import Optional


class LoginInput(BaseModel):
    username: str = Field(..., min_length=1, description="用户名或邮箱")
    password: str = Field(..., min_length=1, description="密码")


class RegisterInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., max_length=100, description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    role: str = Field(default="user", pattern="^(admin|user)$", description="角色")


class TokenOutput(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    status: str

    class Config:
        from_attributes = True


class RefreshInput(BaseModel):
    refresh_token: str
