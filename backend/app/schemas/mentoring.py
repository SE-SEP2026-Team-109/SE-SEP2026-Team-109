
"""Pydantic schemas for mentoring relationships."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    Course,
    CourseLevel,
    MentorshipStatus,
    StudentType,
)


class MentoringUserRead(BaseModel):
    """Public user information shared with their mentoring counterpart."""

    id: int
    name: str | None
    email: str
    photo: str | None

    model_config = ConfigDict(from_attributes=True)


class MentoringStudentRead(BaseModel):
    """Student profile information within a mentoring relationship."""

    id: int
    course: Course
    courselevel: CourseLevel | None
    type: StudentType
    user: MentoringUserRead

    model_config = ConfigDict(from_attributes=True)


class MentoringMentorRead(BaseModel):
    """Mentor profile information within a mentoring relationship."""

    id: int
    designation: str | None
    company: str | None
    experience: float | None
    user: MentoringUserRead

    model_config = ConfigDict(from_attributes=True)


class MentoringRead(BaseModel):
    """Public representation of an active mentoring relationship."""

    id: int
    start: datetime | None
    status: MentorshipStatus

    student_end_requested_at: datetime | None
    mentor_end_requested_at: datetime | None

    student: MentoringStudentRead
    mentor: MentoringMentorRead

    model_config = ConfigDict(from_attributes=True)
