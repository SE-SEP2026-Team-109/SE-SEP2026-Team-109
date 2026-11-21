"""C5 Requests: submit, list, view, withdraw, accept/reject, expire.

Ported from FastAPI ``services/request_service.py`` (Development branch). The
business rules are the same; additions required by M1/M2 are marked ADDED:
* ADDED status history for every change, with the actor (System when automatic) - M1 4.4, US-07, US-09.
* ADDED notifications to the other party - US-06, US-13.
* ADDED ``expires_on`` stored on the request - US-06.
* ADDED reject reason optional - US-08 (FastAPI required it).
* ADDED coordinators/admins can list requests WITHOUT message content - M2 C5, Meeting 5.
* ADDED SQLite-safe locking of the mentor row on submit/accept - M1 edge case 1.
"""

from datetime import timedelta

from flask import current_app

from app import repositories as repo
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.extensions import db
from app.models import (
    Mentorship, MentorshipStatus, Request, RequestSource, RequestStatus, RequestStatusHistory, User, UserRole,
    UserStatus, VerificationStatus, utcnow,
)
from app.services.notification_service import notify

ACTOR = {UserRole.student: "Student", UserRole.mentor: "Mentor", UserRole.coordinator: "Coordinator", UserRole.admin: "Admin"}


def move(req: Request, to: RequestStatus, actor: User | None, reason: str | None = None) -> None:
    """The only place a request status changes, so history can never be skipped ("History writer")."""
    db.session.add(RequestStatusHistory(
        rid=req.id, from_status=req.status, to_status=to,
        actor_id=actor.id if actor else None, actor_role=ACTOR[actor.role] if actor else "System",
    ))
    req.status = to
    req.changed_on = utcnow()
    if reason is not None:
        req.mentor_response = reason


def expire_due_requests() -> int:
    """US-09: pending requests past ``expires_on`` become Expired (actor System) and both sides are told.

    Called lazily before request operations and by the ``flask run-jobs`` command (C16).
    """
    now = utcnow()
    due = repo.pending_requests_past_expiry(now)
    for req in due:
        move(req, RequestStatus.expired, None)
        notify(req.sid, "A mentoring request expired after 14 days without a reply", "/student/requests", req.id)
        notify(req.mid, "A pending mentoring request expired", "/mentor/requests", req.id)
    if due:
        db.session.commit()
    return len(due)


def _active_student(student_id: int):
    user = repo.get_user(student_id)
    if user is None or user.role != UserRole.student or user.student is None or user.status != UserStatus.active:
        raise NotFound("Student not found.")
    return user


def _requestable_mentor(mentor_id: int):
    user = repo.get_user(mentor_id)
    if (user is None or user.role != UserRole.mentor or user.mentor is None or user.status != UserStatus.active
            or user.mentor.veri_status != VerificationStatus.verified):
        raise NotFound("Mentor not found.")
    return user


def create(actor: User, mentor_id: int, message: str, student_id: int | None = None) -> Request:
    expire_due_requests()
    if actor.role == UserRole.student:
        if student_id not in (None, actor.id):
            raise Forbidden("You can only create requests for yourself.")
        student_id, source, assigned_by = actor.id, RequestSource.student, None
    elif actor.role in (UserRole.coordinator, UserRole.admin):
        if student_id is None:
            raise BadRequest("student_id is required when assigning a request.")
        source, assigned_by = RequestSource.coordinator, actor.id  # still needs mentor acceptance (M2 C5)
    else:
        raise Forbidden("Mentors cannot create mentoring requests.")

    student = _active_student(student_id)
    mentor_user = _requestable_mentor(mentor_id)
    try:
        mentor = repo.lock_mentor(mentor_id)
        if mentor.pause:
            raise Conflict("This mentor has paused new requests.")
        if repo.count_active_mentorships(mentor_id) >= mentor.capacity:
            raise Conflict("This mentor has no open slots.")
        if repo.active_mentorship_for_student(student_id):
            raise Conflict("You already have a mentor. Only one active mentorship is allowed at a time.")
        if repo.count_pending_requests(student_id) >= current_app.config["MAX_PENDING_REQUESTS"]:
            raise Conflict("You already have 3 pending requests. Withdraw one or wait for a reply.")
        if repo.pending_request_between(student_id, mentor_id):
            raise Conflict("You already have a pending request to this mentor.")

        now = utcnow()
        req = Request(
            sid=student_id, mid=mentor_id, student_message=message, req_source=source, assigned_by=assigned_by,
            status=RequestStatus.pending, created_on=now,
            expires_on=now + timedelta(days=current_app.config["REQUEST_EXPIRY_DAYS"]),
        )
        db.session.add(req)
        db.session.flush()
        db.session.add(RequestStatusHistory(rid=req.id, from_status=None, to_status=RequestStatus.pending,
                                            actor_id=actor.id, actor_role=ACTOR[actor.role]))
        notify(mentor_id, f"New mentoring request from {student.name}", f"/mentor/requests/{req.id}", req.id)
        if source == RequestSource.coordinator:
            notify(student_id, f"The programme team suggested {mentor_user.name} as your mentor. Waiting for their reply.",
                   "/student/requests", req.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return req


def list_for(user: User, status: RequestStatus | None = None) -> list[Request]:
    expire_due_requests()
    query = db.session.query(Request)
    if user.role == UserRole.student:
        query = query.filter(Request.sid == user.id)
    elif user.role == UserRole.mentor:
        query = query.filter(Request.mid == user.id)
    # coordinators and admins see all requests; request_dto strips the message for them
    if status is not None:
        query = query.filter(Request.status == status)
    return query.order_by(Request.created_on.desc(), Request.id.desc()).all()


def get_for(user: User, request_id: int) -> Request:
    expire_due_requests()
    req = repo.get_request(request_id)
    if req is None:
        raise NotFound("Request not found.")
    if user.role in (UserRole.coordinator, UserRole.admin):
        return req
    if not ((user.role == UserRole.student and req.sid == user.id) or (user.role == UserRole.mentor and req.mid == user.id)):
        raise NotFound("Request not found.")  # 404, not 403, so ids cannot be probed (M1 4.2)
    return req


def withdraw(user: User, request_id: int) -> Request:
    expire_due_requests()
    req = repo.get_request(request_id)
    if req is None or user.role != UserRole.student or req.sid != user.id:
        raise NotFound("Request not found.")
    if req.status != RequestStatus.pending:
        raise Conflict("Only pending requests can be withdrawn.")
    move(req, RequestStatus.withdrawn, user)
    notify(req.mid, f"{user.name} withdrew a mentoring request", "/mentor/requests", req.id)
    db.session.commit()
    return req


def decide(user: User, request_id: int, action: str, reason: str | None) -> Request:
    expire_due_requests()
    req = repo.get_request(request_id)
    if req is None or user.role != UserRole.mentor or req.mid != user.id:
        raise NotFound("Request not found.")
    if req.status != RequestStatus.pending:
        raise Conflict("This request has already been decided.")  # decided requests are terminal (US-08)

    try:
        if action == "reject":
            move(req, RequestStatus.rejected, user, reason or "")
            notify(req.sid, f"{user.name} declined your mentoring request", "/student/requests", req.id)
            db.session.commit()
            return req

        mentor = repo.lock_mentor(user.id)
        if mentor.veri_status != VerificationStatus.verified:
            raise Conflict("Your mentor profile is not verified yet.")
        # Capacity is re-checked inside the accept transaction (409 if the last place was just taken).
        if repo.count_active_mentorships(user.id) >= mentor.capacity:
            raise Conflict("Your capacity is full, so this request cannot be accepted. Raise your capacity first.")
        if repo.active_mentorship_for_student(req.sid):
            raise Conflict("This student already has a mentor, so the request cannot be accepted.")

        now = utcnow()
        move(req, RequestStatus.accepted, user, reason or "")
        db.session.add(Mentorship(rid=req.id, start=now, status=MentorshipStatus.active))
        # The student's other pending requests close as Withdrawn by System (M2 C5).
        for other in repo.pending_requests_of_student(req.sid, exclude_id=req.id):
            move(other, RequestStatus.withdrawn, None,
                 "Closed automatically because the student was matched with another mentor.")
            notify(other.mid, f"{req.student.user.name} is now matched with another mentor, so their request was closed",
                   "/mentor/requests", other.id)
        notify(req.sid, f"{user.name} accepted your mentoring request. You can now see each other's contact details.",
               "/student/requests", req.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return req
