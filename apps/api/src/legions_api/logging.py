"""Logging configuration for Legions backend."""

from __future__ import annotations

import os
import sys

from loguru import logger


def configure_logging() -> None:
    """Configure Loguru sinks and formatting.

    Environment variables:
    - LOG_LEVEL: log level, defaults to INFO
    - LOG_JSON: when set to 1/true, enables JSON serialized logs
    """

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_json = os.getenv("LOG_JSON", "false").lower() in {"1", "true", "yes"}

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        backtrace=False,
        diagnose=False,
        enqueue=True,
        serialize=log_json,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
    )
