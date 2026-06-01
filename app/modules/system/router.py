from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.llm_client import invalidate_llm_client
from app.common.response import error_response, success_response
from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import SystemConfig, User
from app.modules.system.schemas import (
    SettingsUpdate,
    SystemConfigCreate,
    SystemConfigResponse,
    SystemConfigUpdate,
)
from app.modules.system.service import SystemConfigService

router = APIRouter()

AVAILABLE_MODELS = [
    {"value": "deepseek-chat", "label": "DeepSeek Chat", "description": "通用对话模型，兼顾速度与质量"},
    {"value": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "description": "极速响应，适合简单问答"},
    {"value": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "description": "旗舰模型，最强推理能力"},
    {"value": "deepseek-reasoner", "label": "DeepSeek Reasoner", "description": "深度推理，适合复杂问题"},
]


@router.get("/models")
def list_models():
    return success_response(data=AVAILABLE_MODELS)


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")

    def _db_val(key: str, fallback: str = "") -> str:
        row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        return row.config_value if row else fallback

    api_key = _db_val("deepseek_api_key", settings.deepseek_api_key)
    masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "未配置"

    return success_response(data={
        "llm_model": _db_val("llm_model", settings.llm_model),
        "api_base": _db_val("deepseek_api_base", settings.deepseek_api_base),
        "api_key_masked": masked_key,
        "embedding_model": _db_val("embedding_model", settings.embedding_model),
    })


@router.put("/settings")
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")

    def _upsert(key: str, value: str):
        row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if row:
            row.config_value = value
            row.updated_by = current_user.id
        else:
            db.add(SystemConfig(config_key=key, config_value=value, updated_by=current_user.id))

    if body.llm_model is not None:
        _upsert("llm_model", body.llm_model)
    if body.api_base is not None:
        _upsert("deepseek_api_base", body.api_base)
    if body.api_key is not None:
        _upsert("deepseek_api_key", body.api_key)

    db.commit()
    invalidate_llm_client()
    return success_response(message="设置已保存")


@router.get("/configs")
def list_configs(
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    items = SystemConfigService.list(db, keyword)
    data = [SystemConfigResponse.model_validate(c).model_dump() for c in items]
    return success_response(data=data)


@router.get("/configs/{config_id}")
def get_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    cfg = SystemConfigService.get(db, config_id)
    if not cfg:
        return error_response(404, "配置不存在")
    return success_response(data=SystemConfigResponse.model_validate(cfg).model_dump())


@router.post("/configs")
def create_config(
    body: SystemConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    existing = SystemConfigService.get_by_key(db, body.config_key)
    if existing:
        return error_response(400, "配置键已存在")
    cfg = SystemConfigService.create(db, body, current_user.id)
    return success_response(data=SystemConfigResponse.model_validate(cfg).model_dump())


@router.put("/configs/{config_id}")
def update_config(
    config_id: int,
    body: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    cfg = SystemConfigService.update(db, config_id, body, current_user.id)
    if not cfg:
        return error_response(404, "配置不存在")
    return success_response(data=SystemConfigResponse.model_validate(cfg).model_dump())


@router.delete("/configs/{config_id}")
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(403, "无权限")
    ok = SystemConfigService.delete(db, config_id)
    if not ok:
        return error_response(404, "配置不存在")
    return success_response(message="已删除")
