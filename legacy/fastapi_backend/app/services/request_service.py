"""Business logic for creating and managing mentoring requests."""

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import (
    MentorshipStatus,
    RequestSource,
    RequestStatus,
    UserRole,
    UserStatus,
    VerificationStatus,
)
from app.models.mentoring import (
    Mentorship,
    Request as MentoringRequest,
)
from app.models.user import Mentor, Student, User

from app.schemas.requests import RequestCreate, RequestDecision


REQUEST_EXPIRY_DAYS = 14
MAX_PENDING_REQUESTS = 3
SYSTEM_WITHDRAWAL_MESSAGE = (
    "Closed automatically because the student accepted another mentor."
)


def expire_old_requests(db: Session) -> None:
    """
    Mark pending requests older than 14 days as expired.

    Expiry is calculated from the existing created_on column, so no
    additional database column is required. This is a lazy expiry:
    it runs whenever a request operation is performed.
    """
    expiry_time = datetime.utcnow() - timedelta(days=REQUEST_EXPIRY_DAYS)

    db.query(MentoringRequest).filter(
        MentoringRequest.status == RequestStatus.pending,
        MentoringRequest.created_on <= expiry_time,
    ).update(
        {
            MentoringRequest.status: RequestStatus.expired,
            MentoringRequest.changed_on: datetime.utcnow(),
        },
        synchronize_session=False,
    )

    db.commit()


def _get_student(db: Session, student_id: int) -> Student:
    """Return an existing student profile or raise 404."""
    student = db.query(Student).filter(Student.id == student_id).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    user = db.query(User).filter(User.id == student_id).first()

    if user is None or user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student account not found or inactive.",
        )

    return student


def _get_mentor(db: Session, mentor_id: int) -> Mentor:
    """Return an existing verified mentor profile or raise an error."""
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()

    if mentor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor profile not found.",
        )

    user = db.query(User).filter(User.id == mentor_id).first()

    if user is None or user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor account not found or inactive.",
        )

    if mentor.veri_status != VerificationStatus.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mentor is not verified.",
        )

    return mentor


def _get_active_mentorship_count(db: Session, mentor_id: int) -> int:
    """Count the mentor's currently active mentorships."""
    return (
        db.query(func.count(Mentorship.id))
        .join(
            MentoringRequest,
            MentoringRequest.id == Mentorship.rid,
        )
        .filter(
            MentoringRequest.mid == mentor_id,
            Mentorship.status == MentorshipStatus.active,
        )
        .scalar()
        or 0
    )


def create_request(
    db: Session,
    current_user: User,
    data: RequestCreate,
) -> MentoringRequest:
    """
    Create a student-originated or coordinator-assigned request.

    Students create requests for themselves. Coordinators and admins
    must provide the student_id they are assigning the request for.
    """
    expire_old_requests(db)

    if current_user.role == UserRole.student:
        if data.student_id is not None and data.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create requests for yourself.",
            )

        student_id = current_user.id
        assigned_by = None
        request_source = RequestSource.student

    elif current_user.role in (UserRole.coordinator, UserRole.admin):
        if data.student_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="student_id is required for an assigned request.",
            )

        student_id = data.student_id
        assigned_by = current_user.id
        request_source = RequestSource.coordinator

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create mentoring requests.",
        )

    _get_student(db, student_id)
    mentor = _get_mentor(db, data.mentor_id)

    # A paused mentor cannot receive new requests.
    if mentor.pause:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mentor is currently paused.",
        )

    # Do not rely on the directory's displayed free-slot count.
    # Capacity must be checked again when creating the request.
    if _get_active_mentorship_count(db, mentor.id) >= mentor.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mentor has no available slots.",
        )

    # A student who already has an active mentor cannot request another.
    has_active_mentorship = (
        db.query(Mentorship.id)
        .join(
            MentoringRequest,
            MentoringRequest.id == Mentorship.rid,
        )
        .filter(
            MentoringRequest.sid == student_id,
            Mentorship.status == MentorshipStatus.active,
        )
        .first()
        is not None
    )

    if has_active_mentorship:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active mentorship.",
        )

    pending_count = (
        db.query(func.count(MentoringRequest.id))
        .filter(
            MentoringRequest.sid == student_id,
            MentoringRequest.status == RequestStatus.pending,
        )
        .scalar()
        or 0
    )

    if pending_count >= MAX_PENDING_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot have more than 3 pending requests.",
        )

    duplicate_request = (
        db.query(MentoringRequest)
        .filter(
            MentoringRequest.sid == student_id,
            MentoringRequest.mid == mentor.id,
            MentoringRequest.status == RequestStatus.pending,
        )
        .first()
    )

    if duplicate_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request for this mentor.",
        )

    request = MentoringRequest(
        sid=student_id,
        mid=mentor.id,
        student_message=data.student_message,
        assigned_by=assigned_by,
        req_source=request_source,
        status=RequestStatus.pending,
    )

    db.add(request)

    try:
        db.commit()
        db.refresh(request)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The request could not be created because of a conflicting database change.",
        )

    return request


def list_requests(
    db: Session,
    current_user: User,
    request_status: RequestStatus | None = None,
) -> list[MentoringRequest]:
    """
    List the authenticated student's requests or mentor's incoming requests.

    Other roles cannot use this listing endpoint.
    """
    expire_old_requests(db)

    query = db.query(MentoringRequest)

    if current_user.role == UserRole.student:
        query = query.filter(MentoringRequest.sid == current_user.id)

    elif current_user.role == UserRole.mentor:
        query = query.filter(MentoringRequest.mid == current_user.id)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students and mentors can view this request list.",
        )

    if request_status is not None:
        query = query.filter(MentoringRequest.status == request_status)

    return query.order_by(MentoringRequest.created_on.desc()).all()


def get_request(
    db: Session,
    current_user: User,
    request_id: int,
) -> MentoringRequest:
    """Retrieve a request only when the current user is a participant."""
    expire_old_requests(db)

    request = (
        db.query(MentoringRequest)
        .filter(MentoringRequest.id == request_id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    is_student = (
        current_user.role == UserRole.student
        and request.sid == current_user.id
    )
    is_mentor = (
        current_user.role == UserRole.mentor
        and request.mid == current_user.id
    )

    if not (is_student or is_mentor):
        # Return 404 rather than revealing another user's request.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    return request


def withdraw_request(
    db: Session,
    current_user: User,
    request_id: int,
) -> MentoringRequest:
    """Allow a student to withdraw their own pending request."""
    expire_old_requests(db)

    request = (
        db.query(MentoringRequest)
        .filter(MentoringRequest.id == request_id)
#        .with_for_update()
        .first()
    )

    if request is None or request.sid != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requesting student can withdraw this request.",
        )

    if request.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending requests can be withdrawn.",
        )

    request.status = RequestStatus.withdrawn
    request.mentor_response = "Withdrawn by student."

    db.commit()
    db.refresh(request)

    return request


def decide_request(
    db: Session,
    current_user: User,
    request_id: int,
    data: RequestDecision,
) -> MentoringRequest:
    """
    Allow the assigned mentor to accept or reject a pending request.

    Acceptance rechecks capacity, creates an active mentorship and
    closes the student's other pending requests.
    """
    expire_old_requests(db)

    request = (
        db.query(MentoringRequest)
        .filter(MentoringRequest.id == request_id)
#        .with_for_update()
        .first()
    )

    if request is None or request.mid != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if current_user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned mentor can decide this request.",
        )

    if request.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This request is no longer pending.",
        )

    if data.action == "reject":
        request.status = RequestStatus.rejected
        request.mentor_response = data.reason

        db.commit()
        db.refresh(request)
        return request

    # Acceptance: lock and re-fetch the mentor before checking capacity.
    mentor = (
        db.query(Mentor)
        .filter(Mentor.id == request.mid)
        .with_for_update()
        .first()
    )

    if mentor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor profile not found.",
        )

    if mentor.pause:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot accept requests while your profile is paused.",
        )

    if mentor.veri_status != VerificationStatus.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your mentor profile is not verified.",
        )

    if _get_active_mentorship_count(db, mentor.id) >= mentor.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You no longer have an available mentoring slot.",
        )

    # Recheck that the student has not acquired another active mentor.
    existing_mentorship = (
        db.query(Mentorship.id)
        .join(
            MentoringRequest,
            MentoringRequest.id == Mentorship.rid,
        )
        .filter(
            MentoringRequest.sid == request.sid,
            Mentorship.status == MentorshipStatus.active,
        )
        .first()
    )

    if existing_mentorship:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student already has an active mentorship.",
        )

    now = datetime.utcnow()

    request.status = RequestStatus.accepted
    request.mentor_response = data.reason

    # An accepted request creates the actual mentoring relationship.
    mentorship = Mentorship(
        rid=request.id,
        start=now,
        status=MentorshipStatus.active,
    )
    db.add(mentorship)

    # Close the student's other pending requests automatically.
    db.query(MentoringRequest).filter(
        MentoringRequest.sid == request.sid,
        MentoringRequest.id != request.id,
        MentoringRequest.status == RequestStatus.pending,
    ).update(
        {
            MentoringRequest.status: RequestStatus.withdrawn,
            MentoringRequest.mentor_response: SYSTEM_WITHDRAWAL_MESSAGE,
            MentoringRequest.changed_on: now,
        },
        synchronize_session=False,
    )

    try:
        db.commit()
        db.refresh(request)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The request could not be accepted because of a conflicting database change.",
        )

    return request

