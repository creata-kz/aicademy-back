import enum

from sqlalchemy import String, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BadgeCategory(str, enum.Enum):
    weekly = "weekly"
    achievement = "achievement"
    special = "special"
    track = "track"


class Badge(Base):
    __tablename__ = "badges"

    slug: Mapped[str] = mapped_column(String, primary_key=True)
    track_slug: Mapped[str] = mapped_column(
        String, ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    emoji: Mapped[str] = mapped_column(String, nullable=False, default="")
    category: Mapped[BadgeCategory] = mapped_column(
        Enum(BadgeCategory, name="badge_category"), default=BadgeCategory.weekly
    )
    trigger_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    trigger_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    points_reward: Mapped[int] = mapped_column(Integer, default=0)
