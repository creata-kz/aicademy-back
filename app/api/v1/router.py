from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.tracks import router as tracks_router
from app.api.v1.lessons import router as lessons_router
from app.api.v1.progress import router as progress_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.notifications import router as notifications_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(tracks_router)
api_router.include_router(lessons_router)
api_router.include_router(progress_router)
api_router.include_router(onboarding_router)
api_router.include_router(notifications_router)
