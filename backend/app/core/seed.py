
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, Student, Mentor, UserRole
from app.models.enums import (
    Course,
    CourseLevel,
    VerificationStatus,
)

DEMO_PASSWORD = "Demo1234"

DEMO_USERS = [
    {
        "email": "admin@mentorconnect.demo",
        "username": "admin_demo",
        "name": "Programme Admin",
        "role": UserRole.admin,
    },
    {
        "email": "coordinator@mentorconnect.demo",
        "username": "coordinator_demo",
        "name": "Kavya Reddy",
        "role": UserRole.coordinator,
    },
    {
        "email": "student@mentorconnect.demo",
        "username": "student_demo",
        "name": "Aarav Sharma",
        "role": UserRole.student,
    },
    {
        "email": "mentor@mentorconnect.demo",
        "username": "mentor_demo",
        "name": "Priya Nair",
        "role": UserRole.mentor,
    },
]


def seed_demo_users(db: Session) -> None:
    for data in DEMO_USERS:
        user = db.query(User).filter(
            User.email == data["email"]
        ).first()

        # Create the user if it does not already exist.
        if user is None:
            user = User(
                email=data["email"],
                password=hash_password(DEMO_PASSWORD),
                role=data["role"],
                username=data["username"],
                name=data["name"],
            )
            db.add(user)
            db.flush()

        # Create the student profile if it is missing.
        if user.role == UserRole.student and user.student is None:
            db.add(
                Student(
                    id=user.id,
                    course=Course.data_science_and_applications,
                )
            )

        # Create the mentor profile if it is missing.
        if user.role == UserRole.mentor and user.mentor is None:
            db.add(
                Mentor(
                    id=user.id,
                    iitm_program=Course.data_science_and_applications,
                    level_completed=CourseLevel.bsc_degree,
                    designation="Senior Data Analyst",
                    company="MentorConnect",
                    bio="Experienced data professional helping students build their careers.",
                    experience=5.0,
                    capacity=2,
                    veri_status=VerificationStatus.verified,
                )
            )

    db.commit()
