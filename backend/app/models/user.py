"""C1/C2 tables: ``users`` plus the role extensions ``student`` and ``mentor``.

Ported from FastAPI ``app/models/user.py``. Column names follow the team's DBML
(e.g. the role column is ``urole``). CHANGE markers are explained in docs/decisions.md.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import Course, CourseLevel, StudentType, UserRole, UserStatus, VerificationStatus, utcnow


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column("urole", SAEnum(UserRole), nullable=False, default=UserRole.student)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt hash, never plain text
    phone: Mapped[str | None] = mapped_column(String(30))
    # CHANGE: Text instead of String(255) so the frontend's resized data-URL photo fits.
    photo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), nullable=False, default=UserStatus.active)
    delete_time: Mapped[datetime | None] = mapped_column(DateTime)

    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    mentor: Mapped["Mentor | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    user_tags: Mapped[list["UserTag"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active


class Student(db.Model):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    course: Mapped[Course | None] = mapped_column(SAEnum(Course))
    courselevel: Mapped[CourseLevel | None] = mapped_column(SAEnum(CourseLevel))  # null = Foundation
    type: Mapped[StudentType] = mapped_column(SAEnum(StudentType), nullable=False, default=StudentType.standalone)
    careergoal: Mapped[str | None] = mapped_column(Text)
    rollno: Mapped[str | None] = mapped_column(Text)
    mneeds: Mapped[str | None] = mapped_column(Text)
    # CHANGE: free-text skills with level 1-5 and a "want to learn" flag, as the profile page collects them.
    # Stored as JSON because skills are typed freely, while user_tags only accepts admin-approved tags.
    skills: Mapped[list | None] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="student")


class Mentor(db.Model):
    __tablename__ = "mentor"
    __table_args__ = (CheckConstraint("capacity >= 0 AND capacity <= 10", name="ck_mentor_capacity_range"),)

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    iitm_program: Mapped[Course] = mapped_column(SAEnum(Course), nullable=False, default=Course.data_science_and_applications)
    level_completed: Mapped[CourseLevel] = mapped_column(SAEnum(CourseLevel), nullable=False, default=CourseLevel.bsc_degree)
    year_completed: Mapped[int | None] = mapped_column(Integer)
    designation: Mapped[str | None] = mapped_column(String(150))
    still_enrolled: Mapped[bool | None] = mapped_column(Boolean)
    bio: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(String(150))
    experience: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    veri_status: Mapped[VerificationStatus | None] = mapped_column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    pause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # CHANGE: fields the M1 stories / frontend need that the DBML did not have.
    industry: Mapped[str | None] = mapped_column(String(100))        # US-05 search by industry
    career_area: Mapped[str | None] = mapped_column(String(100))     # US-05 search by career area
    support_types: Mapped[list | None] = mapped_column(JSON, default=list)  # US-03 "support types (e.g. resume review)"
    linkedin: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="mentor")
