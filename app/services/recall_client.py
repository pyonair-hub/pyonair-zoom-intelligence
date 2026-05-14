"""Recall.ai API client for bot management and meeting joining.

Recall.ai provides the bot infrastructure that joins meetings as a participant,
captures audio, and streams real-time transcription via WebSocket.

API docs: https://docs.recall.ai/
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.meeting import MeetingPlatform

logger = get_logger("recall_client")


class RecallAPIError(Exception):
    """Raised when a Recall.ai API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Recall API error {status_code}: {detail}")


class RecallClient:
    """Client for the Recall.ai REST API.

    Handles:
    - Creating bots that join meetings
    - Sending chat messages to meetings via the bot
    - Retrieving bot status and transcript data
    - Removing bots from meetings
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.api_key = api_key or settings.recall_api_key
        self.api_base = (api_base or settings.recall_api_base).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.request(method, path, json=json)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json()
            except Exception:
                pass
            raise RecallAPIError(response.status_code, str(detail))
        if response.status_code == 204:
            return {}
        return response.json()

    async def create_bot(
        self,
        meeting_url: str,
        bot_name: str = "Pyonair AI",
        platform: MeetingPlatform = MeetingPlatform.ZOOM,
    ) -> dict[str, Any]:
        """Create a bot and have it join a meeting.

        Args:
            meeting_url: The meeting URL (Zoom, Google Meet, or Teams).
            bot_name: Display name for the bot in the meeting.
            platform: Meeting platform type.

        Returns:
            Bot creation response including bot ID and status.
        """
        payload: dict[str, Any] = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "transcription_options": {
                "provider": "meeting_captions",
            },
            "real_time_transcription": {
                "destination_url": "",  # Set by caller with their webhook URL
                "partial_results": False,
            },
            "chat": {
                "on_bot_join": {
                    "send_to": "everyone",
                    "message": f"Hi everyone! I am {bot_name}, your AI meeting assistant. "
                    "I will be taking notes and can help with research during this call.",
                },
            },
        }

        logger.info(
            "creating_bot",
            meeting_url=meeting_url,
            bot_name=bot_name,
            platform=platform.value,
        )

        result = await self._request("POST", "/bot", json=payload)
        logger.info("bot_created", bot_id=result.get("id"))
        return result

    async def get_bot_status(self, bot_id: str) -> dict[str, Any]:
        """Get the current status of a bot.

        Args:
            bot_id: The bot's unique identifier.

        Returns:
            Bot status including meeting state, participants, etc.
        """
        return await self._request("GET", f"/bot/{bot_id}")

    async def send_chat_message(self, bot_id: str, message: str) -> dict[str, Any]:
        """Send a chat message to the meeting through the bot.

        Args:
            bot_id: The bot's unique identifier.
            message: Text message to send to the meeting chat.

        Returns:
            API response confirming message was sent.
        """
        logger.info(
            "sending_chat_message",
            bot_id=bot_id,
            message_length=len(message),
        )
        return await self._request(
            "POST",
            f"/bot/{bot_id}/send_chat_message",
            json={"message": message},
        )

    async def get_transcript(self, bot_id: str) -> list[dict[str, Any]]:
        """Get the full transcript for a bot's meeting.

        Args:
            bot_id: The bot's unique identifier.

        Returns:
            List of transcript segments with speaker info and timestamps.
        """
        result = await self._request("GET", f"/bot/{bot_id}/transcript")
        return result if isinstance(result, list) else result.get("results", [])

    async def remove_bot(self, bot_id: str) -> None:
        """Remove a bot from its current meeting.

        Args:
            bot_id: The bot's unique identifier.
        """
        logger.info("removing_bot", bot_id=bot_id)
        await self._request("POST", f"/bot/{bot_id}/leave")

    async def list_bots(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List all bots with pagination.

        Returns:
            Paginated list of bots.
        """
        return await self._request(
            "GET",
            f"/bot?limit={limit}&offset={offset}",
        )
