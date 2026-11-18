from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import TagType
from app.models.user import User
from app.schemas.tags import TagRead, TagSuggestionCreate, TagSuggestionRead
from app.services.tag_service import get_approved_tags, suggest_tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def read_tags(
    tag_type: TagType | None = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return get_approved_tags(db, tag_type)

@router.post(
    "/suggest",
    response_model=TagSuggestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tag_suggestion(
    payload: TagSuggestionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return suggest_tag(
            db=db,
            name=payload.name,
            tag_type=payload.type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc