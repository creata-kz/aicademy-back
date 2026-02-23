"""Align DB schema with frontend types - drop and recreate all tables.

Revision ID: 002
Revises: 001
Create Date: 2026-02-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES_TO_DROP = [
    "notifications", "quiz_responses", "quiz_pairs",
    "user_enrollments", "user_badges", "lesson_progress",
    "badges", "lessons", "weeks", "tracks", "users",
]

ENUMS_TO_DROP = ["user_role", "content_type", "badge_category"]


def upgrade() -> None:
    # Drop all existing tables
    for table in TABLES_TO_DROP:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    for enum_name in ENUMS_TO_DROP:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))

    # Recreate enums
    op.execute(sa.text("CREATE TYPE user_role AS ENUM ('student', 'teacher', 'mentor', 'admin')"))
    op.execute(sa.text("CREATE TYPE content_type AS ENUM ('video_lecture', 'screencast', 'interactive', 'reading')"))
    op.execute(sa.text("CREATE TYPE badge_category AS ENUM ('weekly', 'achievement', 'special', 'track')"))

    user_role = postgresql.ENUM("student", "teacher", "mentor", "admin", name="user_role", create_type=False)
    content_type = postgresql.ENUM("video_lecture", "screencast", "interactive", "reading", name="content_type", create_type=False)
    badge_category = postgresql.ENUM("weekly", "achievement", "special", "track", name="badge_category", create_type=False)

    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("photo_url", sa.String(), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default=sa.text("'student'")),
        sa.Column("archetype", sa.String(), nullable=True),
        sa.Column("archetype_stats", postgresql.JSONB(), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("streak_last_date", sa.Date(), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── tracks ── (aligned with frontend TrackData + TrackListItem)
    op.create_table(
        "tracks",
        sa.Column("slug", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("icon", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("color", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("bg", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("weeks", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("weeks_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lessons_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # ── weeks ── (aligned with frontend WeekData)
    op.create_table(
        "weeks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("track_slug", sa.String(), sa.ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("lessons_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("badge_slug", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("badge_emoji", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.UniqueConstraint("track_slug", "week_number"),
    )

    # ── lessons ── (aligned with frontend LessonData)
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("track_slug", sa.String(), sa.ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("content_type", content_type, nullable=False, server_default=sa.text("'video_lecture'")),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("video_lecturer", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("video_lecturer_title", sa.String(), nullable=True),
        sa.Column("video_lecturer_photo", sa.String(), nullable=True),
        sa.Column("video_lines", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("points_for_completion", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("quiz", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("assignment", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("track_slug", "slug"),
    )

    # ── badges ── (aligned with frontend BadgeData)
    op.create_table(
        "badges",
        sa.Column("slug", sa.String(), primary_key=True),
        sa.Column("track_slug", sa.String(), sa.ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("emoji", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("category", badge_category, nullable=False, server_default=sa.text("'weekly'")),
        sa.Column("trigger_type", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("trigger_value", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("points_reward", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # ── lesson_progress ── (aligned with frontend LessonProgress)
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_slug", sa.String(), nullable=False),
        sa.Column("lesson_slug", sa.String(), nullable=False),
        sa.Column("video_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quiz_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quiz_best_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("quiz_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("assignment_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("assignment_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lesson_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_points_earned", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "track_slug", "lesson_slug"),
    )

    # ── user_badges ──
    op.create_table(
        "user_badges",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_slug", sa.String(), sa.ForeignKey("badges.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("earned_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "badge_slug"),
    )

    # ── user_enrollments ──
    op.create_table(
        "user_enrollments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_slug", sa.String(), sa.ForeignKey("tracks.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "track_slug"),
    )

    # ── quiz_pairs (onboarding) ──
    op.create_table(
        "quiz_pairs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("option_a_icon", sa.String(), nullable=False),
        sa.Column("option_a_label", sa.String(), nullable=False),
        sa.Column("option_b_icon", sa.String(), nullable=False),
        sa.Column("option_b_label", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # ── quiz_responses (onboarding) ──
    op.create_table(
        "quiz_responses",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_pair_id", sa.Integer(), sa.ForeignKey("quiz_pairs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_option", sa.String(), nullable=False),
        sa.CheckConstraint("selected_option IN ('a', 'b')", name="check_selected_option"),
        sa.UniqueConstraint("user_id", "quiz_pair_id"),
    )

    # ── notifications ──
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("quiz_responses")
    op.drop_table("quiz_pairs")
    op.drop_table("user_enrollments")
    op.drop_table("user_badges")
    op.drop_table("lesson_progress")
    op.drop_table("badges")
    op.drop_table("lessons")
    op.drop_table("weeks")
    op.drop_table("tracks")
    op.drop_table("users")
    op.execute(sa.text("DROP TYPE IF EXISTS user_role"))
    op.execute(sa.text("DROP TYPE IF EXISTS content_type"))
    op.execute(sa.text("DROP TYPE IF EXISTS badge_category"))
