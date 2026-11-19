from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Course, CourseLevel, StudentType, UserStatus
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.student
    username: str | None = None
    name: str | None = None
    phone: str | None = None
    # required when role is student
    course: Course | None = None
    courselevel: CourseLevel | None = None
    student_type: StudentType = StudentType.standalone
    careergoal: str | None = None
    rollno: str | None = None
    mneeds: str | None = None
    # required when role is mentor
    capacity: int | None = None
    designation: str | None = None
    company: str | None = None
    experience: float | None = None
    bio: str | None = None
    iitm_program: Course | None = None
    level_completed: CourseLevel | None = None
    year_completed: int | None = None
    still_enrolled: bool | None = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    username: str | None
    name: str | None
    phone: str | None
    photo: str | None
    status: UserStatus
    is_active: bool
    created_at: datetime | None

    model_config = {"from_attributes": True}
