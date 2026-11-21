"""Pydantic schemas for mentoring requests."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import RequestSource, RequestStatus


class RequestCreate(BaseModel):
    """Data required to create a mentoring request."""

    mentor_id: int
    student_id: int | None = None
    student_message: str = Field(min_length=50, max_length=1500)

    @field_validator("student_message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Reject messages that contain only whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("The request message cannot be empty.")
        return value


class RequestDecision(BaseModel):
    """Data submitted by a mentor when accepting or rejecting a request."""

    action: Literal["accept", "reject"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str | None) -> str | None:
        """Trim optional mentor response text."""
        return value.strip() if value else None

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        """Require a reason when the mentor rejects a request."""
        if self.action == "reject" and not self.reason:
            raise ValueError("A reason is required when rejecting a request.")
        return self


class RequestRead(BaseModel):
    """Public representation of a mentoring request."""

    id: int
    sid: int
    mid: int
    created_on: datetime | None
    changed_on: datetime | None
    student_message: str | None
    assigned_by: int | None
    req_source: RequestSource
    mentor_response: str | None
    status: RequestStatus

    model_config = ConfigDict(from_attributes=True)

