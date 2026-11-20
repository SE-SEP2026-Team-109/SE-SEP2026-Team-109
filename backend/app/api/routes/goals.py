
"""API routes for student goals."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.goals import GoalPage
from app.services.goal_service import list_my_goals


router = APIRouter(prefix="/goals", tags=["goals"])


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

