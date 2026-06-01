from typing import Optional

from sqlalchemy.orm import Session

from app.models import SystemConfig


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
