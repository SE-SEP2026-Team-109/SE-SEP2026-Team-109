
"""API routes for mentoring relationships."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.mentoring import MentoringRead
from app.services.mentoring_service import list_mentorings


router = APIRouter(prefix="/mentoring", tags=["mentoring"])


@router.get("", response_model=list[MentoringRead])
def read_mentorings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve the authenticated user's active mentoring relationships.

    Mentors receive their active mentees, while students receive
    their assigned mentor.

    Args:
        current_user: Authenticated and active user.
        db: Active SQLAlchemy database session.

    Returns:
        A list of active mentoring relationship DTOs.
    """
    return list_mentorings(db, current_user)
