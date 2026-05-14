"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force demo mode and provide dummy keys for tests
os.environ["DEMO_MODE"] = "true"
os.environ["RECALL_API_KEY"] = "test-recall-key"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

from app.main import app  # noqa: E402
from app.api.routes import set_manager  # noqa: E402
from app.services.meeting_manager import MeetingManager  # noqa: E402
from app.services.ai_processor import AIProcessor  # noqa: E402
from app.services.demo_provider import DemoTranscriptProvider  # noqa: E402
from app.models.meeting import (  # noqa: E402
    Meeting,
    MeetingPlatform,
    MeetingStatus,
    TranscriptSegment,
)


@pytest.fixture
def demo_segments():
    """Get demo transcript segments."""
    provider = DemoTranscriptProvider()
    return provider.get_demo_segments()


@pytest.fixture
def sample_meeting():
    """Create a sample meeting for testing."""
    return Meeting(
        meeting_url="https://zoom.us/j/1234567890",
        platform=MeetingPlatform.ZOOM,
        status=MeetingStatus.ACTIVE,
        bot_display_name="Test AI",
        participants=["Jord", "Ronen", "Sarah"],
    )


@pytest.fixture
def sample_segments():
    """Create a small set of transcript segments for testing."""
    return [
        TranscriptSegment(
            speaker="Jord",
            text="Let's discuss the timeline for the new feature launch.",
            timestamp=0.0,
        ),
        TranscriptSegment(
            speaker="Ronen",
            text="I think we can have the MVP ready by end of next week if we focus on the core functionality.",
            timestamp=12.0,
        ),
        TranscriptSegment(
            speaker="Jord",
            text="OK, Ronen will own the MVP delivery. Sarah, can you handle the client communication?",
            timestamp=28.0,
        ),
        TranscriptSegment(
            speaker="Sarah",
            text="Absolutely. I will draft the announcement email by Thursday.",
            timestamp=40.0,
        ),
    ]


@pytest_asyncio.fixture
async def test_manager():
    """Create a MeetingManager for testing."""
    manager = MeetingManager()
    set_manager(manager)
    yield manager
    await manager.shutdown()


@pytest_asyncio.fixture
async def client(test_manager):
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
