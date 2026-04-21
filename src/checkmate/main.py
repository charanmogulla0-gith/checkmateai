import logging

from fastapi import FastAPI

from checkmate.config import settings
from checkmate.webhook import router as webhook_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Checkmate", description="AI code review bot", version="0.1.0")

app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "checkmate", "docs": "/docs"}
