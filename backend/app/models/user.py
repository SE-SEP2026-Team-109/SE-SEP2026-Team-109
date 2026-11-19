from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Course, CourseLevel, StudentType, UserRole, UserStatus, VerificationStatus

if TYPE_CHECKING:
    from app.models.availability import Availability
    from app.models.feedback import Feedback
    from app.models.mentoring import Request
    from app.models.notifications import Notification
    from app.models.reports import ReportUser
    from app.models.goals import TrackGoal
    from app.models.tags import UserTag

__all__ = ["User", "Student", "Mentor", "UserRole"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    # Python attribute is `role`; the underlying column stays `urole` to match the project's DBML schema.
    role: Mapped[UserRole] = mapped_column("urole", SAEnum(UserRole), nullable=False, default=UserRole.student)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # stores the hashed password
    phone: Mapped[str | None] = mapped_column(String(30))
    photo: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), nullable=False, default=UserStatus.active)
    delete_time: Mapped[datetime | None] = mapped_column(DateTime)

    student: Mapped["Student | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    mentor: Mapped["Mentor | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    user_tags: Mapped[list["UserTag"]] = relationship(back_populates="user")
    reports_filed: Mapped[list["ReportUser"]] = relationship(
        back_populates="reporter_user", foreign_keys="ReportUser.reporter"
    )
    assigned_requests: Mapped[list["Request"]] = relationship(
        back_populates="assigned_by_user", foreign_keys="Request.assigned_by"
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    course: Mapped[Course] = mapped_column(SAEnum(Course))
    courselevel: Mapped[CourseLevel | None] = mapped_column(SAEnum(CourseLevel))
    type: Mapped[StudentType] = mapped_column(SAEnum(StudentType), nullable=False, default=StudentType.standalone)
    careergoal: Mapped[str | None] = mapped_column(Text)
    rollno: Mapped[str | None] = mapped_column(Text)
    mneeds: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="student")
    requests: Mapped[list["Request"]] = relationship(back_populates="student")
    track_goals: Mapped[list["TrackGoal"]] = relationship(back_populates="student")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="student")


class Mentor(Base):
    __tablename__ = "mentor"
    __table_args__= ( CheckConstraint(
        "capacity >= 0 AND capacity <= 10",
        name="ck_mentor_capacity_range",
    ), )

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    iitm_program: Mapped[Course] = mapped_column(
        SAEnum(Course), nullable=False, default=Course.data_science_and_applications
    )
    level_completed: Mapped[CourseLevel] = mapped_column(
        SAEnum(CourseLevel), nullable=False, default=CourseLevel.bsc_degree
    )
    year_completed: Mapped[int | None] = mapped_column(Integer)
    designation: Mapped[str | None] = mapped_column(String(150))
    still_enrolled: Mapped[bool | None] = mapped_column(Boolean)
    bio: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(String(150))
    experience: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    veri_status: Mapped[VerificationStatus | None] = mapped_column(
        SAEnum(VerificationStatus), default=VerificationStatus.pending
    )
    pause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="mentor")
    requests: Mapped[list["Request"]] = relationship(back_populates="mentor")
    availability_slots: Mapped[list["Availability"]] = relationship(back_populates="mentor")
