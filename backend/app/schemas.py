"""Request-body validation schemas (Pydantic v2).

Reused from the FastAPI ``app/schemas/*`` shapes (Pydantic works without FastAPI),
with the Milestone 1 rules the FastAPI code did not enforce added:
* US-01 password >= 8 characters with letters AND numbers,
* US-01 student email must end in study.iitm.ac.in (checked in auth_service),
* US-03/04 capacity 1-10,
* US-08 reject reason OPTIONAL (FastAPI required it; M1 wins - see docs/decisions.md).
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import Course, CourseLevel, StudentType, TagType

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")


def _clean(value):
    return value.strip() if isinstance(value, str) else value


def check_password(value: str) -> str:
    if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must be at least 8 characters and include letters and numbers.")
    return value


def check_username(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    if not USERNAME_RE.match(value):
        raise ValueError("Username must be 3 to 20 lowercase letters, numbers or underscores.")
    return value


class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    level: int = Field(default=1, ge=1, le=5)
    want: bool = False

    _clean_name = field_validator("name")(lambda cls, v: v.strip())


# ---------------- C1 Auth ----------------

class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str
    role: Literal["student", "mentor"]  # coordinator/admin accounts are seeded (M2 C1)
    name: str = Field(min_length=2, max_length=150)
    username: str
    phone: str | None = Field(default=None, max_length=30)
    # student
    course: Course | None = None
    courselevel: CourseLevel | None = None
    student_type: StudentType | None = None
    rollno: str | None = Field(default=None, max_length=30)
    careergoal: str | None = None
    mneeds: str | None = Field(default=None, max_length=2000)
    interests: list[str] = Field(default_factory=list)  # approved tag names
    skills: list[SkillIn] = Field(default_factory=list)
    # mentor
    designation: str | None = Field(default=None, max_length=150)
    company: str | None = Field(default=None, max_length=150)
    experience: float | None = Field(default=None, ge=0, le=60)
    industry: str | None = Field(default=None, max_length=100)
    career_area: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)
    support_types: list[str] = Field(default_factory=list)
    expertise: list[str] = Field(default_factory=list)  # approved tag names
    capacity: int | None = Field(default=None, ge=1, le=10)
    level_completed: CourseLevel | None = None
    year_completed: int | None = Field(default=None, ge=2015, le=2100)
    still_enrolled: bool | None = None
    linkedin: str | None = Field(default=None, max_length=255)

    _strip = field_validator("name", "phone", "rollno", "designation", "company", "industry", "career_area", "bio", "mneeds", mode="before")(lambda cls, v: _clean(v))
    _pw = field_validator("password")(lambda cls, v: check_password(v))
    _un = field_validator("username")(lambda cls, v: check_username(v))

    @model_validator(mode="after")
    def role_rules(self):
        if self.role == "student" and len(self.interests) > 5:
            raise ValueError("Students can choose up to 5 interests.")
        if self.role == "mentor":
            if self.capacity is None:
                raise ValueError("Mentors must set a capacity between 1 and 10.")
            if len(self.expertise) > 6:
                raise ValueError("Mentors can choose up to 6 expertise areas.")
        return self


class LoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    _pw = field_validator("new_password")(lambda cls, v: check_password(v))


# ---------------- C2 Profile ----------------

class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course: Course | None = None
    courselevel: CourseLevel | None = None
    clear_courselevel: bool = False  # "Foundation" means no course level
    type: StudentType | None = None
    careergoal: str | None = None
    rollno: str | None = Field(default=None, max_length=30)
    mneeds: str | None = Field(default=None, max_length=2000)
    skills: list[SkillIn] | None = None


class MentorProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    iitm_program: Course | None = None
    level_completed: CourseLevel | None = None
    year_completed: int | None = Field(default=None, ge=2015, le=2100)
    designation: str | None = Field(default=None, max_length=150)
    still_enrolled: bool | None = None
    bio: str | None = Field(default=None, max_length=2000)
    company: str | None = Field(default=None, max_length=150)
    experience: float | None = Field(default=None, ge=0, le=60)
    capacity: int | None = Field(default=None, ge=1, le=10)  # US-04: 1-10
    pause: bool | None = None  # US-04 'Pause Requests' toggle (missing in FastAPI)
    industry: str | None = Field(default=None, max_length=100)
    career_area: str | None = Field(default=None, max_length=100)
    support_types: list[str] | None = None
    linkedin: str | None = Field(default=None, max_length=255)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    photo: str | None = None  # https URL or data:image/... URL; "" removes it
    student: StudentProfileUpdate | None = None
    mentor: MentorProfileUpdate | None = None

    _un = field_validator("username")(lambda cls, v: check_username(v))


class TagSelection(BaseModel):
    tag_id: int = Field(gt=0)
    want_to_learn: bool = False
    skill_level: int | None = Field(default=None, ge=1, le=5)


class ProfileTagsUpdate(BaseModel):
    tags: list[TagSelection] | None = None
    names: list[str] | None = None  # convenience: select approved tags by name (what the frontend has)


# ---------------- C3 Tags ----------------

class TagCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    type: TagType = TagType.expertise

    _strip = field_validator("name")(lambda cls, v: v.strip())


class TagAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    type: TagType | None = None
    action: Literal["approve", "reject"] | None = None


# ---------------- C5 Requests ----------------

class RequestCreate(BaseModel):
    mentor_id: int = Field(gt=0)
    student_id: int | None = None  # coordinator/admin assignment only
    student_message: str

    @field_validator("student_message")
    @classmethod
    def message_length(cls, value: str) -> str:
        value = value.strip()
        if not 50 <= len(value) <= 1500:
            raise ValueError("Your message must be between 50 and 1500 characters.")
        return value


class RequestDecision(BaseModel):
    action: Literal["accept", "reject"]
    reason: str | None = Field(default=None, max_length=500)  # optional (M1 US-08)

    _clean_reason = field_validator("reason")(lambda cls, v: (v.strip() or None) if isinstance(v, str) else v)


# ---------------- Admin (part of C14) ----------------

class VerificationUpdate(BaseModel):
    status: Literal["verified", "rejected", "pending"]
