from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.week import Week
from app.models.lesson import Lesson
from app.models.badge import Badge
from app.models.enrollment import UserEnrollment
from app.schemas.track import TrackListItem, TrackData
from app.schemas.week import WeekData
from app.schemas.lesson import LessonSummary, LessonData, strip_quiz_answers
from app.schemas.badge import BadgeOut

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackListItem])
async def list_tracks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Track).order_by(Track.sort_order))
    tracks = result.scalars().all()
    return [TrackListItem.model_validate(t) for t in tracks]


@router.get("/{slug}", response_model=TrackData)
async def get_track(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return TrackData.model_validate(track)


@router.get("/{slug}/weeks", response_model=list[WeekData])
async def get_weeks(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Week).where(Week.track_slug == slug).order_by(Week.week_number)
    )
    weeks = result.scalars().all()
    return [WeekData.model_validate(w) for w in weeks]


@router.get("/{slug}/weeks/{week_num}/lessons", response_model=list[LessonSummary])
async def get_week_lessons(slug: str, week_num: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lesson)
        .where(Lesson.track_slug == slug, Lesson.week_number == week_num)
        .order_by(Lesson.lesson_number)
    )
    lessons = result.scalars().all()
    return [LessonSummary.model_validate(l) for l in lessons]


@router.get("/{slug}/lessons/{lesson_slug}", response_model=LessonData)
async def get_lesson(slug: str, lesson_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lesson).where(Lesson.track_slug == slug, Lesson.slug == lesson_slug)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return strip_quiz_answers(lesson)


@router.get("/{slug}/badges", response_model=list[BadgeOut])
async def get_badges(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Badge).where(Badge.track_slug == slug))
    badges = result.scalars().all()
    return [BadgeOut.model_validate(b) for b in badges]


@router.post("/{slug}/enroll")
async def enroll_track(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check track exists
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Check not already enrolled
    result = await db.execute(
        select(UserEnrollment).where(
            UserEnrollment.user_id == user.id, UserEnrollment.track_slug == slug
        )
    )
    if result.scalar_one_or_none():
        return {"message": "Already enrolled", "track_slug": slug}

    enrollment = UserEnrollment(user_id=user.id, track_slug=slug)
    db.add(enrollment)
    await db.commit()
    return {"message": "Enrolled successfully", "track_slug": slug}
