from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole

# Matches the accounts the frontend's "explore with a demo account" buttons expect.
DEMO_PASSWORD = "Demo1234"
DEMO_USERS = [
    {"email": "admin@mentorconnect.demo", "username": "admin_demo", "name": "Programme Admin", "role": UserRole.admin},
    {"email": "coordinator@mentorconnect.demo", "username": "coordinator_demo", "name": "Kavya Reddy", "role": UserRole.coordinator},
    {"email": "student@mentorconnect.demo", "username": "student_demo", "name": "Aarav Sharma", "role": UserRole.student},
    {"email": "mentor@mentorconnect.demo", "username": "mentor_demo", "name": "Priya Nair", "role": UserRole.mentor},
]


def seed_demo_users(db: Session) -> None:
    for data in DEMO_USERS:
        if db.query(User).filter(User.email == data["email"]).first():
            continue
        db.add(
            User(
                email=data["email"],
                password=hash_password(DEMO_PASSWORD),
                role=data["role"],
                username=data["username"],
                name=data["name"],
            )
        )
    db.commit()
