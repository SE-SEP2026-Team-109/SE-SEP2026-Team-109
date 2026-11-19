

"""Business logic for retrieving and managing mentoring relationships."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.enums import MentorshipStatus, UserRole
from app.models.mentoring import Mentorship, Request
from app.models.user import Mentor, Student, User


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
            "status": mentoring.status,
            "student_end_requested_at": mentoring.student_end_requested_at,
            "mentor_end_requested_at": mentoring.mentor_end_requested_at,
            "student": mentoring.request.student,
            "mentor": mentoring.request.mentor,
        }
        for mentoring in mentorings
    ]
