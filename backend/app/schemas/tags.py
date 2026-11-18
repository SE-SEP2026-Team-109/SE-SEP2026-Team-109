from pydantic import BaseModel, ConfigDict

from app.models.enums import TagType


class TagRead(BaseModel):
    id: int
    name: str
    type: TagType

    model_config = ConfigDict(from_attributes=True)