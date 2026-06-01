from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SettingsUpdate(BaseModel):
    llm_model: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None


class SystemConfigCreate(BaseModel):
    config_key: str = Field(..., max_length=100)
    config_value: str
    description: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    config_value: str
    description: Optional[str] = None


class SystemConfigResponse(BaseModel):
    id: int
    config_key: str
    config_value: str
    description: Optional[str] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
