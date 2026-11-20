
"""Business logic for retrieving student goals."""

from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.enums import (
    GoalVisibility,
    MentorshipStatus,
    TrackGoalStatus,
    UserRole,
)
from app.models.goals import TrackGoal
from app.models.user import User, Student
from app.models.mentoring import Mentorship, Request
from app.schemas.goals import GoalCreate


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


def create_goal(
    db: Session,
    current_user: User,
    data: GoalCreate,
) -> TrackGoal:
    """
    Create a career goal for the authenticated student.

    Args:
        db: Database session.
        current_user: Authenticated user creating the goal.
        data: Goal details supplied in the request body.

    Returns:
        The newly created goal.

    Raises:
        HTTPException: If the user is not a student, the student
            profile does not exist, the deadline is in the past,
            or mentorship-only visibility has no active mentorship.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can create goals.",
        )

    student = db.query(Student).filter(
        Student.id == current_user.id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    # Compare both timezone-aware and naive datetimes consistently.
    deadline = data.deadline
    if deadline.tzinfo is not None:
        deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)

    if deadline < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The goal deadline cannot be in the past.",
        )

    mentoring_id = None

    if data.visibility == GoalVisibility.mentorship_only:
        active_mentorship = (
            db.query(Mentorship)
            .join(Request, Mentorship.rid == Request.id)
            .filter(
                Request.sid == current_user.id,
                Mentorship.status == MentorshipStatus.active,
            )
            .first()
        )

        if active_mentorship is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mentorship-only visibility requires an active mentorship.",
            )

        mentoring_id = active_mentorship.id

    goal = TrackGoal(
        sid=current_user.id,
        mgid=mentoring_id,
        title=data.title,
        description=data.description,
        status=TrackGoalStatus.todo,
        deadline=deadline,
        visibility=data.visibility,
    )

    db.add(goal)

    try:
        db.commit()
        db.refresh(goal)
    except Exception:
        db.rollback()
        raise

    return goal

