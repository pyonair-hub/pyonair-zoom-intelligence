"""API routes for the Zoom Meeting Intelligence service.

Provides endpoints to:
- Join a meeting
- Get meeting status and live transcript
- End a meeting and get summary
- Receive Recall.ai webhooks
- List all meetings
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.logging import get_logger
from app.models.meeting import (
    JoinMeetingRequest,
    JoinMeetingResponse,
    Meeting,
    MeetingStatus,
    MeetingSummary,
)
from app.services.meeting_manager import MeetingManager

logger = get_logger("api")

router = APIRouter(prefix="/api/v1", tags=["meetings"])

# Global meeting manager -- initialized in app startup
_manager: Optional[MeetingManager] = None


def get_manager() -> MeetingManager:
    """Get the global meeting manager instance."""
    if _manager is None:
        raise RuntimeError("MeetingManager not initialized")
    return _manager


def set_manager(manager: MeetingManager) -> None:
    """Set the global meeting manager instance (called during app startup)."""
    global _manager
    _manager = manager


@router.post("/meetings/join", response_model=JoinMeetingResponse)
async def join_meeting(request: JoinMeetingRequest) -> JoinMeetingResponse:
    """Join a meeting and start the AI assistant.

    Send a meeting URL (Zoom, Google Meet, or Teams) and the bot will
    join as a participant named "Pyonair AI" (or custom name).

    In demo mode, a simulated transcript will stream automatically.
    """
    manager = get_manager()
    logger.info("join_meeting_request", meeting_url=request.meeting_url)
    response = await manager.join_meeting(request)
    return response


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str) -> dict[str, Any]:
    """Get the current state of a meeting.

    Returns meeting metadata, live transcript, action items,
    decisions, and insights discovered so far.
    """
    manager = get_manager()
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {
        "id": meeting.id,
        "status": meeting.status.value,
        "platform": meeting.platform.value,
        "meeting_url": meeting.meeting_url,
        "bot_display_name": meeting.bot_display_name,
        "bot_id": meeting.bot_id,
        "participants": meeting.participants,
        "transcript_segments": len(meeting.transcript),
        "action_items": [item.model_dump() for item in meeting.action_items],
        "decisions": [d.model_dump() for d in meeting.decisions],
        "insights": [i.model_dump() for i in meeting.insights[-20:]],
        "chat_messages_sent": [m.model_dump() for m in meeting.chat_messages_sent],
        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
        "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
        "summary": meeting.summary,
    }


@router.get("/meetings/{meeting_id}/transcript")
async def get_transcript(meeting_id: str) -> dict[str, Any]:
    """Get the live transcript for a meeting.

    Returns all transcript segments with speaker identification
    and timestamps.
    """
    manager = get_manager()
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {
        "meeting_id": meeting.id,
        "segment_count": len(meeting.transcript),
        "participants": meeting.participants,
        "segments": [
            {
                "speaker": seg.speaker,
                "text": seg.text,
                "timestamp": seg.timestamp,
                "timestamp_display": seg.timestamp_display,
            }
            for seg in meeting.transcript
        ],
    }


@router.post("/meetings/{meeting_id}/end")
async def end_meeting(meeting_id: str) -> dict[str, Any]:
    """End a meeting and generate the comprehensive summary.

    Stops the bot, flushes remaining transcript, runs AI summary
    generation, and returns the complete meeting summary.
    """
    manager = get_manager()
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == MeetingStatus.COMPLETED:
        return {
            "meeting_id": meeting.id,
            "status": "already_completed",
            "summary": meeting.summary,
        }

    summary = await manager.end_meeting(meeting_id)

    if summary is None:
        raise HTTPException(status_code=500, detail="Failed to generate summary")

    return {
        "meeting_id": summary.meeting_id,
        "status": "completed",
        "title": summary.title,
        "duration_minutes": summary.duration_minutes,
        "participants": summary.participants,
        "executive_summary": summary.executive_summary,
        "action_items": [item.model_dump() for item in summary.action_items],
        "decisions": [d.model_dump() for d in summary.decisions],
        "key_topics": summary.key_topics,
        "full_transcript": summary.full_transcript,
    }


@router.get("/meetings")
async def list_meetings() -> dict[str, Any]:
    """List all meetings (active and completed)."""
    manager = get_manager()
    meetings = manager.get_all_meetings()

    return {
        "count": len(meetings),
        "meetings": [
            {
                "id": m.id,
                "status": m.status.value,
                "platform": m.platform.value,
                "meeting_url": m.meeting_url,
                "participants": m.participants,
                "transcript_segments": len(m.transcript),
                "action_items_count": len(m.action_items),
                "started_at": m.started_at.isoformat() if m.started_at else None,
                "ended_at": m.ended_at.isoformat() if m.ended_at else None,
            }
            for m in meetings
        ],
    }


@router.post("/webhooks/recall/transcript/{meeting_id}")
async def recall_transcript_webhook(meeting_id: str, request: Request) -> dict:
    """Receive real-time transcript data from Recall.ai webhook.

    Recall.ai sends transcript segments as they are recognized.
    This endpoint receives them and feeds them into the processing pipeline.
    """
    manager = get_manager()
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    body = await request.json()
    await manager.receive_transcript_webhook(meeting_id, body)

    return {"status": "received"}


@router.post("/webhooks/recall/status/{meeting_id}")
async def recall_status_webhook(meeting_id: str, request: Request) -> dict:
    """Receive bot status updates from Recall.ai webhook.

    Handles events like: bot_joined, bot_left, meeting_ended, error.
    """
    manager = get_manager()
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    body = await request.json()
    event = body.get("event", "unknown")

    logger.info(
        "recall_status_webhook",
        meeting_id=meeting_id,
        event=event,
    )

    if event in ("bot_left", "meeting_ended"):
        if meeting.status == MeetingStatus.ACTIVE:
            await manager.end_meeting(meeting_id)

    elif event == "bot_joined":
        meeting.status = MeetingStatus.ACTIVE

    elif event == "error":
        meeting.status = MeetingStatus.FAILED
        logger.error("recall_bot_error", detail=body.get("data", {}))

    return {"status": "received"}
