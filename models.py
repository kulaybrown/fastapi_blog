from __future__ import annotations
from datetime import UTC, datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")
    image_file: Mapped[str | None] = mapped_column(
      String(255), nullable=True, default=None
    )

    @property
    def image_path(self) -> str:
        if self.image_file:
            return f"/static/images/{self.image_file}"
        return "/static/images/default-avatar.png"

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date_posted: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    author: Mapped[User] = relationship(back_populates="posts")