
"""Business logic for creating and managing mentoring sessions."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.availability import Availability
from app.models.enums import (
    MentorAvailabilityStatus,
    MentorshipStatus,
    SessionStatus,
    UserRole,
)
from app.models.mentoring import Mentorship, Request as MentoringRequest
from app.models.sessions import MentoringSession
from app.models.user import User
from app.schemas.sessions import SessionCreate, SessionDecision, SessionReschedule

def create_session(
    db: Session,
    current_user: User,
    data: SessionCreate,
) -> MentoringSession:
    """Allow a student to book an available slot with their active mentor."""

    # Only students can book sessions.
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can book mentoring sessions.",
        )

    # Find the student's active mentorship.
    mentorship = (
        db.query(Mentorship)
        .join(MentoringRequest, MentoringRequest.id == Mentorship.rid)
        .filter(
            MentoringRequest.sid == current_user.id,
            Mentorship.status == MentorshipStatus.active,
        )
        .first()
    )

    if mentorship is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You do not have an active mentorship.",
        )

    # Find the selected availability slot.
    availability = (
        db.query(Availability)
        .filter(Availability.id == data.available_id)
        .first()
    )

    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found.",
        )

    # Ensure the slot belongs to the student's assigned mentor.
    if availability.mid != mentorship.request.mid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This slot does not belong to your mentor.",
        )

    # Check that the slot is still available.
    if availability.status != MentorAvailabilityStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This availability slot is no longer available.",
        )

    # Only future slots can be booked.
    now = datetime.utcnow()

    if availability.start_time <= now or availability.end_time <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Past or ongoing availability slots cannot be booked.",
        )

    if availability.end_time <= availability.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The availability slot has an invalid time range.",
        )

    # Check whether another session has already booked this slot.
    existing_session = (
        db.query(MentoringSession)
        .filter(MentoringSession.available_id == availability.id)
        .first()
    )

    if existing_session is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This availability slot has already been booked.",
        )

    # Create the session with pending status.
    mentoring_session = MentoringSession(
        mgid=mentorship.id,
        available_id=availability.id,
        status=SessionStatus.pending,
        notes=data.notes,
    )

    # Reserve the slot so it cannot be offered as available.
    availability.status = MentorAvailabilityStatus.in_a_session

    db.add(mentoring_session)

    try:
        db.commit()
        db.refresh(mentoring_session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot was booked by another user. Please select another slot.",
        )

    return mentoring_session

def get_my_sessions(
    db: Session,
    current_user: User,
) -> list[MentoringSession]:
    """Return sessions belonging to the logged-in student or mentor."""

    query = (
        db.query(MentoringSession)
        .join(Mentorship, Mentorship.id == MentoringSession.mgid)
        .join(MentoringRequest, MentoringRequest.id == Mentorship.rid)
    )

    if current_user.role == UserRole.student:
        query = query.filter(MentoringRequest.sid == current_user.id)

    elif current_user.role == UserRole.mentor:
        query = query.filter(MentoringRequest.mid == current_user.id)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students and mentors can view mentoring sessions.",
        )

    return query.order_by(MentoringSession.id.desc()).all()

def get_session_by_id(
    db: Session,
    current_user: User,
    session_id: int,
) -> MentoringSession:
    """Return one session if the logged-in user is a participant."""

    mentoring_session = (
        db.query(MentoringSession)
        .join(Mentorship, Mentorship.id == MentoringSession.mgid)
        .join(MentoringRequest, MentoringRequest.id == Mentorship.rid)
        .filter(MentoringSession.id == session_id)
        .first()
    )

    if mentoring_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    request = mentoring_session.mentorship.request

    if current_user.role == UserRole.student:
        if request.sid != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to view this session.",
            )

    elif current_user.role == UserRole.mentor:
        if request.mid != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to view this session.",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students and mentors can view mentoring sessions.",
        )

    return mentoring_session

def respond_to_session(
    db: Session,
    current_user: User,
    session_id: int,
    data: SessionDecision,
) -> MentoringSession:
    """Allow the assigned mentor to accept or decline a session."""

    if current_user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only mentors can respond to session bookings.",
        )

    mentoring_session = (
        db.query(MentoringSession)
        .filter(MentoringSession.id == session_id)
        .first()
    )

    if mentoring_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    request = mentoring_session.mentorship.request

    if request.mid != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to respond to this session.",
        )

    if mentoring_session.status != SessionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending sessions can be accepted or declined.",
        )

    if data.action == "accept":
        mentoring_session.status = SessionStatus.scheduled
        mentoring_session.mentor_response = None

    else:
        mentoring_session.status = SessionStatus.cancelled
        mentoring_session.mentor_response = data.reason or "Session declined by mentor."

        availability = mentoring_session.availability

        if availability.end_time > datetime.utcnow():
            availability.status = MentorAvailabilityStatus.available

    db.commit()
    db.refresh(mentoring_session)

    return mentoring_session

def reschedule_session(
    db: Session,
    current_user: User,
    session_id: int,
    data: SessionReschedule,
) -> MentoringSession:
    """Allow only the assigned mentor to reschedule a session."""

    if current_user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only mentors can reschedule sessions.",
        )

    mentoring_session = get_session_by_id(db, current_user, session_id)

    if mentoring_session.status not in [
        SessionStatus.pending,
        SessionStatus.scheduled,
        SessionStatus.rescheduled,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session cannot be rescheduled.",
        )

    old_availability = mentoring_session.availability

    new_availability = (
        db.query(Availability)
        .filter(Availability.id == data.available_id)
        .first()
    )

    if new_availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New availability slot not found.",
        )

    if new_availability.id == old_availability.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select a different availability slot.",
        )

    if new_availability.mid != old_availability.mid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The new slot must belong to the same mentor.",
        )

    if new_availability.status != MentorAvailabilityStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The new slot is no longer available.",
        )

    now = datetime.utcnow()

    if (
        new_availability.start_time <= now
        or new_availability.end_time <= now
        or new_availability.end_time <= new_availability.start_time
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select a valid future availability slot.",
        )

    if old_availability.end_time > now:
        old_availability.status = MentorAvailabilityStatus.available

    new_availability.status = MentorAvailabilityStatus.in_a_session
    mentoring_session.available_id = new_availability.id
    mentoring_session.status = SessionStatus.rescheduled

    db.commit()
    db.refresh(mentoring_session)

    return mentoring_session

def cancel_session(
    db: Session,
    current_user: User,
    session_id: int,
) -> MentoringSession:
    """Allow only the assigned mentor to cancel a session."""

    if current_user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only mentors can cancel sessions.",
        )

    mentoring_session = get_session_by_id(db, current_user, session_id)

    if mentoring_session.status not in [
        SessionStatus.pending,
        SessionStatus.scheduled,
        SessionStatus.rescheduled,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session cannot be cancelled.",
        )

    mentoring_session.status = SessionStatus.cancelled
    mentoring_session.mentor_response = "Session cancelled by mentor."

    availability = mentoring_session.availability

    if availability.end_time > datetime.utcnow():
        availability.status = MentorAvailabilityStatus.available

    db.commit()
    db.refresh(mentoring_session)

    return mentoring_session

def complete_session(
    db: Session,
    current_user: User,
    session_id: int,
) -> MentoringSession:
    """Allow only the assigned mentor to mark a session as completed."""

    if current_user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only mentors can mark sessions as completed.",
        )

    mentoring_session = get_session_by_id(db, current_user, session_id)

    if mentoring_session.status not in [
        SessionStatus.scheduled,
        SessionStatus.rescheduled,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only scheduled sessions can be marked as completed.",
        )

    if mentoring_session.availability.end_time > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A session can only be completed after its scheduled end time.",
        )

    mentoring_session.status = SessionStatus.completed

    db.commit()
    db.refresh(mentoring_session)

    return mentoring_session