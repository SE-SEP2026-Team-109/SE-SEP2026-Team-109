from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TagType

if TYPE_CHECKING:
    from app.models.user import User


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[TagType | None] = mapped_column(SAEnum(TagType), default=TagType.domain)
    t_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user_tags: Mapped[list["UserTag"]] = relationship(back_populates="tag")


class UserTag(Base):
    __tablename__ = "user_tags"

    uid: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)
    want_to_learn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skill_level: Mapped[int | None] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="user_tags")
    tag: Mapped["Tag"] = relationship(back_populates="user_tags")
