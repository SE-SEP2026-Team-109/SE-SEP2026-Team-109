from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SessionStatus

if TYPE_CHECKING:
    from app.models.availability import Availability
    from app.models.feedback import Feedback
    from app.models.mentoring import Mentorship
    from app.models.notifications import Notification
    from app.models.user import User


class MentoringSession(Base):
    """Maps to the DBML `session` table (renamed to avoid clashing with sqlalchemy.orm.Session)."""

    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    mgid: Mapped[int] = mapped_column(ForeignKey("mentorship.id"), nullable=False)
    available_id: Mapped[int] = mapped_column(ForeignKey("availability.id"), unique=True, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.pending)
    mentor_response: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    mentorship: Mapped["Mentorship"] = relationship(back_populates="sessions")
    availability: Mapped["Availability"] = relationship(back_populates="session")
    action_items: Mapped[list["SessionActionItem"]] = relationship(back_populates="session")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="session")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="session")


class SessionActionItem(Base):
    __tablename__ = "session_action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), nullable=False)
    item: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)

    session: Mapped["MentoringSession"] = relationship(back_populates="action_items")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assigned_to])
