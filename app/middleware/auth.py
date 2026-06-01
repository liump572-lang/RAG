from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

security = HTTPBearer(auto_error=True)


def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "Token 无效或已过期"})


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_token(credentials)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail={"code": 40102, "message": "用户不存在"})
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "账号已被禁用"})
    return user
