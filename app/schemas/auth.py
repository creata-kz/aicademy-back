from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class DevAuthRequest(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class TelegramWidgetAuth(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    token: str
    user: "UserOut"
    is_new_user: bool


from app.schemas.user import UserOut  # noqa: E402

AuthResponse.model_rebuild()
