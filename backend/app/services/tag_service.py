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
