"""C3 Tags: list approved tags, suggest a tag, admin create/approve/reject/edit.

Ported from FastAPI ``services/tag_service.py``. Suggested tags are stored with
``t_status = False`` and nobody can select them until an admin approves (M2 C3).
"""

from sqlalchemy import select

from app import repositories as repo
from app.errors import BadRequest, Conflict, NotFound
from app.extensions import db
from app.models import Tag, TagType, UserRole
from app.schemas import TagAdminUpdate, TagCreate
from app.services.notification_service import notify_role


def list_tags(tag_type: TagType | None = None, include_pending: bool = False) -> list[Tag]:
    stmt = select(Tag)
    if not include_pending:
        stmt = stmt.where(Tag.t_status.is_(True))
    if tag_type is not None:
        stmt = stmt.where(Tag.type == tag_type)
    return list(db.session.scalars(stmt.order_by(Tag.name)))


def suggest(data: TagCreate, user) -> Tag:
    if any(t.name.lower() == data.name.lower() for t in db.session.scalars(select(Tag))):
        raise Conflict("That tag already exists or is awaiting approval.")
    tag = Tag(name=data.name, type=data.type, t_status=False)
    db.session.add(tag)
    notify_role(UserRole.admin, f"Tag suggested: {data.name}", "/admin/dashboard?tab=content")
    db.session.commit()
    return tag


def admin_create(data: TagCreate) -> Tag:
    if any(t.name.lower() == data.name.lower() for t in db.session.scalars(select(Tag))):
        raise Conflict("That tag already exists.")
    tag = Tag(name=data.name, type=data.type, t_status=True)
    db.session.add(tag)
    db.session.commit()
    return tag


def admin_update(tag_id: int, data: TagAdminUpdate) -> Tag | None:
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        raise NotFound("Tag not found.")
    if data.action == "reject":
        if tag.t_status:
            raise BadRequest("Only pending suggestions can be rejected.")
        if repo.tag_in_use(tag_id):
            raise Conflict("Cannot reject a tag that users have selected.")
        db.session.delete(tag)
        db.session.commit()
        return None
    name = data.name.strip() if data.name else tag.name
    tag_type = data.type or tag.type
    if (name != tag.name or tag_type != tag.type) and repo.tag_by_name_type(name, tag_type, exclude_id=tag.id):
        raise Conflict("A tag with this name and type already exists.")
    if data.name is None and data.type is None and data.action is None:
        raise BadRequest("No changes provided.")
    tag.name, tag.type = name, tag_type
    if data.action == "approve":
        tag.t_status = True
    db.session.commit()
    return tag
