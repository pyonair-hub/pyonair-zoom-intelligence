"""Structured logging configuration."""

from __future__ import annotations

import structlog


def setup_logging(log_level: str = "info") -> None:
    """Configure structlog for the application."""
    import logging

    level_map = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
    numeric_level = level_map.get(log_level.lower(), 20)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)
