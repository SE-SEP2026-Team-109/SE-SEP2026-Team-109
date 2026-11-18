from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import TagType
from app.models.user import User
from app.schemas.tags import TagRead
from app.services.tag_service import get_approved_tags

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def read_tags(
    tag_type: TagType | None = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return get_approved_tags(db, tag_type)