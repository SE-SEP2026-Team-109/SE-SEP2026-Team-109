

"""Business logic for retrieving and managing mentoring relationships."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.models.enums import MentorshipStatus, UserRole, SessionStatus
from app.models.mentoring import Mentorship, Request
from app.models.user import Mentor, Student, User
from app.models.availability import Availability
from app.models.sessions import MentoringSession

from app.services.notification_service import notify

def list_mentorings(
    db: Session,
    current_user: User,
) -> list[dict]:
    """
    Retrieve the authenticated user's active mentoring relationships.

    Mentors receive a list of their active mentees, while students
    receive their active mentoring relationship with their mentor.

    Args:
        db: Active SQLAlchemy database session.
        current_user: Authenticated and active user.

    Returns:
        A list of dictionaries containing mentoring details and the
        associated student and mentor profiles.

    Raises:
        HTTPException: If the user is neither a student nor a mentor.
    """
    query = (
        db.query(Mentorship)
        .join(Mentorship.request)
        .options(
            joinedload(Mentorship.request)
            .joinedload(Request.student)
            .joinedload(Student.user),

            joinedload(Mentorship.request)
            .joinedload(Request.mentor)
            .joinedload(Mentor.user),
        )
        .filter(Mentorship.status == MentorshipStatus.active)
    )

    if current_user.role == UserRole.mentor:
        query = query.filter(Request.mid == current_user.id)

    elif current_user.role == UserRole.student:
        query = query.filter(Request.sid == current_user.id)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students and mentors can access mentoring relationships.",
        )

    mentorings = (
        query
        .order_by(Mentorship.start.desc(), Mentorship.id.desc())
        .all()
    )

    # Map ORM relationships into the response DTO structure.
    return [
        {
            "id": mentoring.id,
            "start": mentoring.start,
            "end": mentoring.end,
            "status": mentoring.status,
            "student_end_requested_at": mentoring.student_end_requested_at,
            "mentor_end_requested_at": mentoring.mentor_end_requested_at,
            "student": mentoring.request.student,
            "mentor": mentoring.request.mentor,
        }
        for mentoring in mentorings
    ]



def request_mentoring_end(
    db: Session,
    current_user: User,
    mentoring_id: int,
) -> dict:
    """
    Record a participant's request to end an active mentorship.

    If the other participant has already requested termination,
    the mentorship is ended immediately and its future sessions
    are cancelled.

    Args:
        db: Active SQLAlchemy database session.
        current_user: Authenticated student or mentor.
        mentoring_id: ID of the mentoring relationship.

    Returns:
        A dictionary containing the updated mentoring relationship
        and its associated student and mentor profiles.

    Raises:
        HTTPException: If the user is unauthorized, the mentoring
            does not belong to them, is inactive, or they have
            already requested its termination.
    """
    if current_user.role not in (UserRole.student, UserRole.mentor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students and mentors can request mentorship termination.",
        )

    # Load the mentorship and its participants.
    # Lock the mentorship row to prevent concurrent end requests
    # from overwriting each other's timestamps.
    mentorship = (
        db.query(Mentorship)
        .options(
            joinedload(Mentorship.request)
            .joinedload(Request.student)
            .joinedload(Student.user),
            joinedload(Mentorship.request)
            .joinedload(Request.mentor)
            .joinedload(Mentor.user),
        )
        .filter(Mentorship.id == mentoring_id)
        .with_for_update(of=Mentorship)
        .first()
    )

    if mentorship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentoring relationship not found.",
        )

    request = mentorship.request

    # Verify that the authenticated user is a participant.
    is_student = (
        current_user.role == UserRole.student
        and request.sid == current_user.id
    )
    is_mentor = (
        current_user.role == UserRole.mentor
        and request.mid == current_user.id
    )

    if not (is_student or is_mentor):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentoring relationship not found.",
        )

    if mentorship.status != MentorshipStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mentoring relationship is no longer active.",
        )

    now = datetime.utcnow()

    if is_student:
        if mentorship.student_end_requested_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already requested to end this mentorship.",
            )

        mentorship.student_end_requested_at = now
        other_user_id = request.mid

        other_party_requested = (
            mentorship.mentor_end_requested_at is not None
        )

    else:
        if mentorship.mentor_end_requested_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already requested to end this mentorship.",
            )

        mentorship.mentor_end_requested_at = now
        other_user_id = request.sid

        other_party_requested = (
            mentorship.student_end_requested_at is not None
        )

    if other_party_requested:
        # Both participants have requested termination.
        mentorship.status = MentorshipStatus.inactive
        mentorship.end = now

        # Find availability IDs for future sessions.
        future_availability_ids = (
            db.query(Availability.id)
            .filter(Availability.start_time >= now)
        )

        # Cancel future sessions belonging to this mentorship.
        db.query(MentoringSession).filter(
            MentoringSession.mgid == mentorship.id,
            MentoringSession.available_id.in_(future_availability_ids),
            MentoringSession.status.in_(
                [
                    SessionStatus.pending,
                    SessionStatus.scheduled,
                    SessionStatus.rescheduled,
                ]
            ),
        ).update(
            {MentoringSession.status: SessionStatus.cancelled},
            synchronize_session=False,
        )

        notify(
            db,
            request.sid,
            "Your mentoring relationship has ended by mutual agreement.",
        )
        notify(
            db,
            request.mid,
            "Your mentoring relationship has ended by mutual agreement.",
        )

    else:
        # The first participant has requested termination.
        # Give the other participant 15 days to respond.
        notify(
            db,
            other_user_id,
            "Your mentoring partner has requested to end the mentoring relationship. "
            "Please respond within 15 days.",
        )

    try:
        db.commit()
        db.refresh(mentorship)

    except Exception:
        db.rollback()
        raise

    # Map ORM relationships to the existing MentoringRead DTO structure.
    return {
        "id": mentorship.id,
        "start": mentorship.start,
        "end": mentorship.end,
        "status": mentorship.status,
        "student_end_requested_at": mentorship.student_end_requested_at,
        "mentor_end_requested_at": mentorship.mentor_end_requested_at,
        "student": request.student,
        "mentor": request.mentor,
    }


def cancel_mentoring_end(
    db: Session,
    current_user: User,
    mentoring_id: int,
) -> dict:
    """
    Allow a participant to withdraw their pending mentorship end request.

    Args:
        db: The database session.
        current_user: The authenticated student or mentor.
        mentoring_id: The ID of the mentorship.

    Returns:
        dict: The updated mentorship with participant details.

    Raises:
        HTTPException: If the mentorship does not exist, the caller is
            not a participant, the mentorship has ended, or the caller
            has no pending end request.
    """
    mentorship = (
        db.query(Mentorship)
        .options(
            joinedload(Mentorship.request)
            .joinedload(Request.student)
            .joinedload(Student.user),
            joinedload(Mentorship.request)
            .joinedload(Request.mentor)
            .joinedload(Mentor.user),
        )
        .filter(Mentorship.id == mentoring_id)
        .with_for_update(of=Mentorship)
        .first()
    )

    if mentorship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship not found.",
        )

    request = mentorship.request

    is_student = (
        current_user.role == UserRole.student
        and request.sid == current_user.id
    )
    is_mentor = (
        current_user.role == UserRole.mentor
        and request.mid == current_user.id
    )

    if not (is_student or is_mentor):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship not found.",
        )

    if mentorship.status != MentorshipStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot withdraw an end request from an inactive mentorship.",
        )

    if is_student:
        if mentorship.student_end_requested_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have not requested to end this mentorship.",
            )

        mentorship.student_end_requested_at = None

    else:
        if mentorship.mentor_end_requested_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have not requested to end this mentorship.",
            )

        mentorship.mentor_end_requested_at = None

    try:
        db.commit()
        db.refresh(mentorship)

    except Exception:
        db.rollback()
        raise

    return {
        "id": mentorship.id,
        "start": mentorship.start,
        "end": mentorship.end,
        "status": mentorship.status,
        "student_end_requested_at": mentorship.student_end_requested_at,
        "mentor_end_requested_at": mentorship.mentor_end_requested_at,
        "student": request.student,
        "mentor": request.mentor,
    }

