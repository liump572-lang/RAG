from app.database import SessionLocal
from app.models import User, Subject
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    db = SessionLocal()

    try:
        if not db.query(User).first():
            admin = User(
                username="admin",
                email="admin@kqa.com",
                password_hash=pwd_context.hash("admin123"),
                role="admin",
                status="active",
            )
            db.add(admin)
            db.commit()
            print("Admin user created: admin / admin123")

        if not db.query(User).filter(User.role == "user").first():
            student = User(
                username="student",
                email="student@kqa.com",
                password_hash=pwd_context.hash("student123"),
                role="user",
                status="active",
            )
            db.add(student)
            db.commit()
            print("Student user created: student / student123")

        if not db.query(Subject).first():
            subjects = [
                Subject(name="计算机网络", description="计算机网络原理与技术", sort_order=1, is_built_in=1),
                Subject(name="操作系统", description="计算机操作系统原理", sort_order=2, is_built_in=1),
                Subject(name="数据库", description="数据库系统概论", sort_order=3, is_built_in=1),
                Subject(name="计算机组成原理", description="计算机组成与结构", sort_order=4, is_built_in=1),
                Subject(name="机器学习", description="机器学习理论与算法", sort_order=5, is_built_in=1),
                Subject(name="深度学习", description="深度学习理论与框架", sort_order=6, is_built_in=1),
                Subject(name="人工智能", description="人工智能导论", sort_order=7, is_built_in=1),
            ]
            db.add_all(subjects)
            db.commit()
            print("7 subjects seeded")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
