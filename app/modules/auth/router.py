from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.common.response import success_response
from app.middleware.auth import verify_token, security
from app.modules.auth.schemas import LoginInput, RegisterInput, RefreshInput
from app.modules.auth import service as auth_service

router = APIRouter()


@router.post("/login")
def login(input: LoginInput, db: Session = Depends(get_db)):
    result = auth_service.login(db, input.username, input.password)
    return success_response(data=result)


@router.post("/register")
def register(input: RegisterInput, db: Session = Depends(get_db)):
    user = auth_service.register(db, input)
    return success_response(data=user)


@router.post("/refresh")
def refresh(input: RefreshInput, db: Session = Depends(get_db)):
    result = auth_service.refresh_token(db, input.refresh_token)
    return success_response(data=result)


@router.get("/me")
def me(credentials=Depends(security), db: Session = Depends(get_db)):
    payload = verify_token(credentials)
    user = auth_service.get_current_user(db, payload["user_id"])
    return success_response(data=user)
