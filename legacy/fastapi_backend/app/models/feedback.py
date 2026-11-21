from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.mentoring import Mentorship
    from app.models.sessions import MentoringSession
    from app.models.user import Student


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    mgid: Mapped[int] = mapped_column(ForeignKey("mentorship.id"), nullable=False)
    sid: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    communication_rating: Mapped[int | None] = mapped_column(Integer)
    helpfulness_rating: Mapped[int | None] = mapped_column(Integer)
    preparedness_rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    mentorship: Mapped["Mentorship"] = relationship(back_populates="feedbacks")
    student: Mapped["Student"] = relationship(back_populates="feedbacks")
    session: Mapped["MentoringSession"] = relationship(back_populates="feedbacks")


class PlatformFeedback(Base):
    __tablename__ = "platform_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
