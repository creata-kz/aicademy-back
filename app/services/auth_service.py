import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def validate_telegram_init_data(init_data: str) -> dict | None:
    """Validate Telegram Mini App initData using HMAC-SHA256. Returns parsed user or None."""
    parsed = parse_qs(init_data, keep_blank_values=True)
    hash_value = parsed.pop("hash", [None])[0]
    if not hash_value:
        return None

    # Build data-check-string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    # HMAC: secret = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, hash_value):
        return None

    # Check auth_date freshness (1 hour window)
    auth_date = int(parsed.get("auth_date", [b"0"])[0])
    if time.time() - auth_date > 3600:
        return None

    # Parse user
    user_str = parsed.get("user", [None])[0]
    if not user_str:
        return None

    try:
        return json.loads(user_str)
    except (json.JSONDecodeError, TypeError):
        return None


def validate_telegram_login_widget(data: dict) -> dict | None:
    """Validate Telegram Login Widget data using SHA256 + HMAC-SHA256. Returns user dict or None."""
    hash_value = data.get("hash")
    if not hash_value:
        return None

    # Build data-check-string: all fields except hash (and None values), sorted by key, joined by \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items()) if k != "hash" and v is not None
    )

    # Login Widget: secret = SHA256(bot_token)
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()

    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, hash_value):
        return None

    # Check auth_date freshness (1 hour window)
    try:
        auth_date = int(data.get("auth_date", 0))
    except (ValueError, TypeError):
        return None
    if time.time() - auth_date > 3600:
        return None

    return data


def create_access_token(user_id: UUID, telegram_id: int | None, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    if telegram_id is not None:
        payload["telegram_id"] = telegram_id
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: str | None = None,
    username: str | None = None,
    photo_url: str | None = None,
) -> tuple[User, bool]:
    """Returns (user, is_new_user) tuple."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.telegram_username = username
        if photo_url is not None:
            user.photo_url = photo_url
        await db.commit()
        await db.refresh(user)
        return user, False

    user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        telegram_username=username,
        photo_url=photo_url,
        role=UserRole.student,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True


async def get_or_create_email_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str | None = None,
) -> tuple[User, bool]:
    """Register a new email user. Returns (user, True) or raises if email exists."""
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False  # email already taken

    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=UserRole.student,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True


async def authenticate_email_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Verify email+password credentials. Returns user or None."""
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
