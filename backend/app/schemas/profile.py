
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.enums import (
    Course,
    CourseLevel,
    StudentType,
    UserStatus,
    VerificationStatus,
)
from app.models.user import UserRole


class StudentProfileRead(BaseModel):
    course: Course
    courselevel: CourseLevel | None
    type: StudentType
    careergoal: str | None
    rollno: str | None
    mneeds: str | None

    model_config = ConfigDict(from_attributes=True)


class MentorProfileRead(BaseModel):
    iitm_program: Course
    level_completed: CourseLevel
    year_completed: int | None
    designation: str | None
    still_enrolled: bool | None
    bio: str | None
    company: str | None
    experience: float | None
    capacity: int
    veri_status: VerificationStatus | None
    pause: bool

    model_config = ConfigDict(from_attributes=True)


class ProfileRead(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    username: str | None
    name: str | None
    phone: str | None
    photo: str | None
    status: UserStatus
    created_at: datetime | None

    student: StudentProfileRead | None
    mentor: MentorProfileRead | None

    model_config = ConfigDict(from_attributes=True)
