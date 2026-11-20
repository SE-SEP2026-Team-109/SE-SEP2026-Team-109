
"""API routes for student goals."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.goals import GoalPage, GoalCreate, GoalRead, GoalStatusUpdate
from app.services.goal_service import (
    list_my_goals, create_goal, 
    update_goal, delete_goal, update_goal_status,
    list_student_goals,
)


router = APIRouter(prefix="/goals", tags=["goals"])
student_goals_router = APIRouter(tags=["goals"])


@router.get("", response_model=GoalPage)
def read_goals(
    goal_status: Literal["todo", "in_progress", "done"] | None = Query(
        default=None,
        alias="status",
        description="Filter goals by status.",
    ),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List the authenticated student's own goals."""
    return list_my_goals(
        db,
        current_user,
        goal_status,
        page,
        page_size,
    )

@router.post("", response_model=GoalRead, status_code=201)
def create_student_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a career goal for the authenticated student."""
    return create_goal(db, current_user, data)


@router.put("/{goal_id}", response_model=GoalRead)
def update_student_goal(
    goal_id: int,
    data: GoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a goal owned by the authenticated student."""
    return update_goal(db, current_user, goal_id, data)


@router.delete("/{goal_id}", status_code=204)
def delete_student_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a goal owned by the authenticated student."""
    delete_goal(db, current_user, goal_id)
    return None



@router.patch("/{goal_id}/status", response_model=GoalRead)
def update_student_goal_status(
    goal_id: int,
    data: GoalStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update the status of a goal owned by the authenticated student."""
    return update_goal_status(db, current_user, goal_id, data.status)



@student_goals_router.get("/students/{id}/goals", response_model=GoalPage)
def get_student_goals(
    id: int,
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List goals visible to the authenticated user for a student."""
    return list_student_goals(
        db=db,
        current_user=current_user,
        student_id=id,
        page=page,
        page_size=page_size,
    )


