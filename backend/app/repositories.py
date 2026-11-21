"""Repository layer: the reusable database queries (M2 "Queries that enforce rules").

Services call these instead of writing the same query in several places. Each
function only reads; services decide what to do with the result and own the
transaction (commit/rollback).
"""

from datetime import datetime

from sqlalchemy import func, select, update

from app.extensions import db
from app.models import (
    Mentor, Mentorship, MentorshipStatus, Notification, Request, RequestStatus, Tag, User, UserRole, UserTag,
)

# ---------------- users ----------------

def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_user_by_email(email: str) -> User | None:
    return db.session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def get_user_by_username(username: str) -> User | None:
    return db.session.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))


def users_with_role(role: UserRole) -> list[User]:
    return list(db.session.scalars(select(User).where(User.role == role)))


# ---------------- requests and mentorships ----------------

def get_request(request_id: int) -> Request | None:
    return db.session.get(Request, request_id)


def count_pending_requests(student_id: int) -> int:
    """3-request limit (US-06). Counted, so expiry and withdrawal free the quota automatically."""
    return db.session.scalar(
        select(func.count(Request.id)).where(Request.sid == student_id, Request.status == RequestStatus.pending)
    ) or 0


def pending_request_between(student_id: int, mentor_id: int) -> Request | None:
    return db.session.scalar(
        select(Request).where(Request.sid == student_id, Request.mid == mentor_id, Request.status == RequestStatus.pending)
    )


def count_active_mentorships(mentor_id: int) -> int:
    """Free slots = capacity - active mentorships (computed, never stored; M2 C4)."""
    return db.session.scalar(
        select(func.count(Mentorship.id)).join(Request, Request.id == Mentorship.rid)
        .where(Request.mid == mentor_id, Mentorship.status == MentorshipStatus.active)
    ) or 0


def active_mentorship_counts() -> dict[int, int]:
    rows = db.session.execute(
        select(Request.mid, func.count(Mentorship.id)).join(Mentorship, Mentorship.rid == Request.id)
        .where(Mentorship.status == MentorshipStatus.active).group_by(Request.mid)
    ).all()
    return {mid: count for mid, count in rows}


def active_mentorship_for_student(student_id: int) -> Mentorship | None:
    """One-mentor rule (M2 C5/C6)."""
    return db.session.scalar(
        select(Mentorship).join(Request, Request.id == Mentorship.rid)
        .where(Request.sid == student_id, Mentorship.status == MentorshipStatus.active)
    )


def active_mentorship_between(student_id: int, mentor_id: int) -> Mentorship | None:
    return db.session.scalar(
        select(Mentorship).join(Request, Request.id == Mentorship.rid)
        .where(Request.sid == student_id, Request.mid == mentor_id, Mentorship.status == MentorshipStatus.active)
    )


def has_request_between(student_id: int, mentor_id: int) -> bool:
    return db.session.scalar(select(Request.id).where(Request.sid == student_id, Request.mid == mentor_id).limit(1)) is not None


def accepted_request_between(student_id: int, mentor_id: int) -> bool:
    return db.session.scalar(
        select(Request.id).where(Request.sid == student_id, Request.mid == mentor_id, Request.status == RequestStatus.accepted).limit(1)
    ) is not None


def pending_requests_of_student(student_id: int, exclude_id: int | None = None) -> list[Request]:
    stmt = select(Request).where(Request.sid == student_id, Request.status == RequestStatus.pending)
    if exclude_id is not None:
        stmt = stmt.where(Request.id != exclude_id)
    return list(db.session.scalars(stmt))


def pending_requests_past_expiry(now: datetime) -> list[Request]:
    return list(db.session.scalars(select(Request).where(Request.status == RequestStatus.pending, Request.expires_on <= now)))


def lock_mentor(mentor_id: int) -> Mentor | None:
    """Serialise capacity checks for one mentor (M1 edge case 1 / M2 "Transaction and locking").

    PostgreSQL: SELECT ... FOR UPDATE locks the mentor row.
    SQLite ignores FOR UPDATE, so we first issue a no-op UPDATE on the row. That makes SQLite take
    its write lock *now*, so a second request has to wait until this transaction commits, and its
    capacity re-check then sees the new mentorship (and returns 409).
    """
    if db.engine.dialect.name == "sqlite":
        db.session.execute(update(Mentor).where(Mentor.id == mentor_id).values(capacity=Mentor.capacity))
        return db.session.get(Mentor, mentor_id)
    return db.session.scalar(select(Mentor).where(Mentor.id == mentor_id).with_for_update())


# ---------------- tags ----------------

def approved_tags_by_name(names: list[str]) -> list[Tag]:
    if not names:
        return []
    lowered = [n.strip().lower() for n in names]
    return list(db.session.scalars(select(Tag).where(Tag.t_status.is_(True), func.lower(Tag.name).in_(lowered))))


def tag_by_name_type(name: str, tag_type, exclude_id: int | None = None) -> Tag | None:
    stmt = select(Tag).where(func.lower(Tag.name) == name.strip().lower(), Tag.type == tag_type)
    if exclude_id is not None:
        stmt = stmt.where(Tag.id != exclude_id)
    return db.session.scalar(stmt)


def tag_in_use(tag_id: int) -> bool:
    return db.session.scalar(select(UserTag.uid).where(UserTag.tag_id == tag_id).limit(1)) is not None


# ---------------- notifications ----------------

def notifications_for(user_id: int) -> list[Notification]:
    return list(db.session.scalars(select(Notification).where(Notification.uid == user_id).order_by(Notification.created_at.desc(), Notification.id.desc())))
