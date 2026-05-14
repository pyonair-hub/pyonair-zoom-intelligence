"""Demo transcript provider for testing without live Recall.ai credentials.

Generates a realistic simulated meeting transcript that exercises
all features: topic detection, action items, decisions, and research triggers.
"""

from __future__ import annotations

from app.models.meeting import TranscriptSegment


class DemoTranscriptProvider:
    """Provides a pre-scripted demo meeting transcript.

    The demo simulates a product strategy meeting between four participants
    discussing a new feature launch, complete with action items,
    decisions, and topics that would trigger research.
    """

    def get_demo_segments(self) -> list[TranscriptSegment]:
        """Return a list of demo transcript segments simulating a real meeting."""
        return [
            TranscriptSegment(
                speaker="Jord",
                text="Alright everyone, let's get started. Today we need to finalize the Q3 product roadmap and decide on the AI assistant feature.",
                timestamp=0.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="Sounds good. I've been looking at the competitive landscape. Intercom just launched their AI features last week and it's getting a lot of traction.",
                timestamp=15.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="Yeah, I saw that. Their pricing is aggressive too. We need to make sure our offering is differentiated, not just another chatbot.",
                timestamp=32.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Exactly. Our edge is the meeting intelligence piece. Nobody else is putting AI directly into client meetings. That is our differentiator.",
                timestamp=48.0,
            ),
            TranscriptSegment(
                speaker="Mike",
                text="From an engineering perspective, the Recall.ai integration is solid. We can have the MVP ready in two weeks if we scope it to Zoom only first.",
                timestamp=65.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="I think we should include Google Meet from day one. Half our clients use Meet, not Zoom. Recall.ai supports both.",
                timestamp=82.0,
            ),
            TranscriptSegment(
                speaker="Mike",
                text="Fair point. Recall handles both the same way under the hood, so it's not much extra work. Let me update the estimate.",
                timestamp=95.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Good. Let's make a decision here. We launch with Zoom and Google Meet support. Teams can come in phase two. Everyone agree?",
                timestamp=110.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="Agreed.",
                timestamp=120.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="Agreed. Makes sense to focus.",
                timestamp=123.0,
            ),
            TranscriptSegment(
                speaker="Mike",
                text="Works for me. I'll scope Zoom plus Meet for the initial build.",
                timestamp=128.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="OK, next topic. Pricing. Sarah, what are you thinking for the meeting AI add-on?",
                timestamp=140.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="I recommend bundling it into existing tiers rather than charging separately. It massively increases perceived value and stickiness.",
                timestamp=155.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="Our cost per meeting hour is about a dollar. Even the Studio tier with 30 hours included only costs us thirty dollars against a seven hundred dollar subscription. The margin math is incredible.",
                timestamp=172.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="That's compelling. What about the Starter tier though? We don't want to eat too much margin on the lower plans.",
                timestamp=190.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="Starter gets five hours per month. That's five dollars cost on a two hundred dollar plan. Two and a half percent. Even if they go over, it's negligible.",
                timestamp=205.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="I like the bundle approach. It makes the pitch so much stronger. Your AI team is not just working behind the scenes, they are in every meeting with you.",
                timestamp=222.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Decision made. We bundle meeting AI into all tiers. Starter gets five hours, Team gets fifteen, Studio gets thirty, Enterprise is unlimited.",
                timestamp=240.0,
            ),
            TranscriptSegment(
                speaker="Mike",
                text="Noted. I have a question about the Celestica integration. Are we still targeting their API v2 or waiting for v3?",
                timestamp=258.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="We should check with John at Celestica. He mentioned v3 is coming but didn't give a timeline. Can someone follow up?",
                timestamp=275.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Mike, can you email John at Celestica this week to get the v3 timeline? We need to know before we commit to the integration approach.",
                timestamp=290.0,
            ),
            TranscriptSegment(
                speaker="Mike",
                text="Will do. I'll reach out by Wednesday.",
                timestamp=302.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Sarah, I need the updated pricing page mockups by Friday. Include the meeting AI feature in the tier comparison.",
                timestamp=315.0,
            ),
            TranscriptSegment(
                speaker="Sarah",
                text="Got it. I'll have the mockups ready by end of day Friday.",
                timestamp=328.0,
            ),
            TranscriptSegment(
                speaker="Jord",
                text="Great meeting everyone. To recap: we are launching with Zoom plus Meet, bundling into tiers, and Mike is checking with Celestica on their API timeline. Let's reconvene next Tuesday.",
                timestamp=342.0,
            ),
            TranscriptSegment(
                speaker="Ronen",
                text="Perfect. Talk to you all Tuesday.",
                timestamp=360.0,
            ),
        ]
