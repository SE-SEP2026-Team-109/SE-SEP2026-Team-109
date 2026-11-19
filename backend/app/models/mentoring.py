from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MentorshipStatus, RequestSource, RequestStatus

if TYPE_CHECKING:
    from app.models.feedback import Feedback
    from app.models.goals import TrackGoal
    from app.models.notifications import Notification
    from app.models.reports import ReportUser
    from app.models.sessions import MentoringSession
    from app.models.user import Mentor, Student, User


class Request(Base):
    __tablename__ = "request"

    id: Mapped[int] = mapped_column(primary_key=True)
    sid: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    mid: Mapped[int] = mapped_column(ForeignKey("mentor.id"), nullable=False)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    changed_on: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow)
    student_message: Mapped[str | None] = mapped_column(Text)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    req_source: Mapped[RequestSource] = mapped_column(
        SAEnum(RequestSource), nullable=False, default=RequestSource.student
    )
    mentor_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), nullable=False, default=RequestStatus.pending)

    student: Mapped["Student"] = relationship(back_populates="requests", foreign_keys=[sid])
    mentor: Mapped["Mentor"] = relationship(back_populates="requests", foreign_keys=[mid])
    assigned_by_user: Mapped["User | None"] = relationship(
        back_populates="assigned_requests", foreign_keys=[assigned_by]
    )
    mentorship: Mapped["Mentorship | None"] = relationship(back_populates="request", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="request")


class Mentorship(Base):
    """Represent an active or completed mentoring relationship."""

    __tablename__ = "mentorship"

    id: Mapped[int] = mapped_column(primary_key=True)
    rid: Mapped[int] = mapped_column(ForeignKey("request.id"), unique=True, nullable=False)
    start: Mapped[datetime | None] = mapped_column(DateTime)
    end: Mapped[datetime | None] = mapped_column(DateTime)
    student_end_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    mentor_end_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[MentorshipStatus] = mapped_column(
        SAEnum(MentorshipStatus),
        nullable=False,
        default=MentorshipStatus.active,
    )

    request: Mapped["Request"] = relationship(back_populates="mentorship")
    sessions: Mapped[list["MentoringSession"]] = relationship(back_populates="mentorship")
    track_goals: Mapped[list["TrackGoal"]] = relationship(back_populates="mentorship")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="mentorship")
    reports: Mapped[list["ReportUser"]] = relationship(back_populates="mentorship")
    