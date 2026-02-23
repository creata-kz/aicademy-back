from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.progress import LessonProgress
from app.models.week import Week
from app.models.user import User
from app.services.streak_service import update_streak
from app.services.badge_service import evaluate_badges


async def get_or_create_progress(
    db: AsyncSession, user_id: UUID, track_slug: str, lesson_slug: str
) -> LessonProgress:
    result = await db.execute(
        select(LessonProgress).where(
            and_(
                LessonProgress.user_id == user_id,
                LessonProgress.track_slug == track_slug,
                LessonProgress.lesson_slug == lesson_slug,
            )
        )
    )
    progress = result.scalar_one_or_none()
    if progress:
        return progress

    progress = LessonProgress(
        user_id=user_id,
        track_slug=track_slug,
        lesson_slug=lesson_slug,
    )
    db.add(progress)
    await db.flush()
    return progress


async def mark_video_complete(
    db: AsyncSession, user: User, track_slug: str, lesson_slug: str
) -> int:
    """Mark video as complete. Returns points earned (0 if already done)."""
    lesson = await _get_lesson(db, track_slug, lesson_slug)
    if not lesson:
        return 0

    progress = await get_or_create_progress(db, user.id, track_slug, lesson_slug)

    if progress.video_completed:
        return 0

    points = lesson.points_for_completion
    progress.video_completed = True
    progress.total_points_earned += points
    user.xp += points

    await update_streak(db, user)
    await db.commit()
    await evaluate_badges(db, user, track_slug)

    return points


async def submit_quiz(
    db: AsyncSession,
    user: User,
    track_slug: str,
    lesson_slug: str,
    answers: dict[str, str],
) -> dict:
    """Submit quiz answers. Returns score, points_earned, correct_count, total_count, passed."""
    lesson = await _get_lesson(db, track_slug, lesson_slug)
    if not lesson:
        return {"score": 0, "points_earned": 0, "correct_count": 0, "total_count": 0, "passed": False}

    quiz = lesson.quiz or {}
    questions = quiz.get("questions", [])
    pass_score = quiz.get("pass_score_percent", 60)
    points_max = quiz.get("points_max", 0)

    # Grade answers server-side
    correct_count = 0
    total_count = len(questions)

    for q in questions:
        qid = q["id"]
        user_answer = answers.get(qid)
        if user_answer is None:
            continue
        correct_options = [opt["text"] for opt in q.get("options", []) if opt.get("is_correct")]
        if user_answer in correct_options:
            correct_count += 1

    score = round((correct_count / total_count) * 100) if total_count > 0 else 0
    passed = score >= pass_score

    progress = await get_or_create_progress(db, user.id, track_slug, lesson_slug)
    progress.quiz_attempts += 1

    # Calculate delta XP (only if score improved)
    previous_best = progress.quiz_best_score
    previous_xp = round((previous_best / 100) * points_max)
    new_xp = round((score / 100) * points_max)
    points_earned = max(0, new_xp - previous_xp)

    progress.quiz_completed = True
    progress.quiz_best_score = max(progress.quiz_best_score, score)

    if points_earned > 0:
        progress.total_points_earned += points_earned
        user.xp += points_earned

    await update_streak(db, user)
    await db.commit()
    await evaluate_badges(db, user, track_slug)

    return {
        "score": score,
        "points_earned": points_earned,
        "correct_count": correct_count,
        "total_count": total_count,
        "passed": passed,
    }


async def complete_assignment(
    db: AsyncSession, user: User, track_slug: str, lesson_slug: str
) -> int:
    """Complete assignment. Returns points earned."""
    lesson = await _get_lesson(db, track_slug, lesson_slug)
    if not lesson:
        return 0

    progress = await get_or_create_progress(db, user.id, track_slug, lesson_slug)

    if progress.assignment_completed:
        return 0

    assignment = lesson.assignment or {}
    points_max = assignment.get("points_max", 0)

    progress.assignment_completed = True
    progress.assignment_points = points_max
    progress.total_points_earned += points_max
    progress.lesson_completed = True
    progress.completed_at = datetime.now(timezone.utc)

    user.xp += points_max

    await update_streak(db, user)
    await db.commit()
    await evaluate_badges(db, user, track_slug)

    return points_max


async def get_track_progress(
    db: AsyncSession, user_id: UUID, track_slug: str
) -> dict:
    """Get full track progress for a user."""
    # Get all weeks
    result = await db.execute(
        select(Week).where(Week.track_slug == track_slug).order_by(Week.week_number)
    )
    weeks = result.scalars().all()

    # Get all user progress for this track
    result = await db.execute(
        select(LessonProgress).where(
            and_(
                LessonProgress.user_id == user_id,
                LessonProgress.track_slug == track_slug,
            )
        )
    )
    all_progress = {p.lesson_slug: p for p in result.scalars().all()}

    # Get all lessons grouped by week
    result = await db.execute(
        select(Lesson).where(Lesson.track_slug == track_slug).order_by(
            Lesson.week_number, Lesson.lesson_number
        )
    )
    all_lessons = result.scalars().all()
    lessons_by_week: dict[int, list] = {}
    for l in all_lessons:
        lessons_by_week.setdefault(l.week_number, []).append(l)

    # Build week progress
    week_progress = []
    total_points = 0
    current_lesson_slug = None

    for w in weeks:
        week_lessons = lessons_by_week.get(w.week_number, [])
        completed = sum(
            1 for l in week_lessons
            if all_progress.get(l.slug) and all_progress[l.slug].lesson_completed
        )
        total = len(week_lessons)
        pct = round((completed / total) * 100) if total > 0 else 0
        week_progress.append({
            "week_number": w.week_number,
            "lessons_total": total,
            "lessons_completed": completed,
            "completion_percent": pct,
            "completed": completed == total and total > 0,
        })

    # Total points
    total_points = sum(p.total_points_earned for p in all_progress.values())

    # Find current lesson (first incomplete)
    for w in weeks:
        for l in lessons_by_week.get(w.week_number, []):
            p = all_progress.get(l.slug)
            if not p or not p.lesson_completed:
                current_lesson_slug = l.slug
                break
        if current_lesson_slug:
            break

    # Get earned badges
    from app.models.progress import UserBadge
    from app.models.badge import Badge

    result = await db.execute(
        select(UserBadge.badge_slug).where(UserBadge.user_id == user_id)
    )
    earned_badge_slugs = [row[0] for row in result.all()]

    # Filter to this track's badges
    result = await db.execute(
        select(Badge.slug).where(Badge.track_slug == track_slug)
    )
    track_badge_slugs = {row[0] for row in result.all()}
    badges_earned = [s for s in earned_badge_slugs if s in track_badge_slugs]

    return {
        "track_slug": track_slug,
        "total_points": total_points,
        "weeks": week_progress,
        "badges_earned": badges_earned,
        "current_lesson_slug": current_lesson_slug,
    }


async def _get_lesson(
    db: AsyncSession, track_slug: str, lesson_slug: str
) -> Lesson | None:
    result = await db.execute(
        select(Lesson).where(
            and_(Lesson.track_slug == track_slug, Lesson.slug == lesson_slug)
        )
    )
    return result.scalar_one_or_none()
