"""Meeting lifecycle manager.

Orchestrates the full meeting flow:
1. Join meeting (create bot via Recall.ai)
2. Set up transcript handler
3. Monitor meeting status
4. Generate summary on meeting end
5. Deliver results
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.models.meeting import (
    JoinMeetingRequest,
    JoinMeetingResponse,
    Meeting,
    MeetingPlatform,
    MeetingStatus,
    MeetingSummary,
    TranscriptSegment,
)
from app.services.ai_processor import AIProcessor
from app.services.demo_provider import DemoTranscriptProvider
from app.services.recall_client import RecallClient
from app.services.transcript_handler import TranscriptHandler

logger = get_logger("meeting_manager")


def _detect_platform(url: str) -> MeetingPlatform:
    """Detect meeting platform from URL."""
    url_lower = url.lower()
    if "zoom.us" in url_lower or "zoomgov.com" in url_lower:
        return MeetingPlatform.ZOOM
    elif "meet.google.com" in url_lower:
        return MeetingPlatform.GOOGLE_MEET
    elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
        return MeetingPlatform.TEAMS
    return MeetingPlatform.ZOOM


class MeetingManager:
    """Manages all active meetings and their lifecycle.

    This is the central coordinator. The API layer talks to this;
    this talks to Recall.ai, AI processor, and transcript handlers.
    """

    def __init__(self):
        self.meetings: dict[str, Meeting] = {}
        self.handlers: dict[str, TranscriptHandler] = {}
        self._recall_client: Optional[RecallClient] = None
        self._ai_processor: Optional[AIProcessor] = None

    @property
    def recall_client(self) -> RecallClient:
        if self._recall_client is None:
            self._recall_client = RecallClient()
        return self._recall_client

    @property
    def ai_processor(self) -> AIProcessor:
        if self._ai_processor is None:
            self._ai_processor = AIProcessor()
        return self._ai_processor

    async def join_meeting(self, request: JoinMeetingRequest) -> JoinMeetingResponse:
        """Join a meeting and start processing.

        Args:
            request: The join meeting request with URL and options.

        Returns:
            Response with meeting ID and initial status.
        """
        platform = _detect_platform(request.meeting_url)
        bot_name = request.bot_name or settings.bot_display_name

        meeting = Meeting(
            meeting_url=request.meeting_url,
            platform=platform,
            bot_display_name=bot_name,
            status=MeetingStatus.JOINING,
        )

        self.meetings[meeting.id] = meeting

        if settings.demo_mode:
            return await self._join_demo(meeting, request)
        else:
            return await self._join_live(meeting, request)

    async def _join_live(
        self, meeting: Meeting, request: JoinMeetingRequest
    ) -> JoinMeetingResponse:
        """Join a real meeting via Recall.ai."""
        if not settings.has_recall_credentials:
            meeting.status = MeetingStatus.FAILED
            return JoinMeetingResponse(
                meeting_id=meeting.id,
                status=meeting.status,
                message="Recall.ai API key not configured. Set RECALL_API_KEY or enable DEMO_MODE.",
            )

        try:
            bot_response = await self.recall_client.create_bot(
                meeting_url=meeting.meeting_url,
                bot_name=meeting.bot_display_name,
                platform=meeting.platform,
            )

            meeting.bot_id = bot_response.get("id")
            meeting.status = MeetingStatus.JOINING
            meeting.started_at = datetime.utcnow()

            # Set up transcript handler
            handler = TranscriptHandler(
                meeting=meeting,
                ai_processor=self.ai_processor,
                recall_client=self.recall_client,
            )
            self.handlers[meeting.id] = handler
            await handler.start()

            logger.info(
                "meeting_joined_live",
                meeting_id=meeting.id,
                bot_id=meeting.bot_id,
            )

            return JoinMeetingResponse(
                meeting_id=meeting.id,
                status=meeting.status,
                bot_id=meeting.bot_id,
                message=f"Bot is joining the meeting as '{meeting.bot_display_name}'.",
            )

        except Exception as e:
            meeting.status = MeetingStatus.FAILED
            logger.error("join_meeting_failed", error=str(e))
            return JoinMeetingResponse(
                meeting_id=meeting.id,
                status=meeting.status,
                message=f"Failed to join meeting: {str(e)}",
            )

    async def _join_demo(
        self, meeting: Meeting, request: JoinMeetingRequest
    ) -> JoinMeetingResponse:
        """Join in demo mode with simulated transcript."""
        meeting.status = MeetingStatus.ACTIVE
        meeting.started_at = datetime.utcnow()
        meeting.bot_id = "demo-bot-001"

        handler = TranscriptHandler(
            meeting=meeting,
            ai_processor=self.ai_processor,
            recall_client=None,  # No real bot in demo mode
            buffer_seconds=5,  # Faster processing for demo
        )
        self.handlers[meeting.id] = handler
        await handler.start()

        # Start demo transcript feed in background
        demo = DemoTranscriptProvider()
        asyncio.create_task(
            self._feed_demo_transcript(meeting.id, demo)
        )

        logger.info("meeting_joined_demo", meeting_id=meeting.id)

        return JoinMeetingResponse(
            meeting_id=meeting.id,
            status=meeting.status,
            bot_id=meeting.bot_id,
            message="Demo mode: Simulated meeting started. Transcript will stream automatically.",
        )

    async def _feed_demo_transcript(
        self, meeting_id: str, demo: DemoTranscriptProvider
    ) -> None:
        """Feed demo transcript segments to the handler over time."""
        handler = self.handlers.get(meeting_id)
        if not handler:
            return

        segments = demo.get_demo_segments()
        for segment in segments:
            if meeting_id not in self.meetings:
                break
            meeting = self.meetings[meeting_id]
            if meeting.status not in (MeetingStatus.ACTIVE, MeetingStatus.JOINING):
                break

            await handler.on_segment(segment)
            # Simulate real-time pacing
            await asyncio.sleep(2.0)

        # Auto-end demo meeting after all segments
        if meeting_id in self.meetings:
            await self.end_meeting(meeting_id)

    async def end_meeting(self, meeting_id: str) -> Optional[MeetingSummary]:
        """End a meeting and generate the summary.

        Args:
            meeting_id: The meeting's unique identifier.

        Returns:
            The generated meeting summary, or None if meeting not found.
        """
        meeting = self.meetings.get(meeting_id)
        if not meeting:
            logger.warning("end_meeting_not_found", meeting_id=meeting_id)
            return None

        meeting.status = MeetingStatus.PROCESSING
        meeting.ended_at = datetime.utcnow()

        # Stop transcript handler (flushes remaining buffer)
        handler = self.handlers.get(meeting_id)
        if handler:
            await handler.force_process()
            await handler.stop()

        # Remove bot from meeting if live
        if not settings.demo_mode and meeting.bot_id:
            try:
                await self.recall_client.remove_bot(meeting.bot_id)
            except Exception as e:
                logger.warning("remove_bot_failed", error=str(e))

        # Generate comprehensive summary
        summary_text = await self.ai_processor.generate_summary(
            transcript=meeting.transcript,
            participants=meeting.participants,
            action_items=meeting.action_items,
            decisions=meeting.decisions,
            meeting_title=meeting.title,
            duration_minutes=meeting.duration_minutes,
        )

        meeting.summary = summary_text
        meeting.status = MeetingStatus.COMPLETED

        summary = MeetingSummary(
            meeting_id=meeting.id,
            title=meeting.title or "Meeting",
            duration_minutes=meeting.duration_minutes or 0.0,
            participant_count=len(meeting.participants),
            participants=meeting.participants,
            executive_summary=summary_text,
            key_topics=[t.topic for t in meeting.topics],
            action_items=meeting.action_items,
            decisions=meeting.decisions,
            full_transcript=meeting.transcript_text,
        )

        logger.info(
            "meeting_ended",
            meeting_id=meeting.id,
            duration_minutes=meeting.duration_minutes,
            total_segments=len(meeting.transcript),
            action_items=len(meeting.action_items),
            decisions=len(meeting.decisions),
        )

        return summary

    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get a meeting by ID."""
        return self.meetings.get(meeting_id)

    def get_all_meetings(self) -> list[Meeting]:
        """Get all meetings."""
        return list(self.meetings.values())

    async def receive_transcript_webhook(
        self, meeting_id: str, data: dict
    ) -> None:
        """Handle incoming transcript data from Recall.ai webhook.

        Args:
            meeting_id: Meeting to attribute the transcript to.
            data: Raw webhook payload from Recall.ai.
        """
        handler = self.handlers.get(meeting_id)
        if not handler:
            logger.warning(
                "transcript_webhook_no_handler", meeting_id=meeting_id
            )
            return

        # Parse Recall.ai transcript format
        segments = []
        for entry in data.get("data", []):
            words = entry.get("words", [])
            text = " ".join(w.get("text", "") for w in words)
            if not text.strip():
                continue

            segment = TranscriptSegment(
                speaker=entry.get("speaker", "Unknown"),
                text=text.strip(),
                timestamp=entry.get("start_time", 0.0),
                confidence=entry.get("confidence", 1.0),
            )
            segments.append(segment)

        if segments:
            await handler.on_segments_batch(segments)

    async def shutdown(self) -> None:
        """Clean shutdown of all meetings and connections."""
        for meeting_id in list(self.handlers.keys()):
            try:
                await self.handlers[meeting_id].stop()
            except Exception:
                pass

        if self._recall_client:
            await self._recall_client.close()

        logger.info("meeting_manager_shutdown")
