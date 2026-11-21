from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.mentoring import Request
    from app.models.sessions import MentoringSession
    from app.models.user import User


class Notification(Base):
    __tablename__ = "Notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    rid: Mapped[int | None] = mapped_column(ForeignKey("request.id"))
    uid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    marked_on: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    request: Mapped["Request | None"] = relationship(back_populates="notifications")
    user: Mapped["User"] = relationship(back_populates="notifications")
    session: Mapped["MentoringSession | None"] = relationship(back_populates="notifications")
