"""Unit tests for TechnicalSEOAuditAgent."""
import uuid
import pytest
from app.agents.layer4.technical_seo import TechnicalSEOAuditAgent, TechnicalSEOInput
from app.agents.base import AgentRunContext


DEMO_PAGES = [
    {"url": "https://ex.com/", "title": "Home", "meta_description": "Desc", "h1": "Welcome", "word_count": 500, "status_code": 200},
    {"url": "https://ex.com/pricing", "title": None, "meta_description": None, "h1": "Pricing", "word_count": 300, "status_code": 200},
    {"url": "https://ex.com/features", "title": "Features", "meta_description": "Our features", "h1": None, "word_count": 150, "status_code": 200},
    {"url": "https://ex.com/old", "title": "Old", "meta_description": None, "h1": None, "word_count": 0, "status_code": 404},
]


class TestTechnicalSEOAuditAgent:
    @pytest.mark.asyncio
    async def test_detects_missing_title(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=DEMO_PAGES),
            ctx,
        )
        assert result.success
        issue_types = [i.issue_type for i in result.output.issues]
        assert "missing_title" in issue_types

    @pytest.mark.asyncio
    async def test_detects_thin_content(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=DEMO_PAGES),
            ctx,
        )
        assert result.success
        issue_types = [i.issue_type for i in result.output.issues]
        assert "thin_content" in issue_types

    @pytest.mark.asyncio
    async def test_detects_broken_pages(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=DEMO_PAGES),
            ctx,
        )
        assert result.success
        issue_types = [i.issue_type for i in result.output.issues]
        assert "broken_pages" in issue_types

    @pytest.mark.asyncio
    async def test_health_score_is_penalized_for_critical_issues(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=DEMO_PAGES),
            ctx,
        )
        assert result.success
        assert result.output.health_score < 100.0

    @pytest.mark.asyncio
    async def test_clean_pages_score_100(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        clean_pages = [
            {"url": "https://ex.com/", "title": "Good Title", "meta_description": "Good desc", "h1": "Good H1", "word_count": 800, "status_code": 200},
            {"url": "https://ex.com/about", "title": "About", "meta_description": "About us", "h1": "About", "word_count": 600, "status_code": 200},
        ]
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=clean_pages),
            ctx,
        )
        assert result.success
        assert result.output.health_score == 100.0
        assert result.output.issues == []

    @pytest.mark.asyncio
    async def test_pages_audited_count_matches(self):
        agent = TechnicalSEOAuditAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            TechnicalSEOInput(site_id=uuid.uuid4(), crawl_id=uuid.uuid4(), pages=DEMO_PAGES),
            ctx,
        )
        assert result.output.total_pages_audited == len(DEMO_PAGES)
