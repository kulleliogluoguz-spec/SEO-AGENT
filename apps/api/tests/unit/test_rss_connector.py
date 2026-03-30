"""Unit tests for the RSS connector."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../packages/connector-sdk"))

from connector_sdk.base import ConnectorConfig, ComplianceMode


def make_config(feed_url: str) -> ConnectorConfig:
    return ConnectorConfig(
        workspace_id="test-workspace",
        source_type="rss",
        display_name="Test Feed",
        params={"feed_url": feed_url},
    )


class TestRSSConnector:
    def setup_method(self):
        from app.connectors.rss.connector import RSSConnector
        self.connector = RSSConnector()

    def test_compliance_mode_is_public_web(self):
        assert self.connector.compliance_mode == ComplianceMode.PUBLIC_WEB

    def test_source_type(self):
        assert self.connector.source_type == "rss"

    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        config = make_config("https://news.ycombinator.com/rss")
        result = await self.connector.validate_config(config)
        assert result.valid

    @pytest.mark.asyncio
    async def test_validate_config_missing_url(self):
        config = ConnectorConfig(
            workspace_id="test",
            source_type="rss",
            display_name="Bad Config",
            params={},
        )
        result = await self.connector.validate_config(config)
        assert not result.valid
        assert any("feed_url" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_config_invalid_scheme(self):
        config = make_config("ftp://example.com/feed.rss")
        result = await self.connector.validate_config(config)
        assert not result.valid

    @pytest.mark.asyncio
    async def test_fetch_yields_raw_documents(self):
        """Fetch should yield RawDocument objects from a feed."""
        # Mock feedparser
        mock_feed = {
            "entries": [
                {
                    "title": "Test Article",
                    "link": "https://example.com/article-1",
                    "summary": "This is a test article about AI and automation.",
                    "author": "Test Author",
                    "published_parsed": (2026, 3, 28, 12, 0, 0, 4, 87, 0),
                    "tags": [],
                }
            ],
            "feed": {"title": "Test Blog"},
            "bozo": False,
        }

        config = make_config("https://example.com/feed.rss")
        config.max_documents_per_run = 10

        with patch.object(self.connector, "_parse_feed", return_value=mock_feed):
            docs = []
            async for doc in self.connector.fetch(config):
                docs.append(doc)

        assert len(docs) == 1
        assert docs[0].title == "Test Article"
        assert docs[0].source_type == "rss"
        assert docs[0].source_url == "https://example.com/article-1"
        assert "automation" in docs[0].raw_text
        assert docs[0].compliance_mode == ComplianceMode.PUBLIC_WEB.value

    @pytest.mark.asyncio
    async def test_fetch_respects_max_documents(self):
        """Fetch should not exceed max_documents_per_run."""
        entries = [
            {
                "title": f"Article {i}",
                "link": f"https://example.com/article-{i}",
                "summary": f"Content of article {i}",
                "published_parsed": (2026, 3, 28, 12, 0, 0, 4, 87, 0),
                "tags": [],
            }
            for i in range(20)
        ]
        mock_feed = {"entries": entries, "feed": {"title": "Big Feed"}, "bozo": False}

        config = make_config("https://example.com/feed.rss")
        config.max_documents_per_run = 5

        with patch.object(self.connector, "_parse_feed", return_value=mock_feed):
            docs = []
            async for doc in self.connector.fetch(config):
                docs.append(doc)

        assert len(docs) == 5

    @pytest.mark.asyncio
    async def test_fetch_keyword_filter(self):
        """Fetch should only yield documents matching keywords."""
        entries = [
            {"title": "AI news", "link": "https://example.com/ai", "summary": "AI machine learning news", "published_parsed": (2026, 3, 28, 12, 0, 0, 4, 87, 0), "tags": []},
            {"title": "Sports news", "link": "https://example.com/sports", "summary": "Football game results", "published_parsed": (2026, 3, 28, 12, 0, 0, 4, 87, 0), "tags": []},
        ]
        mock_feed = {"entries": entries, "feed": {"title": "Mixed Feed"}, "bozo": False}

        config = make_config("https://example.com/feed.rss")
        config.params["keywords"] = ["AI", "machine learning"]
        config.max_documents_per_run = 10

        with patch.object(self.connector, "_parse_feed", return_value=mock_feed):
            docs = []
            async for doc in self.connector.fetch(config):
                docs.append(doc)

        assert len(docs) == 1
        assert "AI" in docs[0].title or "AI" in docs[0].raw_text.upper()

    def test_rate_limit_policy(self):
        policy = self.connector.get_rate_limit_policy()
        assert policy.requests_per_second <= 1.0

    def test_doc_id_is_deterministic(self):
        """Same URL should always produce same document ID."""
        from connector_sdk.base import make_doc_id
        id1 = make_doc_id("rss", "https://example.com/article")
        id2 = make_doc_id("rss", "https://example.com/article")
        assert id1 == id2

    def test_doc_id_differs_for_different_urls(self):
        from connector_sdk.base import make_doc_id
        id1 = make_doc_id("rss", "https://example.com/article-1")
        id2 = make_doc_id("rss", "https://example.com/article-2")
        assert id1 != id2
