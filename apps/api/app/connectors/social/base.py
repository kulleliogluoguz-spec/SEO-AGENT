"""
Social Channel Connector — Base Interface + Adapter Pattern
Every channel implements this interface. Mock implementations are provided;
real API adapters follow the same contract.
"""
from __future__ import annotations

import abc
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Shared Types ────────────────────────────────────────────────────────────

@dataclass
class PublishResult:
    success: bool
    external_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    raw_response: dict = field(default_factory=dict)


@dataclass
class MetricsResult:
    success: bool
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AuthStatus:
    connected: bool
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    scopes: list[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None


@dataclass
class RateLimitState:
    remaining: int = 999
    limit: int = 1000
    reset_at: Optional[datetime] = None
    window_seconds: int = 3600


# ─── Base Interface ──────────────────────────────────────────────────────────

class BaseSocialConnector(abc.ABC):
    """Abstract base for all social media channel connectors."""

    channel_name: str = "base"
    _rate_limit: RateLimitState

    def __init__(self, access_token: Optional[str] = None,
                 refresh_token: Optional[str] = None,
                 account_id: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.account_id = account_id
        self._rate_limit = RateLimitState()

    # ── Auth ──
    @abc.abstractmethod
    async def authenticate(self) -> AuthStatus:
        """Verify credentials and return account info."""
        ...

    @abc.abstractmethod
    async def refresh_auth(self) -> AuthStatus:
        """Refresh expired tokens."""
        ...

    # ── Publishing ──
    @abc.abstractmethod
    async def publish(self, content: dict) -> PublishResult:
        """
        Publish content to the channel.
        `content` follows channel-specific schema.
        """
        ...

    @abc.abstractmethod
    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        """Schedule content for future publishing."""
        ...

    @abc.abstractmethod
    async def delete(self, external_id: str) -> bool:
        """Delete a published post."""
        ...

    # ── Metrics ──
    @abc.abstractmethod
    async def get_metrics(self, external_id: str) -> MetricsResult:
        """Fetch performance metrics for a specific post."""
        ...

    @abc.abstractmethod
    async def get_account_metrics(self) -> MetricsResult:
        """Fetch account-level metrics."""
        ...

    # ── Rate Limiting ──
    def check_rate_limit(self) -> bool:
        """Return True if we can make another request."""
        if self._rate_limit.reset_at and datetime.utcnow() > self._rate_limit.reset_at:
            self._rate_limit.remaining = self._rate_limit.limit
        return self._rate_limit.remaining > 0

    def consume_rate_limit(self):
        self._rate_limit.remaining = max(0, self._rate_limit.remaining - 1)

    async def _rate_limited_call(self, coro_factory, *args, **kwargs):
        """
        Wrapper that enforces rate limits with retry.
        
        CRITICAL: accepts a callable that RETURNS a coroutine, not a coroutine
        itself. Python coroutines can only be awaited once — passing an already-
        created coroutine would crash on retry.
        
        Usage: await self._rate_limited_call(self._real_publish, content)
        NOT:   await self._rate_limited_call(self._real_publish(content))
        """
        last_error = None
        for attempt in range(3):
            if not self.check_rate_limit():
                wait = 60
                if self._rate_limit.reset_at:
                    wait = max(1, (self._rate_limit.reset_at - datetime.utcnow()).total_seconds())
                logger.warning(f"[{self.channel_name}] Rate limited. Waiting {wait:.0f}s (attempt {attempt+1}/3)")
                await asyncio.sleep(min(wait, 300))
                continue
            self.consume_rate_limit()
            try:
                return await coro_factory(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.error(f"[{self.channel_name}] Attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        return PublishResult(success=False, error=f"Failed after 3 attempts: {last_error}")


# ─── Connector Registry ─────────────────────────────────────────────────────

class ConnectorRegistry:
    """Central registry to get the right connector for a channel."""

    _connectors: dict[str, type[BaseSocialConnector]] = {}

    @classmethod
    def register(cls, channel: str, connector_cls: type[BaseSocialConnector]):
        cls._connectors[channel] = connector_cls

    @classmethod
    def get(cls, channel: str, **kwargs) -> BaseSocialConnector:
        if channel not in cls._connectors:
            raise ValueError(f"No connector registered for channel: {channel}")
        return cls._connectors[channel](**kwargs)

    @classmethod
    def available_channels(cls) -> list[str]:
        return list(cls._connectors.keys())
