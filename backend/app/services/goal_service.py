
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

def update_goal(
    db: Session,
    current_user: User,
    goal_id: int,
    data: GoalCreate,
) -> TrackGoal:
    """
    Update an existing goal owned by the authenticated student.

    Args:
        db: Database session.
        current_user: Authenticated student.
        goal_id: ID of the goal to update.
        data: Updated goal details.

    Returns:
        The updated goal.

    Raises:
        HTTPException: If the user is not a student, the goal does not
            belong to them, the deadline is in the past, or the goal
            is associated with an ended mentorship.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can update goals.",
        )

    goal = (
        db.query(TrackGoal)
        .filter(
            TrackGoal.id == goal_id,
            TrackGoal.sid == current_user.id,
            TrackGoal.status != TrackGoalStatus.delete,
        )
        .first()
    )

    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found.",
        )

    # A goal associated with an ended mentorship is read-only.
    if goal.mgid is not None:
        mentorship = (
            db.query(Mentorship)
            .filter(Mentorship.id == goal.mgid)
            .first()
        )

        if mentorship is None or mentorship.status != MentorshipStatus.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Goals associated with ended mentorships cannot be updated.",
            )

    deadline = data.deadline
    if deadline.tzinfo is not None:
        deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)

    if deadline < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The goal deadline cannot be in the past.",
        )

    # Attach an active mentorship if this goal is being made
    # mentorship-only and does not already have one.
    if (
        data.visibility == GoalVisibility.mentorship_only
        and goal.mgid is None
    ):
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

        goal.mgid = active_mentorship.id

    goal.title = data.title
    goal.description = data.description
    goal.deadline = deadline
    goal.visibility = data.visibility

    try:
        db.commit()
        db.refresh(goal)
    except Exception:
        db.rollback()
        raise

    return goal

def delete_goal(
    db: Session,
    current_user: User,
    goal_id: int,
) -> None:
    """
    Delete a goal owned by the authenticated student.

    Args:
        db: Database session.
        current_user: Authenticated student.
        goal_id: ID of the goal to delete.

    Raises:
        HTTPException: If the user is not a student, the goal does not
            belong to them, or the goal is associated with an ended
            mentorship.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can delete goals.",
        )

    goal = (
        db.query(TrackGoal)
        .filter(
            TrackGoal.id == goal_id,
            TrackGoal.sid == current_user.id,
            TrackGoal.status != TrackGoalStatus.delete,
        )
        .first()
    )

    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found.",
        )

    if goal.mgid is not None:
        mentorship = (
            db.query(Mentorship)
            .filter(Mentorship.id == goal.mgid)
            .first()
        )

        if mentorship is None or mentorship.status != MentorshipStatus.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Goals associated with ended mentorships cannot be deleted.",
            )

    try:
        db.delete(goal)
        db.commit()
    except Exception:
        db.rollback()
        raise

