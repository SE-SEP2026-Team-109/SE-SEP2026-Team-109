from pydantic import BaseModel, ConfigDict

from app.models.enums import TagType


class DirectoryTagRead(BaseModel):
    """Represents an approved tag displayed on a mentor's directory card."""

    id: int
    name: str
    type: TagType

    model_config = ConfigDict(from_attributes=True)


class MentorDirectoryItem(BaseModel):
    """Public information needed to display one mentor in the directory."""

    id: int
    name: str | None
    photo: str | None

    designation: str | None
    company: str | None
    bio: str | None
    experience: float | None
    capacity: int

    free_slots: int
    is_paused: bool
    can_request: bool

    tags: list[DirectoryTagRead]


class MentorDirectoryResponse(BaseModel):
    """Paginated response containing mentor directory results."""

    items: list[MentorDirectoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int