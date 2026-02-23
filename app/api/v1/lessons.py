from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.progress import (
    QuizSubmission,
    QuizResult,
    VideoCompleteResponse,
    AssignmentCompleteResponse,
)
from app.services.progress_service import (
    mark_video_complete,
    submit_quiz,
    complete_assignment,
)

router = APIRouter(prefix="/tracks", tags=["progress"])


@router.post(
    "/{slug}/lessons/{lesson_slug}/complete-video",
    response_model=VideoCompleteResponse,
)
async def complete_video(
    slug: str,
    lesson_slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    points = await mark_video_complete(db, user, slug, lesson_slug)
    return VideoCompleteResponse(points_earned=points)


@router.post(
    "/{slug}/lessons/{lesson_slug}/submit-quiz",
    response_model=QuizResult,
)
async def submit_quiz_endpoint(
    slug: str,
    lesson_slug: str,
    body: QuizSubmission,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await submit_quiz(db, user, slug, lesson_slug, body.answers)
    return QuizResult(**result)


@router.post(
    "/{slug}/lessons/{lesson_slug}/complete-assignment",
    response_model=AssignmentCompleteResponse,
)
async def complete_assignment_endpoint(
    slug: str,
    lesson_slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    points = await complete_assignment(db, user, slug, lesson_slug)
    return AssignmentCompleteResponse(points_earned=points)
