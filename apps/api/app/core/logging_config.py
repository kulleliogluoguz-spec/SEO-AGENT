"""
Structured logging + Sentry initialization.

Loguru handles console + file output with daily rotation. Sentry is
initialized only if `SENTRY_DSN` is set so dev environments without a
DSN incur zero overhead.
"""

from __future__ import annotations

import logging
import os
import sys

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
LOG_FILE = "/tmp/ai-growth-os.log"


def setup_logging() -> None:
    """Configure loguru console + file output and Sentry (if DSN is set)."""
    try:
        from loguru import logger
    except ImportError:
        logging.warning("loguru not installed; falling back to stdlib logging")
        return

    logger.remove()

    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
        ),
        level=os.getenv("LOG_LEVEL", "INFO"),
        colorize=True,
    )

    try:
        logger.add(
            LOG_FILE,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} — {message}",
            rotation="1 day",
            retention="7 days",
            level="DEBUG",
        )
    except Exception as e:
        logger.warning("Failed to attach file sink at {}: {}", LOG_FILE, e)

    if SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=SENTRY_DSN,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=0.1,
                environment=os.getenv("ENVIRONMENT", "development"),
                send_default_pii=False,
            )
            logger.info("Sentry initialized")
        except Exception as e:
            logger.warning("Sentry init failed: {}", e)
