"""Tests for data models."""

from app.models.meeting import (
    ActionItem,
    ChatMessage,
    Decision,
    JoinMeetingRequest,
    Meeting,
    MeetingInsight,
    MeetingPlatform,
    MeetingStatus,
    MeetingSummary,
    TranscriptSegment,
)


class TestTranscriptSegment:
    def test_timestamp_display(self):
        seg = TranscriptSegment(speaker="Alice", text="Hello", timestamp=125.5)
        assert seg.timestamp_display == "02:05"

    def test_timestamp_display_zero(self):
        seg = TranscriptSegment(speaker="Alice", text="Start", timestamp=0.0)
        assert seg.timestamp_display == "00:00"

    def test_default_confidence(self):
        seg = TranscriptSegment(speaker="Alice", text="Test", timestamp=10.0)
        assert seg.confidence == 1.0


class TestMeeting:
    def test_create_meeting(self):
        meeting = Meeting(meeting_url="https://zoom.us/j/123")
        assert meeting.status == MeetingStatus.PENDING
        assert meeting.platform == MeetingPlatform.ZOOM
        assert meeting.id is not None
        assert len(meeting.transcript) == 0
        assert len(meeting.action_items) == 0

    def test_transcript_text(self, sample_segments):
        meeting = Meeting(
            meeting_url="https://zoom.us/j/123",
            transcript=sample_segments,
        )
        text = meeting.transcript_text
        assert "[00:00] Jord:" in text
        assert "[00:12] Ronen:" in text
        assert "timeline" in text

    def test_participants_tracking(self):
        meeting = Meeting(
            meeting_url="https://zoom.us/j/123",
            participants=["Jord", "Ronen"],
        )
        assert len(meeting.participants) == 2

    def test_duration_none_without_times(self):
        meeting = Meeting(meeting_url="https://zoom.us/j/123")
        assert meeting.duration_minutes is None


class TestActionItem:
    def test_create_action_item(self):
        item = ActionItem(
            description="Send the report",
            assignee="Ronen",
            source_text="Ronen will send the report",
        )
        assert item.id is not None
        assert item.assignee == "Ronen"
        assert item.deadline is None


class TestDecision:
    def test_create_decision(self):
        decision = Decision(
            description="Launch with Zoom and Meet",
            context="Team agreed to support both platforms from day one",
            participants_involved=["Jord", "Ronen", "Mike"],
        )
        assert len(decision.participants_involved) == 3


class TestJoinMeetingRequest:
    def test_defaults(self):
        req = JoinMeetingRequest(meeting_url="https://zoom.us/j/123")
        assert req.auto_summary is True
        assert req.real_time_chat is True
        assert req.bot_name is None

    def test_custom_bot_name(self):
        req = JoinMeetingRequest(
            meeting_url="https://zoom.us/j/123",
            bot_name="Acme AI",
        )
        assert req.bot_name == "Acme AI"


class TestMeetingInsight:
    def test_create_insight(self):
        insight = MeetingInsight(
            insight_type="action_item",
            content="Ronen to send report by Friday",
            should_post_to_chat=True,
            chat_message="Action item noted: Ronen to send report by Friday",
        )
        assert insight.confidence == 0.8
        assert insight.should_post_to_chat is True
