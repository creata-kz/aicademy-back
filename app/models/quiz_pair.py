import uuid

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QuizPair(Base):
    __tablename__ = "quiz_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    option_a_icon: Mapped[str] = mapped_column(String, nullable=False)
    option_a_label: Mapped[str] = mapped_column(String, nullable=False)
    option_b_icon: Mapped[str] = mapped_column(String, nullable=False)
    option_b_label: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class QuizResponse(Base):
    __tablename__ = "quiz_responses"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_pair_id"),
        CheckConstraint("selected_option IN ('a', 'b')", name="check_selected_option"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quiz_pair_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_pairs.id", ondelete="CASCADE"), nullable=False
    )
    selected_option: Mapped[str] = mapped_column(String, nullable=False)
