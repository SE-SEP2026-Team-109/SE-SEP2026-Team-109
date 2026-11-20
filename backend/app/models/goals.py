from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import GoalVisibility, TrackGoalStatus

if TYPE_CHECKING:
    from app.models.mentoring import Mentorship
    from app.models.user import Student


class TrackGoal(Base):
    __tablename__ = "trackgoal"

    id: Mapped[int] = mapped_column(primary_key=True)
    sid: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    mgid: Mapped[int | None] = mapped_column(ForeignKey("mentorship.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TrackGoalStatus] = mapped_column(
        SAEnum(TrackGoalStatus), nullable=False, default=TrackGoalStatus.todo
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    created_on: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    visibility: Mapped[GoalVisibility | None] = mapped_column(SAEnum(GoalVisibility), default=GoalVisibility.private)

    student: Mapped["Student"] = relationship(back_populates="track_goals")
    mentorship: Mapped["Mentorship | None"] = relationship(back_populates="track_goals")
