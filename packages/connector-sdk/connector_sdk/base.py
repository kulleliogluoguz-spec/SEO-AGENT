"""
BaseConnector and supporting types for the Connector SDK.

Every connector must:
1. Inherit from BaseConnector
2. Declare source_type (unique string identifier)
3. Declare compliance_mode (official_api | public_web | user_upload)
4. Implement validate_config, test_connection, and fetch

See docs/connectors/connector-sdk.md for the full specification.
"""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, ClassVar, Optional


class ComplianceMode(str, Enum):
    OFFICIAL_API = "official_api"
    PUBLIC_WEB = "public_web"
    USER_UPLOAD = "user_upload"


@dataclass
class ConnectorConfig:
    """Configuration for a single connector instance in a workspace."""
    workspace_id: str
    source_type: str
    display_name: str
    params: dict[str, Any] = field(default_factory=dict)
    credentials: dict[str, Any] = field(default_factory=dict)  # Encrypted at rest
    enabled: bool = True
    fetch_interval_minutes: int = 60
    max_documents_per_run: int = 500
    last_fetch_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawDocument:
    """
    Normalized raw document yielded by a connector.

    All connectors must produce RawDocument objects. The normalization
    pipeline then processes these into source_documents and computes embeddings.
    """
    id: str                             # Stable UUID (use make_doc_id)
    source_type: str                    # Connector type e.g. "rss", "reddit"
    source_url: str                     # Canonical URL
    content_hash: str                   # SHA-256 of raw_text (for dedup)
    raw_text: str                       # Full text content
    title: str = ""
    author: str = ""
    published_at: Optional[datetime] = None
    language: str = "en"
    compliance_mode: str = ""           # Inherited from connector
    metadata: dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ConnectionTestResult:
    success: bool
    message: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitPolicy:
    requests_per_second: float = 1.0    # Default: 1 req/sec
    requests_per_minute: int = 60
    requests_per_day: int = 10000
    burst_limit: int = 5
    retry_after_seconds: int = 60       # How long to wait after rate limit hit


@dataclass
class HealthStatus:
    healthy: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    Subclasses must define class variables:
        source_type: str        — unique identifier, e.g. "rss"
        compliance_mode: ComplianceMode
        display_name: str       — human-readable name
        description: str        — short description for UI

    Subclasses must implement:
        validate_config()
        test_connection()
        fetch()
    """

    source_type: ClassVar[str]
    compliance_mode: ClassVar[ComplianceMode]
    display_name: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    async def validate_config(self, config: ConnectorConfig) -> ValidationResult:
        """Validate that the config is complete and valid before connecting."""

    @abstractmethod
    async def test_connection(self, config: ConnectorConfig) -> ConnectionTestResult:
        """Attempt a live connection to verify the source is reachable and credentials work."""

    @abstractmethod
    async def fetch(
        self,
        config: ConnectorConfig,
        since: Optional[datetime] = None,
    ) -> AsyncIterator[RawDocument]:
        """
        Yield RawDocument objects from the source.

        Args:
            config: Connector configuration
            since: Only fetch documents newer than this timestamp (incremental fetch)

        Yields:
            RawDocument objects ready for normalization
        """

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        """Return the rate limiting policy. Override in subclasses."""
        return RateLimitPolicy()

    async def health_check(self) -> HealthStatus:
        """Quick health check (no credentials needed)."""
        return HealthStatus(healthy=True)

    def get_compliance_notes(self) -> str:
        """Return human-readable compliance notes for this connector."""
        notes = {
            ComplianceMode.OFFICIAL_API: (
                "This connector uses an official API. Valid credentials required. "
                "Respects API rate limits and Terms of Service."
            ),
            ComplianceMode.PUBLIC_WEB: (
                "This connector accesses publicly available web content. "
                "Respects robots.txt. Rate limited. No authentication bypass."
            ),
            ComplianceMode.USER_UPLOAD: (
                "This connector processes user-provided data. No external requests."
            ),
        }
        return notes.get(self.compliance_mode, "")

    def get_config_schema(self) -> dict[str, Any]:
        """Return JSON Schema for the connector's config parameters. Override in subclasses."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }


def make_doc_id(source_type: str, source_url: str) -> str:
    """
    Generate a stable, deterministic document ID.
    Identical source_type + source_url always produce the same ID.
    This enables idempotent upserts.
    """
    key = f"{source_type}:{source_url}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def make_content_hash(text: str) -> str:
    """SHA-256 hash of text content, used for deduplication."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
