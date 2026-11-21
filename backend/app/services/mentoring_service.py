"""C6 Mentoring: list relationships, request to end, withdraw an end request.

Ported from FastAPI ``services/mentoring_service.py`` (Development branch). Rules (M2 C6):
* a mentorship is created only by C5 when a request is accepted;
* it ends when both parties ask (Mutual), or when one asks and the other does not
  respond within 15 days (System - see ``jobs.auto_end_mentorships``), or by admin action;
* ending cancels future sessions; lowering capacity never ends a mentorship.
"""

from datetime import timedelta

from flask import current_app

from app.errors import Conflict, Forbidden, NotFound
from app.extensions import db
from app.models import MentoringSession, Mentorship, MentorshipStatus, Request, SessionStatus, User, UserRole, utcnow
from app.services.notification_service import notify


def list_for(user: User, include_ended: bool = False) -> list[Mentorship]:
    query = db.session.query(Mentorship).join(Request, Request.id == Mentorship.rid)
    if not include_ended:
        query = query.filter(Mentorship.status == MentorshipStatus.active)
    if user.role == UserRole.student:
        query = query.filter(Request.sid == user.id)
    elif user.role == UserRole.mentor:
        query = query.filter(Request.mid == user.id)
    elif user.role not in (UserRole.coordinator, UserRole.admin):
        raise Forbidden("You cannot view mentoring relationships.")
    return query.order_by(Mentorship.start.desc(), Mentorship.id.desc()).all()


def _participant_mentorship(user: User, mentoring_id: int) -> tuple[Mentorship, bool]:
    ms = db.session.get(Mentorship, mentoring_id)
    if ms is None:
        raise NotFound("Mentoring relationship not found.")
    is_student = user.role == UserRole.student and ms.request.sid == user.id
    is_mentor = user.role == UserRole.mentor and ms.request.mid == user.id
    if not (is_student or is_mentor):
        raise NotFound("Mentoring relationship not found.")
    if ms.status != MentorshipStatus.active:
        raise Conflict("This mentoring relationship is no longer active.")
    return ms, is_student


def end_mentorship(ms: Mentorship, reason_message: str) -> None:
    """Close a mentorship and cancel its future sessions (caller commits)."""
    now = utcnow()
    ms.status = MentorshipStatus.inactive
    ms.end = now
    db.session.query(MentoringSession).filter(
        MentoringSession.mgid == ms.id,
        MentoringSession.start_time >= now,
        MentoringSession.status.in_([SessionStatus.pending, SessionStatus.scheduled, SessionStatus.rescheduled]),
    ).update({MentoringSession.status: SessionStatus.cancelled}, synchronize_session=False)
    notify(ms.request.sid, reason_message, "/student/dashboard")
    notify(ms.request.mid, reason_message, "/mentor/mentees")


def request_end(user: User, mentoring_id: int) -> Mentorship:
    ms, is_student = _participant_mentorship(user, mentoring_id)
    now = utcnow()
    if is_student:
        if ms.student_end_requested_at:
            raise Conflict("You have already requested to end this mentorship.")
        ms.student_end_requested_at = now
        other_id, other_asked = ms.request.mid, ms.mentor_end_requested_at is not None
    else:
        if ms.mentor_end_requested_at:
            raise Conflict("You have already requested to end this mentorship.")
        ms.mentor_end_requested_at = now
        other_id, other_asked = ms.request.sid, ms.student_end_requested_at is not None
    if other_asked:
        end_mentorship(ms, "Your mentoring relationship has ended by mutual agreement.")
    else:
        days = current_app.config["MENTORSHIP_END_RESPONSE_DAYS"]
        notify(other_id, f"Your mentoring partner asked to end the mentorship. It will end automatically in {days} days "
                         "unless they withdraw the request.", "/notifications")
    db.session.commit()
    return ms


def cancel_end(user: User, mentoring_id: int) -> Mentorship:
    ms, is_student = _participant_mentorship(user, mentoring_id)
    field = "student_end_requested_at" if is_student else "mentor_end_requested_at"
    if getattr(ms, field) is None:
        raise Conflict("You have not requested to end this mentorship.")
    setattr(ms, field, None)
    db.session.commit()
    return ms


def auto_end_due() -> int:
    """C16 job: one side asked to end, the other did not respond within 15 days -> ended by System."""
    cutoff = utcnow() - timedelta(days=current_app.config["MENTORSHIP_END_RESPONSE_DAYS"])
    due = [ms for ms in db.session.query(Mentorship).filter(Mentorship.status == MentorshipStatus.active)
           if (ms.student_end_requested_at and ms.student_end_requested_at <= cutoff)
           or (ms.mentor_end_requested_at and ms.mentor_end_requested_at <= cutoff)]
    for ms in due:
        end_mentorship(ms, "Your mentoring relationship ended automatically 15 days after an end request.")
    if due:
        db.session.commit()
    return len(due)
