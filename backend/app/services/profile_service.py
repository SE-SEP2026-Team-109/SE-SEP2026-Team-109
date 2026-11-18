from sqlalchemy.orm import Session, selectinload

from app.models.user import User
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

    update_data = updates.model_dump(exclude_unset=True)

    student_data = update_data.pop("student", None)
    mentor_data = update_data.pop("mentor", None)

    # Update common user fields.
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    # Update student-specific fields.
    if student_data is not None:
        if user.role != "student" or user.student is None:
            raise ValueError("Student profile updates are not allowed for this user")

        for field, value in student_data.items():
            if value is not None:
                setattr(user.student, field, value)

    # Update mentor-specific fields.
    if mentor_data is not None:
        if user.role != "mentor" or user.mentor is None:
            raise ValueError("Mentor profile updates are not allowed for this user")

        for field, value in mentor_data.items():
            if value is not None:
                setattr(user.mentor, field, value)

    db.commit()
    db.refresh(user)

    return get_user_profile(db, user.id)
