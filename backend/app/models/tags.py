"""C3 tables: ``tag`` (global taxonomy) and ``user_tags`` (which user picked which tag).

``t_status`` False means "suggested, waiting for admin approval"; such tags cannot be
selected by anyone (M2 C3 rule). Ported unchanged from FastAPI.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import TagType


class Tag(db.Model):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("name", "type", name="uq_tag_name_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[TagType | None] = mapped_column(SAEnum(TagType), default=TagType.domain)
    t_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user_tags: Mapped[list["UserTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class UserTag(db.Model):
    __tablename__ = "user_tags"

    uid: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)
    want_to_learn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skill_level: Mapped[int | None] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="user_tags")  # noqa: F821
    tag: Mapped["Tag"] = relationship(back_populates="user_tags")
