"""Tests for the API endpoints."""

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_root(client):
    """Health check / root endpoint returns service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Zoom Meeting Intelligence"
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_health(client):
    """Health endpoint returns configuration status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "demo_mode" in data


@pytest.mark.asyncio
async def test_list_meetings_empty(client):
    """List meetings returns empty when no meetings exist."""
    response = await client.get("/api/v1/meetings")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["meetings"] == []


@pytest.mark.asyncio
async def test_get_meeting_not_found(client):
    """Getting a non-existent meeting returns 404."""
    response = await client.get("/api/v1/meetings/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_end_meeting_not_found(client):
    """Ending a non-existent meeting returns 404."""
    response = await client.post("/api/v1/meetings/nonexistent-id/end")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transcript_not_found(client):
    """Getting transcript for a non-existent meeting returns 404."""
    response = await client.get("/api/v1/meetings/nonexistent-id/transcript")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_join_meeting_demo_mode(client, test_manager):
    """Join a meeting in demo mode starts a simulated session."""
    response = await client.post(
        "/api/v1/meetings/join",
        json={"meeting_url": "https://zoom.us/j/1234567890"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "demo" in data["message"].lower()
    assert data["meeting_id"] is not None

    # Verify meeting appears in list
    list_response = await client.get("/api/v1/meetings")
    list_data = list_response.json()
    assert list_data["count"] >= 1


@pytest.mark.asyncio
async def test_join_meeting_custom_bot_name(client, test_manager):
    """Join with a custom bot name passes it through."""
    response = await client.post(
        "/api/v1/meetings/join",
        json={
            "meeting_url": "https://meet.google.com/abc-defg-hij",
            "bot_name": "Acme AI Assistant",
        },
    )
    assert response.status_code == 200
    data = response.json()
    meeting_id = data["meeting_id"]

    # Check meeting details reflect custom name
    detail = await client.get(f"/api/v1/meetings/{meeting_id}")
    detail_data = detail.json()
    assert detail_data["bot_display_name"] == "Acme AI Assistant"


@pytest.mark.asyncio
async def test_webhook_transcript(client, test_manager):
    """Recall.ai transcript webhook feeds data into the meeting."""
    # First join a meeting
    join_resp = await client.post(
        "/api/v1/meetings/join",
        json={"meeting_url": "https://zoom.us/j/999"},
    )
    meeting_id = join_resp.json()["meeting_id"]

    # Send a transcript webhook
    webhook_data = {
        "data": [
            {
                "speaker": "TestUser",
                "words": [
                    {"text": "Hello"},
                    {"text": "world"},
                ],
                "start_time": 5.0,
                "confidence": 0.95,
            }
        ]
    }
    resp = await client.post(
        f"/api/v1/webhooks/recall/transcript/{meeting_id}",
        json=webhook_data,
    )
    assert resp.status_code == 200

    # Verify transcript was added
    import asyncio
    await asyncio.sleep(0.1)  # Let async processing happen

    transcript_resp = await client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    transcript_data = transcript_resp.json()
    # Should have at least the webhook segment (plus any demo segments)
    assert transcript_data["segment_count"] >= 1
