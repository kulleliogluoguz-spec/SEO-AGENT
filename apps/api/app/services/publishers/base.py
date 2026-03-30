"""
Base publisher interface — all channel publishers implement this contract.

PublisherService is the single abstraction used by:
  - publish_sweep_job (background task)
  - POST /api/v1/publishing/publish-now/{content_id}
  - POST /api/v1/publishing/validate-connection/{channel}

Design principles:
  - Every publish operation writes an AuditEvent (who, what, when, under which policy)
  - Credentials are loaded from credential_store at call time (never stored on instance beyond init)
  - All network calls use httpx.AsyncClient with reasonable timeouts
  - Rate limit responses (429) are surfaced as PublishResult.rate_limited=True, not raised
  - The caller (sweep job / endpoint) handles retry scheduling
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PublisherStatus(str, Enum):
    READY = "ready"                        # credentials valid, scopes ok
    NO_CREDENTIALS = "no_credentials"      # user has not connected this channel
    INVALID_CREDENTIALS = "invalid_credentials"   # token invalid/expired
    MISSING_SCOPES = "missing_scopes"      # token exists but lacks required scopes
    RATE_LIMITED = "rate_limited"          # channel is rate-limiting us now
    UNAVAILABLE = "unavailable"            # channel API is down or unreachable
    NOT_IMPLEMENTED = "not_implemented"    # publisher stub, not yet built


@dataclass
class PublishResult:
    success: bool
    post_id: Optional[str] = None           # platform-native post/tweet ID
    post_url: Optional[str] = None          # public URL of the published post
    error: Optional[str] = None
    rate_limited: bool = False
    retry_after_seconds: Optional[int] = None
    raw_response: Optional[dict] = field(default=None, repr=False)
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def ok(cls, post_id: str, post_url: Optional[str] = None, raw: Optional[dict] = None) -> "PublishResult":
        return cls(success=True, post_id=post_id, post_url=post_url, raw_response=raw)

    @classmethod
    def fail(cls, error: str, rate_limited: bool = False, retry_after: Optional[int] = None) -> "PublishResult":
        return cls(success=False, error=error, rate_limited=rate_limited, retry_after_seconds=retry_after)

    @classmethod
    def not_implemented(cls, channel: str) -> "PublishResult":
        return cls(
            success=False,
            error=f"Publisher for '{channel}' is not yet fully implemented. "
                  "Connect the account in Connections and ensure the required OAuth scopes are granted.",
        )


class PublisherService(ABC):
    """
    Abstract base class for all channel publishers.

    Concrete implementations:
      - XPublisher       (X / Twitter API v2)
      - InstagramPublisher (Instagram Graph API)
      - TikTokPublisher  (TikTok Content Posting API)
    """

    channel: str = ""  # override in subclass

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._credentials: Optional[dict] = None

    def _load_credentials(self) -> Optional[dict]:
        """Load and decode credentials from the credential store."""
        from app.core.store.credential_store import get_credential
        cred = get_credential(self.user_id, self.channel)
        if not cred:
            # Try aliases (e.g. "twitter" → "x")
            return None
        return cred

    @abstractmethod
    async def check_status(self) -> PublisherStatus:
        """Validate that credentials are present, valid, and have required scopes."""

    @abstractmethod
    async def publish_text_post(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
        schedule_at: Optional[str] = None,
    ) -> PublishResult:
        """Publish a text-only post. Returns PublishResult."""

    async def publish_media_post(
        self,
        text: str,
        media_urls: list[str],
        reply_to_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish a post with media attachments. Default: falls back to text-only."""
        logger.warning("[%s] media publishing not implemented, falling back to text-only", self.channel)
        return await self.publish_text_post(text, reply_to_id=reply_to_id)

    async def get_post_metrics(self, post_id: str) -> Optional[dict]:
        """Fetch engagement metrics for a published post. Returns None if not implemented."""
        return None

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post. Returns True on success."""
        return False

    def _audit(self, action: str, result: PublishResult, content_id: Optional[str] = None) -> None:
        """Write an audit event for this publish action."""
        try:
            from app.core.store.audit_store import write_audit_event
            write_audit_event(
                user_id=self.user_id,
                action=f"publish.{self.channel}.{action}",
                channel=self.channel,
                success=result.success,
                post_id=result.post_id,
                content_id=content_id,
                error=result.error,
            )
        except Exception as e:
            logger.debug("[audit] write failed: %s", e)
