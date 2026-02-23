from fastapi import APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.progress import LessonProgress as LessonProgressModel
from app.schemas.progress import LessonProgressOut, TrackProgressOut
from app.services.progress_service import get_track_progress

router = APIRouter(prefix="/tracks", tags=["progress"])


@router.get("/{slug}/progress", response_model=TrackProgressOut)
async def track_progress(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_track_progress(db, user.id, slug)
    return TrackProgressOut(**data)


@router.get("/{slug}/lessons/{lesson_slug}/progress", response_model=LessonProgressOut)
async def lesson_progress(
    slug: str,
    lesson_slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LessonProgressModel).where(
            and_(
                LessonProgressModel.user_id == user.id,
                LessonProgressModel.track_slug == slug,
                LessonProgressModel.lesson_slug == lesson_slug,
            )
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        return LessonProgressOut(
            lesson_slug=lesson_slug,
            video_completed=False,
            quiz_completed=False,
            quiz_best_score=0,
            quiz_attempts=0,
            assignment_completed=False,
            assignment_points=0,
            lesson_completed=False,
            total_points_earned=0,
            completed_at=None,
        )

    return LessonProgressOut(
        lesson_slug=progress.lesson_slug,
        video_completed=progress.video_completed,
        quiz_completed=progress.quiz_completed,
        quiz_best_score=progress.quiz_best_score,
        quiz_attempts=progress.quiz_attempts,
        assignment_completed=progress.assignment_completed,
        assignment_points=progress.assignment_points,
        lesson_completed=progress.lesson_completed,
        total_points_earned=progress.total_points_earned,
        completed_at=progress.completed_at,
    )
