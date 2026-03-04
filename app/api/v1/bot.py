from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.schemas.user import UserOut
from app.schemas.auth import AuthResponse
from app.services.auth_service import create_access_token, get_or_create_user
from app.services.telegram_bot import (
    create_auth_session,
    get_auth_session,
    confirm_auth_session,
    handle_update,
)

router = APIRouter(tags=["bot"])


@router.post("/bot/webhook")
async def telegram_webhook(request: Request):
    """Telegram Bot webhook — receives updates from Telegram."""
    update = await request.json()
    await handle_update(update)
    return {"ok": True}


class TelegramBotInitRequest(BaseModel):
    return_url: str = ""


@router.post("/auth/telegram-bot/init")
async def init_telegram_bot_auth(body: TelegramBotInitRequest = TelegramBotInitRequest()):
    """Create an auth session for Telegram bot login. Returns token and bot URL."""
    token = create_auth_session(return_url=body.return_url)
    return {
        "token": token,
        "bot_url": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=auth_{token}",
    }


@router.get("/auth/telegram-bot/confirm-redirect")
async def confirm_redirect(
    token: str = Query(...),
    tg_id: int = Query(...),
    first_name: str = Query("User"),
    last_name: str = Query(""),
    username: str = Query(""),
):
    """Confirm auth session via URL click and redirect to website."""
    session = get_auth_session(token)

    if not session or session["status"] != "pending":
        return RedirectResponse(url=session.get("return_url", "/") if session else "/")

    confirm_auth_session(token, tg_id, {
        "id": tg_id,
        "first_name": first_name,
        "last_name": last_name or None,
        "username": username or None,
    })

    return_url = session.get("return_url", "")
    if return_url:
        return RedirectResponse(url=return_url)

    return {"status": "confirmed", "message": "You can close this tab and return to the website."}


@router.get("/auth/telegram-bot/status/{token}")
async def check_telegram_bot_auth(token: str, db: AsyncSession = Depends(get_db)):
    """Poll auth session status. Returns JWT when confirmed."""
    session = get_auth_session(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session expired or not found",
        )

    if session["status"] == "pending":
        return {"status": "pending"}

    if session["status"] == "confirmed":
        tg_user = session["telegram_user"]

        user, is_new_user = await get_or_create_user(
            db,
            telegram_id=tg_user["id"],
            first_name=tg_user.get("first_name", "User"),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
        )

        jwt_token = create_access_token(user.id, user.telegram_id, user.role.value)

        return {
            "status": "confirmed",
            "token": jwt_token,
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "is_new_user": is_new_user,
        }
