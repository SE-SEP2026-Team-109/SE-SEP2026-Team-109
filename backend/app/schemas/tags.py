from pydantic import BaseModel, ConfigDict, Field

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