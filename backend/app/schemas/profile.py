
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, Field, AnyUrl

from app.models.enums import (
    Course,
    CourseLevel,
    StudentType,
    UserStatus,
    VerificationStatus,
)
from app.models.user import UserRole
from app.schemas.tags import ProfileTagRead

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


class StudentProfileUpdate(BaseModel):
    course: Course | None = None
    courselevel: CourseLevel | None = None
    type: StudentType | None = None
    careergoal: str | None = None
    rollno: str | None = None
    mneeds: str | None = None

    model_config = ConfigDict(extra="forbid")


class MentorProfileUpdate(BaseModel):
    iitm_program: Course | None = None
    level_completed: CourseLevel | None = None
    year_completed: int | None = None
    designation: str | None = None
    still_enrolled: bool | None = None
    bio: str | None = None
    company: str | None = None
    experience: float | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, ge=0, le=10)

    model_config = ConfigDict(extra="forbid")


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    photo: AnyUrl | None = None

    student: StudentProfileUpdate | None = None
    mentor: MentorProfileUpdate | None = None

    model_config = ConfigDict(extra="forbid")



class MentorPublicProfileRead(BaseModel):
    id: int
    name: str | None
    photo: str | None

    iitm_program: Course
    level_completed: CourseLevel
    year_completed: int | None
    designation: str | None
    bio: str | None
    company: str | None
    experience: float | None
    capacity: int
    pause: bool
    tags: list[ProfileTagRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StudentProfileCardRead(BaseModel):
    id: int
    name: str | None
    photo: str | None
    course: Course
    courselevel: CourseLevel | None
    type: StudentType
    careergoal: str | None
    mneeds: str | None
    tags: list[ProfileTagRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)