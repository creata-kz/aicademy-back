from pydantic import BaseModel
from datetime import datetime, date
from uuid import UUID


class UserOut(BaseModel):
    id: UUID
    telegram_id: int | None = None
    telegram_username: str | None = None
    email: str | None = None
    email_verified: bool = False
    first_name: str
    last_name: str | None = None
    photo_url: str | None = None
    role: str
    archetype: str | None = None
    archetype_stats: dict | None = None
    xp: int
    streak: int
    streak_last_date: date | None = None
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    archetype: str | None = None
    archetype_stats: dict | None = None
    onboarding_complete: bool | None = None
