"""C13 table: ``Notifications`` (table name kept from the DBML/FastAPI model).

``marked_on`` is the time the user marked it read (NULL = unread).
CHANGE: added ``link`` so the frontend can open the related page when clicked.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import utcnow


class Notification(db.Model):
    __tablename__ = "Notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    rid: Mapped[int | None] = mapped_column(ForeignKey("request.id"))
    uid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    marked_on: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(255))
