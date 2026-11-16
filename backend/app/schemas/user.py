from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserStatus
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.student
    username: str | None = None
    name: str | None = None
    phone: str | None = None


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
