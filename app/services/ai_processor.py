"""AI processing pipeline for meeting transcripts.

Takes buffered transcript segments and produces real-time insights,
action items, decisions, topic detection, and chat messages.
Uses Claude API for all analysis.
"""

from __future__ import annotations

import json
from typing import Optional

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.core.logging import get_logger
from app.models.meeting import (
    ActionItem,
    ChatMessage,
    Decision,
    MeetingInsight,
    MeetingSummary,
    TranscriptSegment,
)

logger = get_logger("ai_processor")


SYSTEM_PROMPT_REALTIME = """You are Pyonair AI, an intelligent meeting assistant participating in a live meeting. You analyze transcript segments in real time and produce actionable insights.

Your job is to:
1. Detect topic shifts and new subjects being discussed
2. Identify action items as they are assigned
3. Spot decisions being made
4. Find moments where research or context would help the team
5. Generate concise, helpful chat messages when you have something valuable to add

Rules:
- Be concise. Chat messages should be 1-3 sentences max.
- Only suggest posting to chat when you have genuinely useful info.
- Track who says what -- attribute action items and decisions to speakers.
- Do not be annoying. Quality over quantity for chat contributions.
- If someone mentions a company, person, or concept that might need context, flag it.

Respond ONLY with valid JSON matching this schema:
{
  "insights": [
    {
      "insight_type": "topic_shift | action_item | decision | research_finding | key_point",
      "content": "description of the insight",
      "confidence": 0.0-1.0,
      "should_post_to_chat": true/false,
      "chat_message": "message to post (only if should_post_to_chat is true)"
    }
  ],
  "action_items": [
    {
      "description": "what needs to be done",
      "assignee": "person name or null",
      "source_text": "exact quote from transcript"
    }
  ],
  "decisions": [
    {
      "description": "what was decided",
      "context": "surrounding context",
      "participants_involved": ["name1", "name2"]
    }
  ]
}

If nothing noteworthy happened in this segment, return: {"insights": [], "action_items": [], "decisions": []}"""


SYSTEM_PROMPT_SUMMARY = """You are Pyonair AI, generating a comprehensive post-meeting summary.

Given a full meeting transcript, produce a structured summary. Be thorough but concise. Use the actual participants' names. Group action items by assignee. List all decisions with context.

Your summary should be formatted as clean, readable text (not markdown) that could be pasted into an email. Use clear section headers with line breaks."""


class AIProcessor:
    """Processes meeting transcript segments using Claude API.

    Handles:
    - Real-time transcript analysis (buffered segments -> insights)
    - Post-meeting summary generation
    - Action item and decision extraction
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.ai_model
        self._client: Optional[AsyncAnthropic] = None
        self._conversation_context: list[dict] = []
        self._max_context_segments = 50

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _format_segments(self, segments: list[TranscriptSegment]) -> str:
        """Format transcript segments into a readable string for the LLM."""
        lines = []
        for seg in segments:
            lines.append(f"[{seg.timestamp_display}] {seg.speaker}: {seg.text}")
        return "\n".join(lines)

    async def analyze_segments(
        self,
        new_segments: list[TranscriptSegment],
        context_segments: list[TranscriptSegment],
        participants: list[str],
    ) -> dict:
        """Analyze new transcript segments with conversation context.

        Args:
            new_segments: The newly received transcript segments to analyze.
            context_segments: Recent prior segments for context.
            participants: List of known participant names.

        Returns:
            Dict containing insights, action_items, and decisions.
        """
        if not new_segments:
            return {"insights": [], "action_items": [], "decisions": []}

        context_text = self._format_segments(context_segments[-self._max_context_segments:])
        new_text = self._format_segments(new_segments)

        user_message = (
            f"Meeting participants: {', '.join(participants) if participants else 'Unknown'}\n\n"
        )
        if context_text:
            user_message += f"Previous context:\n{context_text}\n\n"
        user_message += f"New transcript to analyze:\n{new_text}"

        client = self._get_client()

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT_REALTIME,
                messages=[{"role": "user", "content": user_message}],
            )

            result_text = response.content[0].text.strip()

            # Handle potential markdown code fences in response
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                if result_text.endswith("```"):
                    result_text = result_text[:-3].strip()

            result = json.loads(result_text)
            logger.info(
                "segments_analyzed",
                num_new=len(new_segments),
                insights=len(result.get("insights", [])),
                action_items=len(result.get("action_items", [])),
                decisions=len(result.get("decisions", [])),
            )
            return result

        except json.JSONDecodeError as e:
            logger.error("ai_response_parse_error", error=str(e))
            return {"insights": [], "action_items": [], "decisions": []}
        except Exception as e:
            logger.error("ai_processing_error", error=str(e))
            return {"insights": [], "action_items": [], "decisions": []}

    async def generate_summary(
        self,
        transcript: list[TranscriptSegment],
        participants: list[str],
        action_items: list[ActionItem],
        decisions: list[Decision],
        meeting_title: Optional[str] = None,
        duration_minutes: Optional[float] = None,
    ) -> str:
        """Generate a comprehensive post-meeting summary.

        Args:
            transcript: Full meeting transcript.
            participants: All meeting participants.
            action_items: Action items extracted during the meeting.
            decisions: Decisions extracted during the meeting.
            meeting_title: Optional meeting title.
            duration_minutes: Optional meeting duration.

        Returns:
            Formatted meeting summary text.
        """
        transcript_text = self._format_segments(transcript)

        existing_items = "\n".join(
            f"- {item.description} (assigned to: {item.assignee or 'unassigned'})"
            for item in action_items
        )
        existing_decisions = "\n".join(
            f"- {d.description}" for d in decisions
        )

        user_message = f"""Meeting: {meeting_title or 'Untitled Meeting'}
Duration: {f'{duration_minutes:.0f} minutes' if duration_minutes else 'Unknown'}
Participants: {', '.join(participants) if participants else 'Unknown'}

Action items identified during the call:
{existing_items or '(none detected yet)'}

Decisions identified during the call:
{existing_decisions or '(none detected yet)'}

Full transcript:
{transcript_text}

Generate a comprehensive meeting summary. Include:
1. Executive Summary (3-5 sentences covering the main points)
2. Key Topics Discussed (bulleted list)
3. Action Items (with assignees, include any we may have missed)
4. Decisions Made (with context)
5. Follow-Up Items (things that need attention but are not formal action items)
6. Notable Quotes or Key Statements (if any stand out)"""

        client = self._get_client()

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT_SUMMARY,
                messages=[{"role": "user", "content": user_message}],
            )

            summary = response.content[0].text.strip()
            logger.info(
                "summary_generated",
                transcript_segments=len(transcript),
                summary_length=len(summary),
            )
            return summary

        except Exception as e:
            logger.error("summary_generation_error", error=str(e))
            return f"Error generating summary: {str(e)}"

    def parse_insights(
        self, raw: dict, timestamp: float = 0.0
    ) -> tuple[list[MeetingInsight], list[ActionItem], list[Decision], list[ChatMessage]]:
        """Parse raw AI analysis output into typed model objects.

        Args:
            raw: The raw dict from analyze_segments().
            timestamp: Current timestamp in the meeting.

        Returns:
            Tuple of (insights, action_items, decisions, chat_messages).
        """
        insights = []
        for item in raw.get("insights", []):
            insight = MeetingInsight(
                insight_type=item.get("insight_type", "key_point"),
                content=item.get("content", ""),
                confidence=item.get("confidence", 0.8),
                should_post_to_chat=item.get("should_post_to_chat", False),
                chat_message=item.get("chat_message"),
                timestamp=timestamp,
            )
            insights.append(insight)

        action_items = []
        for item in raw.get("action_items", []):
            action = ActionItem(
                description=item.get("description", ""),
                assignee=item.get("assignee"),
                source_text=item.get("source_text", ""),
                timestamp=timestamp,
            )
            action_items.append(action)

        decisions = []
        for item in raw.get("decisions", []):
            decision = Decision(
                description=item.get("description", ""),
                context=item.get("context", ""),
                participants_involved=item.get("participants_involved", []),
                timestamp=timestamp,
            )
            decisions.append(decision)

        chat_messages = []
        for insight in insights:
            if insight.should_post_to_chat and insight.chat_message:
                chat_messages.append(
                    ChatMessage(
                        content=insight.chat_message,
                        message_type=insight.insight_type,
                        timestamp=timestamp,
                    )
                )

        return insights, action_items, decisions, chat_messages
