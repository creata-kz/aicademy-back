from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge
from app.models.progress import LessonProgress, UserBadge
from app.models.lesson import Lesson
from app.models.week import Week
from app.models.user import User


async def evaluate_badges(
    db: AsyncSession, user: User, track_slug: str
) -> list[str]:
    """Evaluate and award badges after a progress action. Returns list of newly earned badge slugs."""
    # Get all track badges
    result = await db.execute(select(Badge).where(Badge.track_slug == track_slug))
    badges = result.scalars().all()

    # Get already earned
    result = await db.execute(
        select(UserBadge.badge_slug).where(UserBadge.user_id == user.id)
    )
    earned = {row[0] for row in result.all()}

    newly_earned: list[str] = []

    for badge in badges:
        if badge.slug in earned:
            continue

        awarded = False

        if badge.trigger_type == "week_complete" and badge.trigger_value:
            week_number = badge.trigger_value.get("week_number")
            if week_number is not None:
                awarded = await _check_week_complete(db, user.id, track_slug, week_number)

        elif badge.trigger_type == "all_quizzes_perfect":
            awarded = await _check_all_quizzes_perfect(db, user.id, track_slug)

        elif badge.trigger_type == "streak" and badge.trigger_value:
            streak_days = badge.trigger_value.get("streak_days", 0)
            awarded = user.streak >= streak_days

        if awarded:
            db.add(UserBadge(user_id=user.id, badge_slug=badge.slug))
            if badge.points_reward > 0:
                user.xp += badge.points_reward
            newly_earned.append(badge.slug)

    if newly_earned:
        await db.commit()

    return newly_earned


async def _check_week_complete(
    db: AsyncSession, user_id: UUID, track_slug: str, week_number: int
) -> bool:
    """Check if all lessons in a week are completed."""
    # Get all lessons in this week
    result = await db.execute(
        select(Lesson.slug).where(
            and_(Lesson.track_slug == track_slug, Lesson.week_number == week_number)
        )
    )
    lesson_slugs = [row[0] for row in result.all()]
    if not lesson_slugs:
        return False

    # Check progress for each
    result = await db.execute(
        select(LessonProgress).where(
            and_(
                LessonProgress.user_id == user_id,
                LessonProgress.track_slug == track_slug,
                LessonProgress.lesson_slug.in_(lesson_slugs),
                LessonProgress.lesson_completed == True,
            )
        )
    )
    completed = result.scalars().all()
    return len(completed) == len(lesson_slugs)


async def _check_all_quizzes_perfect(
    db: AsyncSession, user_id: UUID, track_slug: str
) -> bool:
    """Check if all completed quizzes have score 100."""
    result = await db.execute(
        select(LessonProgress).where(
            and_(
                LessonProgress.user_id == user_id,
                LessonProgress.track_slug == track_slug,
                LessonProgress.quiz_completed == True,
            )
        )
    )
    progress_rows = result.scalars().all()
    if not progress_rows:
        return False
    return all(p.quiz_best_score == 100 for p in progress_rows)
