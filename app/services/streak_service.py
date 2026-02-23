from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def update_streak(db: AsyncSession, user: User) -> int:
    """Update user streak. Returns new streak value."""
    today = date.today()

    if user.streak_last_date == today:
        return user.streak  # already active today

    if user.streak_last_date == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1

    user.streak_last_date = today
    await db.commit()
    await db.refresh(user)
    return user.streak
