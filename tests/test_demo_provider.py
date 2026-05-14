"""Tests for the demo transcript provider."""

from app.services.demo_provider import DemoTranscriptProvider


class TestDemoTranscriptProvider:
    def test_segments_not_empty(self):
        provider = DemoTranscriptProvider()
        segments = provider.get_demo_segments()
        assert len(segments) > 0

    def test_segments_have_speakers(self, demo_segments):
        for seg in demo_segments:
            assert seg.speaker, f"Segment at {seg.timestamp} has no speaker"
            assert seg.text, f"Segment at {seg.timestamp} has no text"

    def test_segments_ordered_by_timestamp(self, demo_segments):
        timestamps = [seg.timestamp for seg in demo_segments]
        assert timestamps == sorted(timestamps), "Segments should be in chronological order"

    def test_multiple_speakers(self, demo_segments):
        speakers = set(seg.speaker for seg in demo_segments)
        assert len(speakers) >= 3, f"Expected at least 3 speakers, got {speakers}"

    def test_contains_action_items(self, demo_segments):
        """The demo transcript should contain recognizable action items."""
        full_text = " ".join(seg.text for seg in demo_segments)
        # These phrases indicate action items exist in the demo
        assert "email" in full_text.lower() or "by" in full_text.lower()
        assert "friday" in full_text.lower() or "wednesday" in full_text.lower()

    def test_contains_decisions(self, demo_segments):
        """The demo transcript should contain recognizable decisions."""
        full_text = " ".join(seg.text for seg in demo_segments)
        assert "decision" in full_text.lower() or "agreed" in full_text.lower()
