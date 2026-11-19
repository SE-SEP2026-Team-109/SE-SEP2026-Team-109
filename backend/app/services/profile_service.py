from sqlalchemy.orm import Session, selectinload

from app.models.user import VerificationStatus
from app.models.user import User, UserRole, Mentor, Student
from app.schemas.profile import ProfileUpdate

def get_user_profile(db: Session, user_id: int) -> User | None:
    """Retrieves a user with their associated role profiles."""
    return (
        db.query(User)
        .options(
            selectinload(User.student),
            selectinload(User.mentor),
        )
        .filter(User.id == user_id)
        .first()
    )



def update_user_profile(db: Session, user: User, updates: ProfileUpdate) -> User:
    """Update the authenticated user's editable profile fields."""

    try:
        update_data = updates.model_dump(exclude_unset=True)

        student_data = update_data.pop("student", None)
        mentor_data = update_data.pop("mentor", None)

        # Update common user fields.
        for field, value in update_data.items():
            if value is not None:
                if field == "photo":
                    value = str(value)

                setattr(user, field, value)

        # Update student-specific fields.
        if student_data is not None:
            if user.role != UserRole.student or user.student is None:
                raise ValueError(
                    "Student profile updates are not allowed for this user"
                )

            for field, value in student_data.items():
                if value is not None:
                    setattr(user.student, field, value)

        # Update mentor-specific fields.
        if mentor_data is not None:
            if user.role != UserRole.mentor or user.mentor is None:
                raise ValueError(
                    "Mentor profile updates are not allowed for this user"
                )

            for field, value in mentor_data.items():
                if value is not None:
                    setattr(user.mentor, field, value)

        db.flush()
        db.commit()

        return get_user_profile(db, user.id)

    except Exception:
        db.rollback()
        raise


def get_public_mentor_profile(db: Session, mentor_id: int) -> User | None:
    """Retrieve a verified mentor's public profile."""

    return (
        db.query(User)
        .join(Mentor, Mentor.id == User.id)
        .filter(
            User.id == mentor_id,
            User.role == UserRole.mentor,
            Mentor.veri_status == VerificationStatus.verified,
        )
        .first()
    )


def get_student_profile_card(db: Session, student_id: int) -> User | None:
    """Retrieve a student's profile for mentor review."""

    return (
        db.query(User)
        .join(Student, Student.id == User.id)
        .filter(
            User.id == student_id,
            User.role == UserRole.student,
        )
        .first()
    )