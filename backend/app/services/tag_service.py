from sqlalchemy.orm import Session, joinedload
from app.models.user import User, UserRole
from app.models.enums import TagType
from app.models.tags import Tag, UserTag


def get_approved_tags(
    db: Session,
    tag_type: TagType | None = None,
) -> list[Tag]:
    """Retrieve approved tags, optionally filtered by type."""

    query = db.query(Tag).filter(Tag.t_status.is_(True))

    if tag_type is not None:
        query = query.filter(Tag.type == tag_type)

    return query.order_by(Tag.name.asc()).all()

def update_profile_tags(
    db: Session,
    user: User,
    tags: list,
) -> list[UserTag]:
    try:
        tag_ids = [item.tag_id for item in tags]

        if len(tag_ids) != len(set(tag_ids)):
            raise ValueError("Duplicate tag IDs are not allowed")

        if user.role == UserRole.student:
            if len(tags) > 5:
                raise ValueError("Students can select up to 5 tags")

        elif user.role == UserRole.mentor:
            if len(tags) > 6:
                raise ValueError("Mentors can select up to 6 tags")

        else:
            raise ValueError("Only students and mentors can select profile tags")

        approved_tags = (
            db.query(Tag)
            .filter(
                Tag.id.in_(tag_ids),
                Tag.t_status.is_(True),
            )
            .all()
        ) if tag_ids else []

        if len(approved_tags) != len(tag_ids):
            raise ValueError("One or more tags are invalid or not approved")

        # Replace the user's existing tag selections.
        db.query(UserTag).filter(
            UserTag.uid == user.id
        ).delete(synchronize_session=False)

        for item in tags:
            db.add(
                UserTag(
                    uid=user.id,
                    tag_id=item.tag_id,
                    want_to_learn=item.want_to_learn,
                    skill_level=item.skill_level,
                )
            )

        db.commit()

        return (
            db.query(UserTag)
            .options(joinedload(UserTag.tag))
            .filter(UserTag.uid == user.id)
            .all()
        )

    except Exception:
        db.rollback()
        raise


def suggest_tag(
    db: Session,
    name: str,
    tag_type: TagType,
) -> Tag:
    try:
        existing_tag = (
            db.query(Tag)
            .filter(
                Tag.name.ilike(name),
                Tag.type == tag_type,
            )
            .first()
        )

        if existing_tag:
            raise ValueError(
                "A tag with this name and type already exists or is pending approval"
            )

        suggestion = Tag(
            name=name,
            type=tag_type,
            t_status=False,
        )

        db.add(suggestion)
        db.commit()
        db.refresh(suggestion)

        return suggestion

    except Exception:
        db.rollback()
        raise



def create_admin_tag(
    db: Session,
    name: str,
    tag_type: TagType,
) -> Tag:
    try:
        existing = (
            db.query(Tag)
            .filter(
                Tag.name.ilike(name),
                Tag.type == tag_type,
            )
            .first()
        )

        if existing:
            raise ValueError("A tag with this name and type already exists")

        tag = Tag(
            name=name,
            type=tag_type,
            t_status=True,
        )

        db.add(tag)
        db.commit()
        db.refresh(tag)

        return tag

    except Exception:
        db.rollback()
        raise


def update_admin_tag(
    db: Session,
    tag_id: int,
    updates,
) -> Tag | None:
    try:
        tag = db.get(Tag, tag_id)

        if tag is None:
            raise LookupError("Tag not found")

        update_data = updates.model_dump(exclude_unset=True)
        action = update_data.pop("action", None)
        name = update_data.get("name", tag.name)
        tag_type = update_data.get("type", tag.type)

        if action == "reject":
            if tag.t_status:
                raise ValueError("Only pending suggestions can be rejected")

            linked_user_tag = (
                db.query(UserTag)
                .filter(UserTag.tag_id == tag_id)
                .first()
            )

            if linked_user_tag:
                raise ValueError("Cannot reject a tag that users have selected")

            db.delete(tag)
            db.commit()
            return None

        if name != tag.name or tag_type != tag.type:
            existing = (
                db.query(Tag)
                .filter(
                    Tag.name.ilike(name),
                    Tag.type == tag_type,
                    Tag.id != tag_id,
                )
                .first()
            )

            if existing:
                raise ValueError(
                    "A tag with this name and type already exists"
                )

        tag.name = name
        tag.type = tag_type

        if action == "approve":
            tag.t_status = True

        if not update_data and action is None:
            raise ValueError("No updates provided")

        db.commit()
        db.refresh(tag)

        return tag

    except Exception:
        db.rollback()
        raise

