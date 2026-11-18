from sqlalchemy.orm import Session, selectinload

from app.models.user import User


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
