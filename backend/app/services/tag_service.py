from sqlalchemy.orm import Session

from app.models.enums import TagType
from app.models.tags import Tag


def get_approved_tags(
    db: Session,
    tag_type: TagType | None = None,
) -> list[Tag]:
    """Retrieve approved tags, optionally filtered by type."""

    query = db.query(Tag).filter(Tag.t_status.is_(True))

    if tag_type is not None:
        query = query.filter(Tag.type == tag_type)

    return query.order_by(Tag.name.asc()).all()