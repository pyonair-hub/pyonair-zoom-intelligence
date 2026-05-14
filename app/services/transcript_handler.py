"""Real-time transcript handler.

Receives transcript segments (from Recall.ai webhook or WebSocket),
buffers them, and dispatches to the AI processor at configurable intervals.
Also handles posting chat messages back to the meeting.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.models.meeting import (
    ActionItem,
    ChatMessage,
    Decision,
    Meeting,
    MeetingInsight,
    MeetingStatus,
    TranscriptSegment,
)
from app.services.ai_processor import AIProcessor
from app.services.recall_client import RecallClient

logger = get_logger("transcript_handler")


class TranscriptHandler:
    """Manages the real-time transcript processing pipeline for a single meeting.

    Flow:
    1. Receives transcript segments via on_segment()
    2. Buffers segments until processing interval
    3. Sends buffered segments to AI processor for analysis
    4. Posts chat messages back to meeting via Recall.ai
    5. Stores insights, action items, decisions on the Meeting object
    """

    def __init__(
        self,
        meeting: Meeting,
        ai_processor: AIProcessor,
        recall_client: Optional[RecallClient] = None,
        buffer_seconds: int = 0,
        on_insight: Optional[Callable] = None,
        on_chat_message: Optional[Callable] = None,
    ):
        self.meeting = meeting
        self.ai_processor = ai_processor
        self.recall_client = recall_client
        self.buffer_seconds = buffer_seconds or settings.transcript_buffer_seconds
        self.on_insight = on_insight
        self.on_chat_message = on_chat_message

        self._segment_buffer: list[TranscriptSegment] = []
        self._processing_lock = asyncio.Lock()
        self._process_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_process_time = 0.0

    async def start(self) -> None:
        """Start the periodic processing loop."""
        self._running = True
        self._process_task = asyncio.create_task(self._processing_loop())
        logger.info("transcript_handler_started", meeting_id=self.meeting.id)

    async def stop(self) -> None:
        """Stop the processing loop and flush remaining segments."""
        self._running = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass

        # Flush remaining buffer
        if self._segment_buffer:
            await self._process_buffer()

        logger.info("transcript_handler_stopped", meeting_id=self.meeting.id)

    async def on_segment(self, segment: TranscriptSegment) -> None:
        """Receive a new transcript segment.

        Args:
            segment: The new transcript segment from Recall.ai.
        """
        self.meeting.transcript.append(segment)

        # Track participants
        if segment.speaker and segment.speaker not in self.meeting.participants:
            self.meeting.participants.append(segment.speaker)

        self._segment_buffer.append(segment)

    async def on_segments_batch(self, segments: list[TranscriptSegment]) -> None:
        """Receive a batch of transcript segments at once."""
        for segment in segments:
            await self.on_segment(segment)

    async def _processing_loop(self) -> None:
        """Periodic loop that processes buffered segments."""
        while self._running:
            try:
                await asyncio.sleep(self.buffer_seconds)
                if self._segment_buffer:
                    await self._process_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "processing_loop_error",
                    error=str(e),
                    meeting_id=self.meeting.id,
                )

    async def _process_buffer(self) -> None:
        """Process the current buffer of segments through the AI pipeline."""
        async with self._processing_lock:
            if not self._segment_buffer:
                return

            segments_to_process = self._segment_buffer.copy()
            self._segment_buffer.clear()

            # Use recent transcript as context (last 20 segments before the buffer)
            buffer_start_idx = max(
                0, len(self.meeting.transcript) - len(segments_to_process) - 20
            )
            buffer_end_idx = len(self.meeting.transcript) - len(segments_to_process)
            context_segments = self.meeting.transcript[buffer_start_idx:buffer_end_idx]

            current_time = (
                segments_to_process[-1].timestamp if segments_to_process else 0.0
            )

            logger.info(
                "processing_buffer",
                meeting_id=self.meeting.id,
                num_segments=len(segments_to_process),
                context_segments=len(context_segments),
            )

            # Run AI analysis
            raw_result = await self.ai_processor.analyze_segments(
                new_segments=segments_to_process,
                context_segments=context_segments,
                participants=self.meeting.participants,
            )

            # Parse results into typed objects
            insights, action_items, decisions, chat_messages = (
                self.ai_processor.parse_insights(raw_result, timestamp=current_time)
            )

            # Store on the meeting object
            self.meeting.insights.extend(insights)
            self.meeting.action_items.extend(action_items)
            self.meeting.decisions.extend(decisions)

            # Post chat messages to the meeting
            for msg in chat_messages:
                await self._post_chat_message(msg)

            # Fire callbacks
            for insight in insights:
                if self.on_insight:
                    try:
                        self.on_insight(insight)
                    except Exception:
                        pass

            self._last_process_time = time.time()

    async def _post_chat_message(self, message: ChatMessage) -> None:
        """Post a chat message to the meeting via Recall.ai."""
        if not self.recall_client or not self.meeting.bot_id:
            logger.info(
                "chat_message_skipped_no_bot",
                content=message.content[:100],
            )
            self.meeting.chat_messages_sent.append(message)
            if self.on_chat_message:
                self.on_chat_message(message)
            return

        try:
            await self.recall_client.send_chat_message(
                self.meeting.bot_id, message.content
            )
            self.meeting.chat_messages_sent.append(message)
            logger.info(
                "chat_message_sent",
                meeting_id=self.meeting.id,
                message_type=message.message_type,
            )
            if self.on_chat_message:
                self.on_chat_message(message)
        except Exception as e:
            logger.error(
                "chat_message_failed",
                error=str(e),
                meeting_id=self.meeting.id,
            )

    async def force_process(self) -> None:
        """Force immediate processing of the buffer (e.g., on meeting end)."""
        await self._process_buffer()
