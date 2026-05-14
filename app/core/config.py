"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    # Recall.ai
    recall_api_key: str = ""
    recall_api_base: str = "https://us-west-2.recall.ai/api/v1"

    # Anthropic
    anthropic_api_key: str = ""

    # Application
    host: str = "0.0.0.0"
    port: int = 8900
    log_level: str = "info"
    demo_mode: bool = True

    # Bot
    bot_display_name: str = "Pyonair AI"

    # Email (post-meeting summaries)
    summary_email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # AI processing
    ai_model: str = "claude-sonnet-4-20250514"
    transcript_buffer_seconds: int = 30
    min_segments_for_insight: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def has_recall_credentials(self) -> bool:
        return bool(self.recall_api_key)

    @property
    def has_anthropic_credentials(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
