"""C2 Profile: own profile, public mentor profile, student card, tag selection.

Ported from FastAPI ``services/profile_service.py`` and the logic that sat in
``api/routes/profile.py``. CHANGES: mentors can toggle ``pause`` (US-04), capacity
is limited to 1-10 (US-03/04 acceptance criteria), and a mentor can only open the
card of a student who sent them a request (M2: "card for a mentor reviewing a request").
"""

from flask import current_app

from app import repositories as repo
from app.errors import BadRequest, Conflict, NotFound
from app.extensions import db
from app.models import Tag, User, UserRole, UserStatus, UserTag, VerificationStatus
from app.schemas import ProfileTagsUpdate, ProfileUpdate


def _check_photo(photo: str) -> str | None:
    if photo == "":
        return None
    if not (photo.startswith("https://") or photo.startswith("data:image/")):
        raise BadRequest("Photo must be an https:// link or an uploaded image.")
    if len(photo) > current_app.config["PHOTO_MAX_CHARS"]:
        raise BadRequest("The image is too large. Choose a smaller picture.")
    return photo


def update_profile(user: User, data: ProfileUpdate) -> User:
    fields = data.model_dump(exclude_unset=True)
    student = fields.pop("student", None)
    mentor = fields.pop("mentor", None)
    try:
        if "username" in fields and fields["username"] and fields["username"] != user.username:
            other = repo.get_user_by_username(fields["username"])
            if other and other.id != user.id:
                raise Conflict("That username is already taken.")
            user.username = fields["username"]
        if fields.get("name"):
            user.name = fields["name"].strip()
        if "phone" in fields:
            user.phone = (fields["phone"] or "").strip() or None
        if "photo" in fields:
            user.photo = _check_photo(fields["photo"] or "")

        if student is not None:
            if user.role != UserRole.student or user.student is None:
                raise BadRequest("Student profile fields cannot be updated for this account.")
            clear_level = student.pop("clear_courselevel", False)
            for key, value in student.items():
                if value is not None:
                    setattr(user.student, key, value)
            if clear_level:
                user.student.courselevel = None
        if mentor is not None:
            if user.role != UserRole.mentor or user.mentor is None:
                raise BadRequest("Mentor profile fields cannot be updated for this account.")
            for key, value in mentor.items():
                if value is not None:
                    if key == "support_types":
                        value = [s.strip() for s in value if s and s.strip()]
                    setattr(user.mentor, key, value)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user


def set_tags(user: User, data: ProfileTagsUpdate) -> User:
    """Replace the user's tag selection. Only approved tags; students <= 5, mentors <= 6 (M2 C3)."""
    if user.role == UserRole.student:
        limit = current_app.config["STUDENT_MAX_TAGS"]
    elif user.role == UserRole.mentor:
        limit = current_app.config["MENTOR_MAX_TAGS"]
    else:
        raise BadRequest("Only students and mentors can select profile tags.")

    if data.names is not None:
        names = list(dict.fromkeys(n.strip() for n in data.names if n.strip()))
        tags = repo.approved_tags_by_name(names)
        if len(tags) != len(names):
            raise BadRequest("One or more tags are invalid or not approved.")
        selections = [(t.id, False, None) for t in tags]
    else:
        items = data.tags or []
        ids = [i.tag_id for i in items]
        if len(ids) != len(set(ids)):
            raise BadRequest("Duplicate tags are not allowed.")
        approved = {t.id for t in db.session.query(Tag).filter(Tag.id.in_(ids), Tag.t_status.is_(True))} if ids else set()
        if approved != set(ids):
            raise BadRequest("One or more tags are invalid or not approved.")
        selections = [(i.tag_id, i.want_to_learn, i.skill_level) for i in items]

    if len(selections) > limit:
        raise BadRequest(f"You can select up to {limit} tags.")
    try:
        db.session.query(UserTag).filter(UserTag.uid == user.id).delete(synchronize_session=False)
        for tag_id, want, level in selections:
            db.session.add(UserTag(uid=user.id, tag_id=tag_id, want_to_learn=want, skill_level=level))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    db.session.refresh(user)
    return user


def public_mentor(viewer: User, mentor_id: int) -> User:
    """Verified, active mentors only. Anything else is a 404 (no probing)."""
    user = repo.get_user(mentor_id)
    if (user is None or user.role != UserRole.mentor or user.mentor is None or user.status != UserStatus.active
            or user.mentor.veri_status != VerificationStatus.verified):
        # Admins may open unverified mentors (they verify them).
        if not (viewer.role == UserRole.admin and user is not None and user.role == UserRole.mentor):
            raise NotFound("Mentor profile not found.")
    return user


def student_card(viewer: User, student_id: int) -> User:
    user = repo.get_user(student_id)
    if user is None or user.role != UserRole.student or user.student is None:
        raise NotFound("Student profile not found.")
    if viewer.role == UserRole.mentor and not repo.has_request_between(student_id, viewer.id):
        raise NotFound("Student profile not found.")
    return user
