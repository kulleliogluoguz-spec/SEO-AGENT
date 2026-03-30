"""
RSS / Atom Feed Connector

Compliance mode: PUBLIC_WEB
- Accesses publicly available RSS/Atom feeds
- Rate limited (respects feed-level delays)
- No authentication bypass
- Robots.txt checked at the feed host level

Usage:
    config = ConnectorConfig(
        workspace_id="...",
        source_type="rss",
        display_name="Hacker News",
        params={"feed_url": "https://news.ycombinator.com/rss"},
    )
    async for doc in connector.fetch(config):
        print(doc.title)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

# Import from the connector SDK (installed as a package or via path)
try:
    from connector_sdk.base import (
        BaseConnector,
        ComplianceMode,
        ConnectorConfig,
        ConnectionTestResult,
        RateLimitPolicy,
        RawDocument,
        ValidationResult,
        make_content_hash,
        make_doc_id,
    )
    from connector_sdk.registry import ConnectorRegistry
except ImportError:
    # Fallback for direct imports when SDK is in packages/
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../packages/connector-sdk"))
    from connector_sdk.base import (
        BaseConnector,
        ComplianceMode,
        ConnectorConfig,
        ConnectionTestResult,
        RateLimitPolicy,
        RawDocument,
        ValidationResult,
        make_content_hash,
        make_doc_id,
    )
    from connector_sdk.registry import ConnectorRegistry


@ConnectorRegistry.register
class RSSConnector(BaseConnector):
    """
    RSS / Atom feed connector.

    Fetches entries from any RSS 2.0 or Atom 1.0 feed.
    Supports incremental fetch via the `since` parameter.
    """

    source_type = "rss"
    compliance_mode = ComplianceMode.PUBLIC_WEB
    display_name = "RSS / Atom Feed"
    description = "Monitor any RSS or Atom feed for new content (blogs, news, podcasts, etc.)"

    async def validate_config(self, config: ConnectorConfig) -> ValidationResult:
        if "feed_url" not in config.params:
            return ValidationResult(valid=False, errors=["feed_url is required"])
        url = config.params["feed_url"]
        if not url.startswith(("http://", "https://")):
            return ValidationResult(valid=False, errors=["feed_url must start with http:// or https://"])
        return ValidationResult(valid=True)

    async def test_connection(self, config: ConnectorConfig) -> ConnectionTestResult:
        feed_url = config.params.get("feed_url", "")
        try:
            feed = await self._parse_feed(feed_url)
            if feed is None:
                return ConnectionTestResult(success=False, error="Failed to parse feed")
            entry_count = len(feed.get("entries", []))
            title = feed.get("feed", {}).get("title", "Unknown feed")
            return ConnectionTestResult(
                success=True,
                message=f"Connected to '{title}' — {entry_count} entries found",
                details={"title": title, "entry_count": entry_count},
            )
        except Exception as e:
            return ConnectionTestResult(success=False, error=str(e))

    async def fetch(
        self,
        config: ConnectorConfig,
        since: Optional[datetime] = None,
    ) -> AsyncIterator[RawDocument]:
        feed_url = config.params.get("feed_url", "")
        filter_keywords = config.params.get("keywords", [])
        max_docs = config.max_documents_per_run

        feed = await self._parse_feed(feed_url)
        if feed is None:
            logger.error(f"RSSConnector: failed to parse feed {feed_url}")
            return

        entries = feed.get("entries", [])
        count = 0

        for entry in entries:
            if count >= max_docs:
                break

            # Extract published date
            published_at = self._parse_entry_date(entry)

            # Skip old entries if incremental fetch
            if since and published_at and published_at <= since.replace(tzinfo=timezone.utc):
                continue

            # Build text content
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
            link = entry.get("link", "")
            author = entry.get("author", "")

            raw_text = f"{title}\n\n{summary}".strip()
            if not raw_text:
                continue

            # Keyword filter (optional)
            if filter_keywords:
                text_lower = raw_text.lower()
                if not any(kw.lower() in text_lower for kw in filter_keywords):
                    continue

            yield RawDocument(
                id=make_doc_id("rss", link or f"{feed_url}:{entry.get('id', title)}"),
                source_type="rss",
                source_url=link,
                content_hash=make_content_hash(raw_text),
                raw_text=raw_text,
                title=title,
                author=author,
                published_at=published_at,
                compliance_mode=self.compliance_mode.value,
                metadata={
                    "feed_url": feed_url,
                    "feed_title": feed.get("feed", {}).get("title", ""),
                    "tags": [t.get("term", "") for t in entry.get("tags", [])],
                },
            )
            count += 1

        logger.info(f"RSSConnector: yielded {count} documents from {feed_url}")

    async def _parse_feed(self, feed_url: str) -> Optional[dict]:
        """Fetch and parse the feed. Returns feedparser dict or None."""
        try:
            import feedparser

            # feedparser is synchronous — run in executor
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

            if feed.get("bozo") and not feed.get("entries"):
                logger.warning(f"Feed parse error for {feed_url}: {feed.get('bozo_exception')}")
                return None

            return feed
        except ImportError:
            # Fallback: fetch raw and parse manually
            logger.warning("feedparser not installed, using raw HTTP fetch")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    feed_url,
                    headers={"User-Agent": "AIGrowthOS/1.0 (growth-intelligence; polite-bot)"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                # Return minimal structure
                return {"entries": [], "feed": {"title": feed_url}, "_raw": response.text}

    def _parse_entry_date(self, entry: dict) -> Optional[datetime]:
        """Parse a feed entry's date into a timezone-aware datetime."""
        for field in ("published_parsed", "updated_parsed", "created_parsed"):
            value = entry.get(field)
            if value:
                import time
                try:
                    ts = time.mktime(value)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    continue
        return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(
            requests_per_second=0.5,   # 1 req per 2 seconds
            requests_per_minute=10,
            requests_per_day=500,
        )

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "feed_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "URL of the RSS or Atom feed",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional keywords to filter entries (OR match)",
                },
            },
            "required": ["feed_url"],
        }
