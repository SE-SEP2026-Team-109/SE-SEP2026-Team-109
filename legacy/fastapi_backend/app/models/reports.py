from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ReportCategory, ReportStatus

if TYPE_CHECKING:
    from app.models.mentoring import Mentorship
    from app.models.user import User


class ReportUser(Base):
    __tablename__ = "report_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    mgid: Mapped[int] = mapped_column(ForeignKey("mentorship.id"), nullable=False)
    reporter: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[ReportCategory] = mapped_column(
        SAEnum(ReportCategory), nullable=False, default=ReportCategory.others
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus | None] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.pending)
    actions: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    changed_on: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow)
    attachment: Mapped[str | None] = mapped_column(String(255))
    keep_anonymous: Mapped[bool | None] = mapped_column(Boolean)

    mentorship: Mapped["Mentorship"] = relationship(back_populates="reports")
    reporter_user: Mapped["User"] = relationship(back_populates="reports_filed", foreign_keys=[reporter])
