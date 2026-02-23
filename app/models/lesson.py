import enum

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContentType(str, enum.Enum):
    video_lecture = "video_lecture"
    screencast = "screencast"
    interactive = "interactive"
    reading = "reading"


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("track_slug", "slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_slug: Mapped[str] = mapped_column(
        String, ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type"), default=ContentType.video_lecture
    )
    duration_min: Mapped[int] = mapped_column(Integer, default=0)

    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String, nullable=True)
    video_lecturer: Mapped[str] = mapped_column(String, nullable=False, default="")
    video_lecturer_title: Mapped[str | None] = mapped_column(String, nullable=True)
    video_lecturer_photo: Mapped[str | None] = mapped_column(String, nullable=True)
    video_lines: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    points_for_completion: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    quiz: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    assignment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
