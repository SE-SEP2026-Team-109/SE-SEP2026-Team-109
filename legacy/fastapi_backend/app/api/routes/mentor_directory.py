from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.mentor_directory import MentorDirectoryResponse
from app.services.mentor_directory_service import get_mentor_directory


router = APIRouter(prefix="/mentors", tags=["mentor directory"])


@router.get("", response_model=MentorDirectoryResponse)
def read_mentor_directory(
    q: str | None = Query(default=None, description="Search mentor name, designation or company"),
    industry: str | None = Query(default=None, description="Filter by domain tag"),
    area: str | None = Query(default=None, description="Filter by expertise tag"),
    expertise: str | None = Query(default=None, description="Filter by skill or tool tag"),
    has_slots: bool | None = Query(default=None, description="Filter mentors by available capacity"),
    sort: Literal["free_slots", "experience", "best_match"] = Query(
        default="free_slots",
        description="Sort by available slots, experience or matching tags",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Browse verified mentors.

    Requires authentication. Results include public mentor details,
    approved tags, calculated free slots and request-button eligibility.
    """

    return get_mentor_directory(
        db=db,
        current_user=current_user,
        q=q,
        industry=industry,
        area=area,
        expertise=expertise,
        has_slots=has_slots,
        sort=sort,
        page=page,
        page_size=page_size,
    )