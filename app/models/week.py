from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Week(Base):
    __tablename__ = "weeks"
    __table_args__ = (UniqueConstraint("track_slug", "week_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_slug: Mapped[str] = mapped_column(
        String, ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    badge_slug: Mapped[str] = mapped_column(String, nullable=False, default="")
    badge_emoji: Mapped[str] = mapped_column(String, nullable=False, default="")
