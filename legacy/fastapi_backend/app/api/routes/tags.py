from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import TagType
from app.models.user import User, UserRole
from app.schemas.tags import (
    TagRead, TagSuggestionCreate,
    TagSuggestionRead, TagAdminCreate,
    TagAdminRead, TagAdminUpdate,
)
from app.services.tag_service import (
    get_approved_tags, suggest_tag,
    create_admin_tag, update_admin_tag,
)


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

@router.post(
    "/admin",
    response_model=TagAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tag(
    payload: TagAdminCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        return create_admin_tag(
            db=db,
            name=payload.name,
            tag_type=payload.type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/admin/{tag_id}",
    response_model=TagAdminRead,
    responses={204: {"description": "Tag suggestion permanently rejected"}},
)
def update_tag(
    tag_id: int,
    payload: TagAdminUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        result = update_admin_tag(db, tag_id, payload)

        if result is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        return result

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

