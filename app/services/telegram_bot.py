"""Telegram Bot service for web auth via bot confirmation."""

import secrets
import time

import httpx

from app.config import settings

# In-memory auth sessions: token → {telegram_id, status, created_at}
_auth_sessions: dict[str, dict] = {}

# Cleanup old sessions every call
def _cleanup():
    now = time.time()
    expired = [k for k, v in _auth_sessions.items() if now - v["created_at"] > 300]
    for k in expired:
        del _auth_sessions[k]


def create_auth_session() -> str:
    """Create a new auth session, return the token."""
    _cleanup()
    token = secrets.token_urlsafe(32)
    _auth_sessions[token] = {
        "telegram_id": None,
        "telegram_user": None,
        "status": "pending",
        "created_at": time.time(),
    }
    return token


def get_auth_session(token: str) -> dict | None:
    """Get auth session by token."""
    _cleanup()
    return _auth_sessions.get(token)


def confirm_auth_session(token: str, telegram_id: int, telegram_user: dict):
    """Mark auth session as confirmed with user data."""
    session = _auth_sessions.get(token)
    if session and session["status"] == "pending":
        session["status"] = "confirmed"
        session["telegram_id"] = telegram_id
        session["telegram_user"] = telegram_user


async def send_telegram_message(chat_id: int, text: str, reply_markup: dict | None = None):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        return resp.json()


async def answer_callback_query(callback_query_id: str, text: str = ""):
    """Answer a callback query."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "callback_query_id": callback_query_id,
            "text": text,
        })


async def edit_message_text(chat_id: int, message_id: int, text: str):
    """Edit a message."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageText"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
        })


async def handle_update(update: dict):
    """Process incoming Telegram update."""

    # Handle /start command with auth token
    if "message" in update:
        message = update["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]
        user = message.get("from", {})

        if text.startswith("/start auth_"):
            token = text.replace("/start auth_", "")
            session = get_auth_session(token)

            if not session:
                await send_telegram_message(chat_id, "This login link has expired. Please try again.")
                return

            if session["status"] != "pending":
                await send_telegram_message(chat_id, "This login has already been used.")
                return

            first_name = user.get("first_name", "User")
            await send_telegram_message(
                chat_id,
                f"Hi {first_name}! Confirm login to <b>AI Academy</b>?",
                reply_markup={
                    "inline_keyboard": [[
                        {
                            "text": "Confirm Login",
                            "callback_data": f"auth_confirm:{token}",
                        },
                        {
                            "text": "Cancel",
                            "callback_data": f"auth_cancel:{token}",
                        },
                    ]]
                },
            )
            return

        if text == "/start":
            await send_telegram_message(
                chat_id,
                "Welcome to <b>AI Academy</b>! Use the web app to get started.",
            )
            return

    # Handle callback queries (button presses)
    if "callback_query" in update:
        callback = update["callback_query"]
        data = callback.get("data", "")
        callback_id = callback["id"]
        user = callback.get("from", {})
        message = callback.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if data.startswith("auth_confirm:"):
            token = data.replace("auth_confirm:", "")
            session = get_auth_session(token)

            if session and session["status"] == "pending":
                confirm_auth_session(token, user["id"], {
                    "id": user["id"],
                    "first_name": user.get("first_name", "User"),
                    "last_name": user.get("last_name"),
                    "username": user.get("username"),
                })
                await answer_callback_query(callback_id, "Logged in!")
                if chat_id and message_id:
                    await edit_message_text(chat_id, message_id, "You are now logged in to <b>AI Academy</b>!")
            else:
                await answer_callback_query(callback_id, "Session expired")

            return

        if data.startswith("auth_cancel:"):
            await answer_callback_query(callback_id, "Cancelled")
            if chat_id and message_id:
                await edit_message_text(chat_id, message_id, "Login cancelled.")
            return
