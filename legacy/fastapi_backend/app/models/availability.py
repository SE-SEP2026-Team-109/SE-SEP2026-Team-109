from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MentorAvailabilityStatus

if TYPE_CHECKING:
    from app.models.sessions import MentoringSession
    from app.models.user import Mentor


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    mid: Mapped[int] = mapped_column(ForeignKey("mentor.id"), nullable=False)
    date: Mapped[date | None] = mapped_column(Date)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[MentorAvailabilityStatus] = mapped_column(
        SAEnum(MentorAvailabilityStatus), nullable=False, default=MentorAvailabilityStatus.available
    )

    mentor: Mapped["Mentor"] = relationship(back_populates="availability_slots")
    session: Mapped["MentoringSession | None"] = relationship(back_populates="availability", uselist=False)
