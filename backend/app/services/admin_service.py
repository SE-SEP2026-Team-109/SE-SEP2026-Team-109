"""Admin operations needed in Sprint 1 (part of C14 Account Lifecycle).

Only mentor verification and the user list are implemented now, because the
Sprint 1 flow needs them: a mentor who registers is hidden from students until
an admin verifies them (M2 C2). Deactivate/blacklist/deletion are Sprint 2.
"""

from sqlalchemy import select

from app import repositories as repo
from app.errors import BadRequest, NotFound
from app.extensions import db
from app.models import User, UserRole, VerificationStatus
from app.services.notification_service import notify


def list_users() -> list[User]:
    return list(db.session.scalars(select(User).order_by(User.role, User.name)))


def set_verification(mentor_id: int, status: str) -> User:
    user = repo.get_user(mentor_id)
    if user is None or user.role != UserRole.mentor or user.mentor is None:
        raise NotFound("Mentor not found.")
    new = VerificationStatus(status)
    if new == VerificationStatus.verified and not (user.mentor.designation and user.mentor.company):
        raise BadRequest("This mentor has not completed their profile yet (job title and company are required).")
    user.mentor.veri_status = new
    if new == VerificationStatus.verified:
        notify(user.id, "Your mentor profile is verified and now visible to students", "/mentor/profile")
    elif new == VerificationStatus.rejected:
        notify(user.id, "Your mentor profile was not approved. Contact the programme admin for details.", "/mentor/profile")
    db.session.commit()
    return user
