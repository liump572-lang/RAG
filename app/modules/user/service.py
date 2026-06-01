from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models import User
from app.common.exceptions import BusinessException
from app.modules.user.schemas import CreateUserInput, UpdateUserInput, UserOut

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def list_users(db: Session, page: int = 1, size: int = 20,
               keyword: str = None, role: str = None, status: str = None) -> dict:
    query = db.query(User)

    if keyword:
        query = query.filter(
            (User.username.like(f"%{keyword}%")) | (User.email.like(f"%{keyword}%"))
        )
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)

    total = query.count()
    items = query.order_by(User.created_at.desc()) \
        .offset((page - 1) * size).limit(size).all()

    return {
        "items": [UserOut.model_validate(u) for u in items],
        "total": total,
        "page": page,
        "size": size,
    }


def create_user(db: Session, data: CreateUserInput) -> UserOut:
    if db.query(User).filter(User.username == data.username).first():
        raise BusinessException(error_code=40901, message="用户名已存在", status_code=409)
    if db.query(User).filter(User.email == data.email).first():
        raise BusinessException(error_code=40902, message="邮箱已注册", status_code=409)

    user = User(
        username=data.username,
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        role=data.role,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def update_user(db: Session, user_id: int, data: UpdateUserInput) -> UserOut:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(error_code=40410, message="用户不存在", status_code=404)

    if data.username is not None:
        user.username = data.username
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role

    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def toggle_status(db: Session, user_id: int, target_status: str, current_user_id: int) -> None:
    if user_id == current_user_id:
        raise BusinessException(error_code=40910, message="不能操作自身账号", status_code=409)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(error_code=40410, message="用户不存在", status_code=404)

    user.status = target_status
    db.commit()


def reset_password(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(error_code=40410, message="用户不存在", status_code=404)

    new_password = "123456"
    user.password_hash = pwd_context.hash(new_password)
    db.commit()
    return new_password
