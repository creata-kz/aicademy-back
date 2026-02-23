from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.schemas.auth import TelegramAuthRequest, DevAuthRequest, TelegramWidgetAuth, AuthResponse
from app.schemas.user import UserOut
from app.services.auth_service import (
    validate_telegram_init_data,
    validate_telegram_login_widget,
    create_access_token,
    get_or_create_user,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(body: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate via Telegram Mini App initData or dev mode."""
    # Try Telegram validation first
    tg_user = validate_telegram_init_data(body.init_data)

    if tg_user is None:
        # In dev mode, try parsing init_data as JSON dev user
        if not settings.DEV_MODE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram data")

        import json
        try:
            dev_data = json.loads(body.init_data)
            tg_user = dev_data
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth data")

    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing telegram id")

    user, is_new_user = await get_or_create_user(
        db,
        telegram_id=telegram_id,
        first_name=tg_user.get("first_name", "User"),
        last_name=tg_user.get("last_name"),
        username=tg_user.get("username"),
        photo_url=tg_user.get("photo_url"),
    )

    token = create_access_token(user.id, user.telegram_id, user.role.value)

    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
        is_new_user=is_new_user,
    )


@router.post("/telegram-widget", response_model=AuthResponse)
async def auth_telegram_widget(body: TelegramWidgetAuth, db: AsyncSession = Depends(get_db)):
    """Authenticate via Telegram Login Widget (web users)."""
    widget_data = body.model_dump()
    validated = validate_telegram_login_widget(widget_data)

    if validated is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram widget data")

    user, is_new_user = await get_or_create_user(
        db,
        telegram_id=body.id,
        first_name=body.first_name,
        last_name=body.last_name,
        username=body.username,
        photo_url=body.photo_url,
    )

    token = create_access_token(user.id, user.telegram_id, user.role.value)

    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
        is_new_user=is_new_user,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(user: User = Depends(get_current_user)):
    """Refresh JWT token."""
    token = create_access_token(user.id, user.telegram_id, user.role.value)
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
        is_new_user=False,
    )
