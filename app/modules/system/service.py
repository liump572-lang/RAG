from typing import Optional

from sqlalchemy.orm import Session

from app.models import SystemConfig


def _validate_kg_config_change(db: Session, key: str, value: str):
    from app.common.kg_settings import KG_SETTING_DEFAULTS, validate_kg_settings
    if key not in KG_SETTING_DEFAULTS:
        return
    values = dict(KG_SETTING_DEFAULTS)
    rows = db.query(SystemConfig).filter(SystemConfig.config_key.in_(KG_SETTING_DEFAULTS)).all()
    for row in rows:
        values[row.config_key] = row.config_value
    values[key] = value
    validate_kg_settings(values)


class SystemConfigService:

    @staticmethod
    def list(db: Session, keyword: str = None):
        query = db.query(SystemConfig)
        if keyword:
            query = query.filter(SystemConfig.config_key.like(f"%{keyword}%"))
        return query.order_by(SystemConfig.id).all()

    @staticmethod
    def get(db: Session, config_id: int) -> Optional[SystemConfig]:
        return db.query(SystemConfig).filter(SystemConfig.id == config_id).first()

    @staticmethod
    def get_by_key(db: Session, key: str) -> Optional[SystemConfig]:
        return db.query(SystemConfig).filter(SystemConfig.config_key == key).first()

    @staticmethod
    def create(db: Session, data, user_id: int) -> SystemConfig:
        _validate_kg_config_change(db, data.config_key, data.config_value)
        cfg = SystemConfig(
            config_key=data.config_key,
            config_value=data.config_value,
            description=data.description,
            updated_by=user_id,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def update(db: Session, config_id: int, data, user_id: int) -> Optional[SystemConfig]:
        cfg = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
        if not cfg:
            return None
        _validate_kg_config_change(db, cfg.config_key, data.config_value)
        cfg.config_value = data.config_value
        if data.description is not None:
            cfg.description = data.description
        cfg.updated_by = user_id
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def delete(db: Session, config_id: int) -> bool:
        cfg = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
        if not cfg:
            return False
        db.delete(cfg)
        db.commit()
        return True
