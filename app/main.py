import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set Telegram bot webhook on startup
    import httpx
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_url and settings.TELEGRAM_BOT_TOKEN:
        webhook_url = f"https://{railway_url}/api/v1/bot/webhook"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
                    json={"url": webhook_url},
                )
                logger.info("Webhook set: %s", resp.json())
        except Exception as e:
            logger.error("Failed to set webhook: %s", e)
    yield


app = FastAPI(
    title="AI Academy API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
