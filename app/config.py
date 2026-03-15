import json
import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_JWT_SECRET = "super-secret-jwt-key-change-in-production"


class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = "aiacademy_test_bot"
    JWT_SECRET: str = _INSECURE_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    DEV_MODE: bool = False
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "AI Academy <onboarding@resend.dev>"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = True
    ENVIRONMENT: str = "dev"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def check_jwt_secret(self) -> "Settings":
        if self.JWT_SECRET == _INSECURE_JWT_SECRET and self.ENVIRONMENT != "dev":
            raise ValueError(
                "JWT_SECRET must be set to a strong random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
