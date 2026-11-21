"""C5/C6 tables: ``request``, ``request_status_history`` and ``mentorship``.

Ported from FastAPI ``app/models/mentoring.py`` (Development branch, which already
has the end-request timestamps). CHANGES:
* ``request.expires_on`` - M2 C5 "expires_on = created + 14 days" (FastAPI computed it on the fly).
* ``request_status_history`` - new table required by M1 4.4 and M2 "History writer":
  from_status, to_status, actor (NULL = System), timestamp.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import MentorshipStatus, RequestSource, RequestStatus, utcnow


class Request(db.Model):
    __tablename__ = "request"
    __table_args__ = (
        Index("ix_request_sid_status", "sid", "status"),
        Index("ix_request_mid_status", "mid", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sid: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    mid: Mapped[int] = mapped_column(ForeignKey("mentor.id"), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    changed_on: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow)
    expires_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    student_message: Mapped[str | None] = mapped_column(Text)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    req_source: Mapped[RequestSource] = mapped_column(SAEnum(RequestSource), nullable=False, default=RequestSource.student)
    mentor_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), nullable=False, default=RequestStatus.pending)
    reminded_on: Mapped[datetime | None] = mapped_column(DateTime)  # C16 stuck-request reminder (sent once)

    student: Mapped["Student"] = relationship(foreign_keys=[sid])  # noqa: F821
    mentor: Mapped["Mentor"] = relationship(foreign_keys=[mid])  # noqa: F821
    mentorship: Mapped["Mentorship | None"] = relationship(back_populates="request", uselist=False)
    history: Mapped[list["RequestStatusHistory"]] = relationship(
        back_populates="request", order_by="RequestStatusHistory.id", cascade="all, delete-orphan"
    )


class RequestStatusHistory(db.Model):
    __tablename__ = "request_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    rid: Mapped[int] = mapped_column(ForeignKey("request.id"), nullable=False, index=True)
    from_status: Mapped[RequestStatus | None] = mapped_column(SAEnum(RequestStatus))
    to_status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # NULL means System
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)  # Student / Mentor / Coordinator / Admin / System
    changed_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    request: Mapped["Request"] = relationship(back_populates="history")


class Mentorship(db.Model):
    """An active or ended mentoring relationship. Created only when a request is accepted (M2 C6)."""

    __tablename__ = "mentorship"

    id: Mapped[int] = mapped_column(primary_key=True)
    rid: Mapped[int] = mapped_column(ForeignKey("request.id"), unique=True, nullable=False)
    start: Mapped[datetime | None] = mapped_column(DateTime)
    end: Mapped[datetime | None] = mapped_column(DateTime)
    student_end_requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    mentor_end_requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[MentorshipStatus] = mapped_column(SAEnum(MentorshipStatus), nullable=False, default=MentorshipStatus.active)

    request: Mapped["Request"] = relationship(back_populates="mentorship")
