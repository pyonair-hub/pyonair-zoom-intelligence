"""Tests for the AI processor service."""

import pytest

from app.models.meeting import (
    ActionItem,
    Decision,
    MeetingInsight,
    TranscriptSegment,
)
from app.services.ai_processor import AIProcessor


class TestAIProcessorParsing:
    """Test the parse_insights method (no API calls needed)."""

    def setup_method(self):
        self.processor = AIProcessor(api_key="test-key")

    def test_parse_empty_response(self):
        raw = {"insights": [], "action_items": [], "decisions": []}
        insights, actions, decisions, chats = self.processor.parse_insights(raw)
        assert len(insights) == 0
        assert len(actions) == 0
        assert len(decisions) == 0
        assert len(chats) == 0

    def test_parse_insights(self):
        raw = {
            "insights": [
                {
                    "insight_type": "topic_shift",
                    "content": "Discussion shifted to pricing",
                    "confidence": 0.9,
                    "should_post_to_chat": False,
                }
            ],
            "action_items": [],
            "decisions": [],
        }
        insights, actions, decisions, chats = self.processor.parse_insights(raw)
        assert len(insights) == 1
        assert insights[0].insight_type == "topic_shift"
        assert insights[0].confidence == 0.9
        assert len(chats) == 0

    def test_parse_action_items(self):
        raw = {
            "insights": [],
            "action_items": [
                {
                    "description": "Send the report by Friday",
                    "assignee": "Ronen",
                    "source_text": "Ronen will send the report by Friday",
                }
            ],
            "decisions": [],
        }
        insights, actions, decisions, chats = self.processor.parse_insights(raw, timestamp=100.0)
        assert len(actions) == 1
        assert actions[0].assignee == "Ronen"
        assert actions[0].timestamp == 100.0

    def test_parse_decisions(self):
        raw = {
            "insights": [],
            "action_items": [],
            "decisions": [
                {
                    "description": "Launch with Zoom and Meet",
                    "context": "Team voted unanimously",
                    "participants_involved": ["Jord", "Ronen", "Mike"],
                }
            ],
        }
        insights, actions, decisions, chats = self.processor.parse_insights(raw)
        assert len(decisions) == 1
        assert "Zoom" in decisions[0].description
        assert len(decisions[0].participants_involved) == 3

    def test_parse_chat_messages_from_insights(self):
        raw = {
            "insights": [
                {
                    "insight_type": "research_finding",
                    "content": "Found relevant info about Intercom",
                    "confidence": 0.85,
                    "should_post_to_chat": True,
                    "chat_message": "FYI: Intercom launched their AI features last week with aggressive pricing.",
                }
            ],
            "action_items": [],
            "decisions": [],
        }
        insights, actions, decisions, chats = self.processor.parse_insights(raw)
        assert len(chats) == 1
        assert "Intercom" in chats[0].content
        assert chats[0].message_type == "research_finding"

    def test_parse_no_chat_when_not_flagged(self):
        raw = {
            "insights": [
                {
                    "insight_type": "key_point",
                    "content": "Important but not chat-worthy",
                    "confidence": 0.7,
                    "should_post_to_chat": False,
                }
            ],
            "action_items": [],
            "decisions": [],
        }
        _, _, _, chats = self.processor.parse_insights(raw)
        assert len(chats) == 0

    def test_format_segments(self):
        segments = [
            TranscriptSegment(speaker="Alice", text="Hello everyone", timestamp=0.0),
            TranscriptSegment(speaker="Bob", text="Hi Alice", timestamp=5.0),
        ]
        result = self.processor._format_segments(segments)
        assert "[00:00] Alice: Hello everyone" in result
        assert "[00:05] Bob: Hi Alice" in result

    def test_parse_handles_missing_fields(self):
        """Gracefully handle partial data from the AI."""
        raw = {
            "insights": [{"insight_type": "key_point"}],
            "action_items": [{"description": "Do something"}],
            "decisions": [{"description": "Decided something"}],
        }
        insights, actions, decisions, chats = self.processor.parse_insights(raw)
        assert len(insights) == 1
        assert insights[0].content == ""
        assert len(actions) == 1
        assert actions[0].assignee is None
        assert len(decisions) == 1
