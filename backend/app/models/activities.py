"""Sprint 2 tables (C7-C12): goals, availability, sessions, action items, feedback, reports.

Ported from the FastAPI models so the database already matches the M2 design.
The APIs that use them are Sprint 2 work (see docs/traceability.md) - the tables
exist now so that adding those APIs later does not require a schema reset.
CHANGE markers are explained in docs/decisions.md.
"""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import (
    FeedbackKind, GoalVisibility, MentorAvailabilityStatus, ReportCategory, ReportStatus,
    SessionStatus, TrackGoalStatus, utcnow,
)


class TrackGoal(db.Model):  # C7
    __tablename__ = "trackgoal"

    id: Mapped[int] = mapped_column(primary_key=True)
    sid: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False, index=True)
    mgid: Mapped[int | None] = mapped_column(ForeignKey("mentorship.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TrackGoalStatus] = mapped_column(SAEnum(TrackGoalStatus), nullable=False, default=TrackGoalStatus.todo)
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    visibility: Mapped[GoalVisibility | None] = mapped_column(SAEnum(GoalVisibility), default=GoalVisibility.private)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)  # CHANGE: frontend goals carry free-text tags


class Availability(db.Model):  # C8
    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    mid: Mapped[int] = mapped_column(ForeignKey("mentor.id"), nullable=False, index=True)
    date: Mapped[date | None] = mapped_column(Date)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[MentorAvailabilityStatus] = mapped_column(
        SAEnum(MentorAvailabilityStatus), nullable=False, default=MentorAvailabilityStatus.available
    )


class MentoringSession(db.Model):  # C9 (named to avoid clashing with sqlalchemy Session)
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    mgid: Mapped[int] = mapped_column(ForeignKey("mentorship.id"), nullable=False, index=True)
    # CHANGE: nullable so a past session can be logged without a booked slot (US-12 "log date, duration").
    # Still unique, which is the M2 "unique constraint on session slot as final guard" against double booking.
    available_id: Mapped[int | None] = mapped_column(ForeignKey("availability.id"), unique=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)  # CHANGE: copied from the slot, or entered for logged sessions
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.pending)
    mentor_response: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class SessionActionItem(db.Model):  # C10
    __tablename__ = "session_action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # CHANGE: M2 C10 "DELETE: creator only"
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), nullable=False, index=True)
    item: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)


class Feedback(db.Model):  # C11 session feedback
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    mgid: Mapped[int] = mapped_column(ForeignKey("mentorship.id"), nullable=False, index=True)
    # CHANGE: giver/receiver instead of a mandatory student id, because the frontend lets mentors
    # give feedback too, and "final" feedback is not tied to one session (session_id nullable).
    giver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"))
    kind: Mapped[FeedbackKind] = mapped_column(SAEnum(FeedbackKind), nullable=False, default=FeedbackKind.session)
    rating: Mapped[int | None] = mapped_column(Integer)
    communication_rating: Mapped[int | None] = mapped_column(Integer)
    helpfulness_rating: Mapped[int | None] = mapped_column(Integer)
    preparedness_rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)


class PlatformFeedback(db.Model):  # C11 anonymous platform feedback: no user id is stored
    __tablename__ = "platform_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)


class ReportUser(db.Model):  # C12
    __tablename__ = "report_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    # CHANGE: nullable, and reported_user added (M2 Meeting 8 decision) so users can report
    # someone outside an active mentorship.
    mgid: Mapped[int | None] = mapped_column(ForeignKey("mentorship.id"))
    reporter: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reported_user: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    category: Mapped[ReportCategory] = mapped_column(SAEnum(ReportCategory), nullable=False, default=ReportCategory.others)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus | None] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.pending)
    actions: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    changed_on: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow)
    attachment: Mapped[str | None] = mapped_column(String(255))
    keep_anonymous: Mapped[bool | None] = mapped_column(Boolean)
