from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.common.exceptions import BusinessException
from app.modules.auth.schemas import RegisterInput, TokenOutput, UserInfo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: int, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"user_id": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {"user_id": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def login(db: Session, username_or_email: str, password: str) -> dict:
    user = db.query(User).filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    if not user:
        raise BusinessException(error_code=40101, message="用户名或密码错误", status_code=401)
    if not _verify_password(password, user.password_hash):
        raise BusinessException(error_code=40102, message="用户名或密码错误", status_code=401)
    if user.status == "disabled":
        raise BusinessException(error_code=40301, message="账号已被禁用，请联系管理员", status_code=403)

    user.last_login_at = datetime.now()
    db.commit()

    access_token = _create_access_token(user.id, user.role)
    refresh_token = _create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user),
    }


def register(db: Session, data: RegisterInput) -> UserInfo:
    existing_username = db.query(User).filter(User.username == data.username).first()
    if existing_username:
        raise BusinessException(error_code=40901, message="用户名已被注册", status_code=409)

    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise BusinessException(error_code=40902, message="邮箱已被注册", status_code=409)

    user = User(
        username=data.username,
        email=data.email,
        password_hash=_hash_password(data.password),
        role="user",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserInfo.model_validate(user)


def refresh_token(db: Session, token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise BusinessException(error_code=40104, message="refresh_token 无效", status_code=401)
        user_id = payload.get("user_id")
    except JWTError:
        raise BusinessException(error_code=40104, message="refresh_token 无效或已过期", status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status == "disabled":
        raise BusinessException(error_code=40104, message="用户不存在或已被禁用", status_code=401)

    new_access_token = _create_access_token(user.id, user.role)
    return {"access_token": new_access_token, "token_type": "bearer"}


def get_current_user(db: Session, user_id: int) -> UserInfo:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(error_code=404, message="用户不存在", status_code=404)
    return UserInfo.model_validate(user)
