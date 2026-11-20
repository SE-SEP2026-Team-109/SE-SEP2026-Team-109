
"""Business logic for retrieving student goals."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import TrackGoalStatus, UserRole
from app.models.goals import TrackGoal
from app.models.user import User


def list_my_goals(
    db: Session,
    current_user: User,
    goal_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    List the authenticated student's goals with optional filtering.

    Args:
        db: Database session.
        current_user: Authenticated user.
        goal_status: Optional goal status filter.
        page: Page number, starting from 1.
        page_size: Number of goals per page.

    Returns:
        A dictionary containing the goals and pagination metadata.

    Raises:
        HTTPException: If the authenticated user is not a student.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their own goals.",
        )

    query = db.query(TrackGoal).filter(
        TrackGoal.sid == current_user.id,
        TrackGoal.status != TrackGoalStatus.delete,
    )

    if goal_status is not None:
        query = query.filter(
            TrackGoal.status == TrackGoalStatus(goal_status)
        )

    total = query.count()

    goals = (
        query
        .order_by(TrackGoal.created_on.desc(), TrackGoal.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": goals,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
