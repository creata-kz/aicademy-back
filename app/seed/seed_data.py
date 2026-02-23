"""
Seed script: loads JSON data from frontend into the database.
Run: python -m app.seed.seed_data
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Base, Track, Week, Lesson, Badge, QuizPair
from app.database import engine

# Path to frontend data
FRONTEND_DATA = Path(__file__).resolve().parent.parent.parent.parent / "aicademy" / "src" / "data"


async def seed():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        await seed_tracks(db)
        await seed_quiz_pairs(db)
        print("Seeding complete!")


async def seed_tracks(db: AsyncSession):
    tracks_index_path = FRONTEND_DATA / "tracks" / "index.json"
    if not tracks_index_path.exists():
        print(f"Warning: {tracks_index_path} not found, skipping tracks")
        return

    with open(tracks_index_path, "r", encoding="utf-8") as f:
        tracks_list = json.load(f)

    for idx, t in enumerate(tracks_list):
        slug = t["slug"]
        track_dir = FRONTEND_DATA / "tracks" / slug

        # Load track details if available
        track_file = track_dir / "track.json"
        track_data = {}
        if track_file.exists():
            with open(track_file, "r", encoding="utf-8") as f:
                track_data = json.load(f)

        # Upsert track
        existing = await db.execute(select(Track).where(Track.slug == slug))
        track = existing.scalar_one_or_none()

        track_fields = dict(
            title=track_data.get("title", t.get("title", "")),
            description=track_data.get("description", ""),
            icon=track_data.get("icon", t.get("icon", "")),
            color=track_data.get("color", t.get("color", "")),
            bg=track_data.get("bg", t.get("bg", "")),
            weeks=t.get("weeks", ""),
            weeks_count=track_data.get("weeks_count", 0),
            lessons_count=track_data.get("lessons_count", 0),
            total_points=track_data.get("total_points", 0),
            is_active=track_data.get("is_active", t.get("is_active", False)),
            sort_order=idx,
        )

        if track:
            for k, v in track_fields.items():
                setattr(track, k, v)
        else:
            track = Track(slug=slug, **track_fields)
            db.add(track)

        await db.flush()

        # Seed weeks
        weeks_file = track_dir / "weeks.json"
        if weeks_file.exists():
            await seed_weeks(db, slug, weeks_file)

        # Seed lessons
        lessons_dir = track_dir / "lessons"
        if lessons_dir.exists():
            await seed_lessons(db, slug, lessons_dir)

        # Seed badges
        badges_file = track_dir / "badges.json"
        if badges_file.exists():
            await seed_badges(db, slug, badges_file)

    await db.commit()
    print(f"Seeded {len(tracks_list)} tracks")


async def seed_weeks(db: AsyncSession, track_slug: str, weeks_file: Path):
    with open(weeks_file, "r", encoding="utf-8") as f:
        weeks_data = json.load(f)

    for w in weeks_data:
        existing = await db.execute(
            select(Week).where(
                Week.track_slug == track_slug, Week.week_number == w["week_number"]
            )
        )
        week = existing.scalar_one_or_none()

        week_fields = dict(
            title=w["title"],
            description=w.get("description", ""),
            lessons_count=w.get("lessons_count", 0),
            total_points=w.get("total_points", 0),
            badge_slug=w.get("badge_slug", ""),
            badge_emoji=w.get("badge_emoji", ""),
        )

        if week:
            for k, v in week_fields.items():
                setattr(week, k, v)
        else:
            week = Week(
                track_slug=track_slug,
                week_number=w["week_number"],
                **week_fields,
            )
            db.add(week)

    print(f"  Seeded {len(weeks_data)} weeks for {track_slug}")


async def seed_lessons(db: AsyncSession, track_slug: str, lessons_dir: Path):
    count = 0
    for lesson_file in sorted(lessons_dir.glob("*.json")):
        with open(lesson_file, "r", encoding="utf-8") as f:
            l = json.load(f)

        slug = l["slug"]
        existing = await db.execute(
            select(Lesson).where(Lesson.track_slug == track_slug, Lesson.slug == slug)
        )
        lesson = existing.scalar_one_or_none()

        lesson_data = dict(
            track_slug=track_slug,
            slug=slug,
            week_number=l["week_number"],
            lesson_number=l["lesson_number"],
            title=l["title"],
            description=l.get("description", ""),
            content_type=l.get("content_type", "video_lecture"),
            duration_min=l.get("duration_min", 0),
            thumbnail_url=l.get("thumbnail_url"),
            video_url=l.get("video_url"),
            video_lecturer=l.get("video_lecturer", ""),
            video_lecturer_title=l.get("video_lecturer_title"),
            video_lecturer_photo=l.get("video_lecturer_photo"),
            video_lines=l.get("video_lines", []),
            points_for_completion=l.get("points_for_completion", 0),
            summary=l.get("summary"),
            quiz=l.get("quiz", {}),
            assignment=l.get("assignment", {}),
        )

        if lesson:
            for k, v in lesson_data.items():
                if k != "track_slug":
                    setattr(lesson, k, v)
        else:
            lesson = Lesson(**lesson_data)
            db.add(lesson)

        count += 1

    print(f"  Seeded {count} lessons for {track_slug}")


async def seed_badges(db: AsyncSession, track_slug: str, badges_file: Path):
    with open(badges_file, "r", encoding="utf-8") as f:
        badges_data = json.load(f)

    for b in badges_data:
        existing = await db.execute(select(Badge).where(Badge.slug == b["slug"]))
        badge = existing.scalar_one_or_none()

        badge_fields = dict(
            track_slug=track_slug,
            title=b["title"],
            emoji=b.get("emoji", ""),
            category=b.get("category", "weekly"),
            trigger_type=b.get("trigger_type", ""),
            trigger_value=b.get("trigger_value", {}),
            points_reward=b.get("points_reward", 0),
        )

        if badge:
            for k, v in badge_fields.items():
                setattr(badge, k, v)
        else:
            badge = Badge(slug=b["slug"], **badge_fields)
            db.add(badge)

    print(f"  Seeded {len(badges_data)} badges for {track_slug}")


async def seed_quiz_pairs(db: AsyncSession):
    pairs = [
        {
            "id": 1,
            "question": "What drives you most?",
            "option_a_icon": "Film",
            "option_a_label": "Telling a Story",
            "option_b_icon": "Palette",
            "option_b_label": "Visual Aesthetics",
            "sort_order": 1,
        },
        {
            "id": 2,
            "question": "Pick your creative chaos",
            "option_a_icon": "Pen",
            "option_a_label": "Solo & Focused",
            "option_b_icon": "Sparkle",
            "option_b_label": "Team & Dynamic",
            "sort_order": 2,
        },
        {
            "id": 3,
            "question": "Which world appeals more?",
            "option_a_icon": "Scroll",
            "option_a_label": "Historical Reality",
            "option_b_icon": "Gamepad",
            "option_b_label": "Fantasy Logic",
            "sort_order": 3,
        },
        {
            "id": 4,
            "question": "Your tool of choice?",
            "option_a_icon": "Camera",
            "option_a_label": "The Lens",
            "option_b_icon": "Film",
            "option_b_label": "The Edit",
            "sort_order": 4,
        },
    ]

    for p in pairs:
        existing = await db.execute(select(QuizPair).where(QuizPair.id == p["id"]))
        pair = existing.scalar_one_or_none()
        if pair:
            for k, v in p.items():
                if k != "id":
                    setattr(pair, k, v)
        else:
            db.add(QuizPair(**p))

    await db.commit()
    print(f"Seeded {len(pairs)} quiz pairs")


if __name__ == "__main__":
    asyncio.run(seed())
