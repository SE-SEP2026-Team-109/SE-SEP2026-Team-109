from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal
from app.models.enums import TagType


class TagRead(BaseModel):
    id: int
    name: str
    type: TagType
    model_config = ConfigDict(from_attributes=True)

class TagSelectionInput(BaseModel):
    tag_id: int = Field(gt=0)
    want_to_learn: bool = False
    skill_level: int | None = None


class ProfileTagsUpdate(BaseModel):
    tags: list[TagSelectionInput]


class ProfileTagRead(BaseModel):
    tag: TagRead
    want_to_learn: bool
    skill_level: int | None

    model_config = ConfigDict(from_attributes=True)


class TagSuggestionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: TagType

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tag name cannot be empty")
        return value


class TagSuggestionRead(BaseModel):
    id: int
    name: str
    type: TagType
    t_status: bool

    model_config = ConfigDict(from_attributes=True)


class TagAdminCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: TagType

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tag name cannot be empty")
        return value


class TagAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: TagType | None = None
    action: Literal["approve", "reject"] | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Tag name cannot be empty")
        return value


class TagAdminRead(BaseModel):
    id: int
    name: str
    type: TagType
    t_status: bool

    model_config = ConfigDict(from_attributes=True)

