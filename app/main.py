"""Zoom Meeting Intelligence - FastAPI Application.

Main entry point for the service. Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8900 --reload

Or:
    python -m app.main
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, set_manager
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.services.meeting_manager import MeetingManager

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info(
        "starting",
        host=settings.host,
        port=settings.port,
        demo_mode=settings.demo_mode,
        has_recall=settings.has_recall_credentials,
        has_anthropic=settings.has_anthropic_credentials,
    )

    manager = MeetingManager()
    set_manager(manager)
    app.state.manager = manager

    yield

    logger.info("shutting_down")
    await manager.shutdown()


app = FastAPI(
    title="Zoom Meeting Intelligence",
    description=(
        "AI-powered meeting assistant that joins Zoom, Google Meet, and Teams calls. "
        "Transcribes with speaker identification, contributes real-time insights to chat, "
        "and delivers comprehensive post-meeting summaries."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    """Health check and service info."""
    return {
        "service": "Zoom Meeting Intelligence",
        "version": "0.1.0",
        "status": "running",
        "demo_mode": settings.demo_mode,
        "endpoints": {
            "join_meeting": "POST /api/v1/meetings/join",
            "get_meeting": "GET /api/v1/meetings/{meeting_id}",
            "get_transcript": "GET /api/v1/meetings/{meeting_id}/transcript",
            "end_meeting": "POST /api/v1/meetings/{meeting_id}/end",
            "list_meetings": "GET /api/v1/meetings",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "recall_configured": settings.has_recall_credentials,
        "anthropic_configured": settings.has_anthropic_credentials,
        "demo_mode": settings.demo_mode,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
