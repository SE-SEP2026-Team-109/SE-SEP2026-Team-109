
"""API routes for mentoring relationships."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.mentoring import MentoringRead
from app.services.mentoring_service import list_mentorings, request_mentoring_end, cancel_mentoring_end


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



@router.post("/{mentoring_id}/end", response_model=MentoringRead)
def end_mentoring(
    mentoring_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Request termination of an active mentoring relationship.

    The mentorship ends immediately if the other participant has
    already requested termination.

    Args:
        mentoring_id: ID of the mentoring relationship.
        current_user: Authenticated and active user.
        db: Active SQLAlchemy database session.

    Returns:
        The updated mentoring relationship.
    """
    return request_mentoring_end(db, current_user, mentoring_id)


@router.post("/{mentoring_id}/end/cancel", response_model=MentoringRead)
def cancel_end_mentoring(
    mentoring_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Withdraw the authenticated participant's pending mentorship end request."""
    return cancel_mentoring_end(db, current_user, mentoring_id)

