
"""Pydantic schemas for mentoring sessions."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MentorAvailabilityStatus, SessionStatus


class SessionCreate(BaseModel):
    """Data required for a student to book a session."""

    available_id: int
    notes: str | None = Field(default=None, max_length=1500)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class SessionDecision(BaseModel):
    """Data submitted by a mentor when responding to a booking."""

    action: Literal["accept", "decline"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class SessionReschedule(BaseModel):
    """Data required to reschedule a session."""

    available_id: int


class AvailabilityRead(BaseModel):
    """Availability details associated with a session."""

    id: int
    mid: int
    date: date | None
    start_time: datetime
    end_time: datetime
    status: MentorAvailabilityStatus

    model_config = ConfigDict(from_attributes=True)


class SessionRead(BaseModel):
    """Public representation of a mentoring session."""

    id: int
    mgid: int
    available_id: int
    status: SessionStatus
    mentor_response: str | None
    notes: str | None
    availability: AvailabilityRead

    model_config = ConfigDict(from_attributes=True)
