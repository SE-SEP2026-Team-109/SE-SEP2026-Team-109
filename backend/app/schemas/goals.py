
"""Pydantic schemas for student goals."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GoalVisibility


GoalStatus = Literal["todo", "in_progress", "done"]


class GoalRead(BaseModel):
    """Public representation of a student's goal."""

    id: int
    student_id: int = Field(validation_alias="sid")
    mentoring_id: int | None = Field(validation_alias="mgid")
    title: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    status: GoalStatus
    deadline: datetime | None
    created_on: datetime | None
    visibility: GoalVisibility | None

    model_config = ConfigDict(from_attributes=True)


class GoalPage(BaseModel):
    """Paginated response containing a student's goals."""

    items: list[GoalRead]
    page: int
    page_size: int
    total: int
