"""Tests for the transcript handler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.models.meeting import (
    Meeting,
    MeetingPlatform,
    MeetingStatus,
    TranscriptSegment,
)
from app.services.ai_processor import AIProcessor
from app.services.transcript_handler import TranscriptHandler


@pytest.fixture
def mock_ai_processor():
    processor = MagicMock(spec=AIProcessor)
    processor.analyze_segments = AsyncMock(
        return_value={"insights": [], "action_items": [], "decisions": []}
    )
    processor.parse_insights = MagicMock(return_value=([], [], [], []))
    return processor


@pytest.fixture
def handler_meeting():
    return Meeting(
        meeting_url="https://zoom.us/j/123",
        platform=MeetingPlatform.ZOOM,
        status=MeetingStatus.ACTIVE,
    )


@pytest_asyncio.fixture
async def handler(handler_meeting, mock_ai_processor):
    h = TranscriptHandler(
        meeting=handler_meeting,
        ai_processor=mock_ai_processor,
        recall_client=None,
        buffer_seconds=1,
    )
    yield h
    if h._running:
        await h.stop()


@pytest.mark.asyncio
async def test_on_segment_adds_to_transcript(handler, handler_meeting):
    seg = TranscriptSegment(speaker="Alice", text="Hello", timestamp=0.0)
    await handler.on_segment(seg)
    assert len(handler_meeting.transcript) == 1
    assert handler_meeting.transcript[0].speaker == "Alice"


@pytest.mark.asyncio
async def test_on_segment_tracks_participants(handler, handler_meeting):
    seg1 = TranscriptSegment(speaker="Alice", text="Hello", timestamp=0.0)
    seg2 = TranscriptSegment(speaker="Bob", text="Hi", timestamp=5.0)
    seg3 = TranscriptSegment(speaker="Alice", text="How are you?", timestamp=10.0)

    await handler.on_segment(seg1)
    await handler.on_segment(seg2)
    await handler.on_segment(seg3)

    assert "Alice" in handler_meeting.participants
    assert "Bob" in handler_meeting.participants
    assert len(handler_meeting.participants) == 2  # No duplicates


@pytest.mark.asyncio
async def test_force_process(handler, handler_meeting, mock_ai_processor):
    seg = TranscriptSegment(speaker="Alice", text="Important point", timestamp=0.0)
    await handler.on_segment(seg)
    await handler.force_process()

    mock_ai_processor.analyze_segments.assert_called_once()


@pytest.mark.asyncio
async def test_on_segments_batch(handler, handler_meeting):
    segments = [
        TranscriptSegment(speaker="Alice", text="One", timestamp=0.0),
        TranscriptSegment(speaker="Bob", text="Two", timestamp=5.0),
        TranscriptSegment(speaker="Carol", text="Three", timestamp=10.0),
    ]
    await handler.on_segments_batch(segments)
    assert len(handler_meeting.transcript) == 3
    assert len(handler_meeting.participants) == 3


@pytest.mark.asyncio
async def test_start_stop(handler):
    await handler.start()
    assert handler._running is True
    await handler.stop()
    assert handler._running is False


@pytest.mark.asyncio
async def test_processing_loop_calls_ai(handler, handler_meeting, mock_ai_processor):
    """Start handler, add segment, wait for processing loop to trigger."""
    await handler.start()

    seg = TranscriptSegment(speaker="Alice", text="Test message", timestamp=0.0)
    await handler.on_segment(seg)

    # Wait for buffer_seconds (1s) + small margin
    await asyncio.sleep(1.5)

    await handler.stop()
    assert mock_ai_processor.analyze_segments.call_count >= 1
