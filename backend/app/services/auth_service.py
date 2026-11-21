"""C1 Auth: registration, login, password change.

Ported from FastAPI ``api/routes/auth.py`` (where the logic lived in the route)
and moved into a service as M2 requires. Added the M1 US-01 rules FastAPI lacked:
IITM email domain for students, password strength, and blocked-status messages.
"""

from flask import current_app

from app import repositories as repo
from app.errors import BadRequest, Conflict, Forbidden, Unauthorized
from app.extensions import db
from app.models import CourseLevel, Mentor, Student, StudentType, User, UserRole, UserStatus, UserTag, VerificationStatus
from app.schemas import RegisterIn
from app.security import create_access_token, hash_password, verify_password
from app.services.notification_service import notify_role


def _is_iitm_student_email(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    allowed = current_app.config["STUDENT_EMAIL_DOMAIN"]
    return domain == allowed or domain.endswith("." + allowed)


def _attach_tags(user: User, names: list[str], limit: int) -> None:
    names = list(dict.fromkeys(n.strip() for n in names if n.strip()))[:limit]
    tags = repo.approved_tags_by_name(names)
    if len(tags) != len(names):
        known = {t.name.lower() for t in tags}
        missing = [n for n in names if n.lower() not in known]
        raise BadRequest(f"These tags are not approved yet: {', '.join(missing)}")
    for tag in tags:
        db.session.add(UserTag(uid=user.id, tag_id=tag.id))


def register(data: RegisterIn) -> User:
    if data.role == "student" and not _is_iitm_student_email(data.email):
        raise BadRequest("Students must register with an email address ending in study.iitm.ac.in.")
    if repo.get_user_by_email(data.email):
        raise Conflict("An account with this email already exists.")
    if repo.get_user_by_username(data.username):
        raise Conflict("That username is already taken.")

    user = User(
        email=data.email.strip().lower(), password=hash_password(data.password), role=UserRole(data.role),
        username=data.username, name=data.name, phone=data.phone or None, status=UserStatus.active,
    )
    try:
        db.session.add(user)
        db.session.flush()  # gives user.id without committing yet
        if data.role == "student":
            db.session.add(Student(
                id=user.id, course=data.course, courselevel=data.courselevel,
                type=data.student_type or StudentType.standalone, rollno=(data.rollno or None),
                careergoal=data.careergoal, mneeds=data.mneeds,
                skills=[s.model_dump() for s in data.skills],
            ))
            _attach_tags(user, data.interests, current_app.config["STUDENT_MAX_TAGS"])
        else:
            db.session.add(Mentor(
                id=user.id, designation=data.designation, company=data.company, experience=data.experience,
                industry=data.industry, career_area=data.career_area, bio=data.bio,
                support_types=[s.strip() for s in data.support_types if s.strip()],
                capacity=data.capacity, pause=False,
                level_completed=data.level_completed or CourseLevel.bsc_degree,
                year_completed=data.year_completed, still_enrolled=data.still_enrolled, linkedin=data.linkedin,
                veri_status=VerificationStatus.pending,  # hidden from students until an admin verifies (M2 C2)
            ))
            _attach_tags(user, data.expertise, current_app.config["MENTOR_MAX_TAGS"])
            notify_role(UserRole.admin, f"New mentor {data.name} is waiting for verification", "/admin/dashboard?tab=users")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user


BLOCKED_MESSAGES = {
    UserStatus.deactive: "This account has been deactivated. Contact the programme admin.",
    UserStatus.blacklisted: "This account has been blocked. Contact the programme admin.",
    UserStatus.to_be_deleted: "This account is scheduled for deletion.",
}


def login(email: str, password: str) -> tuple[User, str, object]:
    user = repo.get_user_by_email(email)
    if user is None or not verify_password(password, user.password):
        raise Unauthorized("Email or password is incorrect.")
    if user.status != UserStatus.active:
        raise Forbidden(BLOCKED_MESSAGES.get(user.status, "This account is not active."))
    token, expires = create_access_token(user.id, user.role.value)
    return user, token, expires


def change_password(user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password):
        raise BadRequest("Your current password is incorrect.")
    if current == new:
        raise BadRequest("Choose a password that is different from the current one.")
    user.password = hash_password(new)
    db.session.commit()
