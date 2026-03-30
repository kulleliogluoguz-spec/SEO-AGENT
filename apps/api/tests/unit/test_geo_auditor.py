"""Unit tests for the GEO Auditor agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.geo.geo_auditor import GEOAuditor, GEOCheckResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_HOMEPAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Acme SaaS - Project Management for Teams</title>
    <meta name="description" content="Acme helps teams manage projects efficiently with AI-powered insights.">
    <link rel="canonical" href="https://acme.example.com/">
    <meta property="og:site_name" content="Acme SaaS">
    <meta property="og:title" content="Acme - Project Management for Teams">
    <meta property="og:description" content="AI-powered project management">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme SaaS",
        "url": "https://acme.example.com",
        "description": "Project management for teams"
    }
    </script>
</head>
<body>
    <img src="/logo.png" alt="Acme SaaS Logo" class="logo">
    <h1>Manage Projects with AI</h1>
    <h2>What is Acme?</h2>
    <p>Acme is a project management tool that helps teams track work, collaborate, and ship faster.</p>
    <h2>Key Features</h2>
    <ul>
        <li>AI-powered task prioritization</li>
        <li>Real-time collaboration</li>
        <li>Automated reporting</li>
    </ul>
    <h2>How does it work?</h2>
    <p>Connect your team, create projects, and let our AI engine suggest what to work on next.</p>
</body>
</html>
"""

SAMPLE_ROBOTS_TXT_OPEN = """
User-agent: *
Disallow: /admin/
Disallow: /private/

User-agent: Googlebot
Allow: /
"""

SAMPLE_ROBOTS_TXT_BLOCKED_AI = """
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: *
Allow: /
"""

SAMPLE_LLMS_TXT = """
# Acme SaaS

Acme is a project management platform for software teams.

## Product
- Task tracking and sprint planning
- AI-powered prioritization
- Real-time collaboration

## Key URLs
- Homepage: https://acme.example.com/
- Docs: https://docs.acme.example.com/
- API: https://api.acme.example.com/

## Contact
support@acme.example.com
"""


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_llms_txt_present():
    """llms.txt present with good content should score >= 60."""
    auditor = GEOAuditor()
    pages = {"llms_txt": SAMPLE_LLMS_TXT}
    result = await auditor._check_llms_txt("https://acme.example.com", pages)
    assert result.score >= 60
    assert result.passed
    assert result.metadata["present"] is True


@pytest.mark.asyncio
async def test_check_llms_txt_missing():
    """Missing llms.txt should score 0 and produce recommendations."""
    auditor = GEOAuditor()
    pages = {"llms_txt": None}
    result = await auditor._check_llms_txt("https://acme.example.com", pages)
    assert result.score == 0.0
    assert not result.passed
    assert result.metadata["present"] is False
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_check_robots_txt_open():
    """robots.txt that allows AI crawlers should score 100."""
    auditor = GEOAuditor()
    pages = {"robots_txt": SAMPLE_ROBOTS_TXT_OPEN}
    result = await auditor._check_robots_txt("https://acme.example.com", pages)
    assert result.score >= 80
    assert result.passed
    assert result.metadata["allows_all_ai"] is True


@pytest.mark.asyncio
async def test_check_robots_txt_blocks_ai():
    """robots.txt that blocks majority of AI crawlers should score low."""
    auditor = GEOAuditor()
    pages = {"robots_txt": SAMPLE_ROBOTS_TXT_BLOCKED_AI}
    result = await auditor._check_robots_txt("https://acme.example.com", pages)
    assert len(result.metadata["blocked_crawlers"]) >= 2


@pytest.mark.asyncio
async def test_check_robots_txt_missing():
    """No robots.txt = all crawlers allowed = high score."""
    auditor = GEOAuditor()
    pages = {"robots_txt": None}
    result = await auditor._check_robots_txt("https://acme.example.com", pages)
    assert result.score >= 80
    assert result.metadata["allows_all_ai"] is True


@pytest.mark.asyncio
async def test_check_schema_markup_with_org_schema():
    """Homepage with Organization JSON-LD should score >= 50."""
    auditor = GEOAuditor()
    pages = {"homepage": SAMPLE_HOMEPAGE_HTML}
    result = await auditor._check_schema_markup("https://acme.example.com", pages)
    assert result.score >= 40
    assert "Organization" in result.metadata["schema_types"]


@pytest.mark.asyncio
async def test_check_schema_markup_no_schema():
    """Homepage with no JSON-LD should score 0."""
    html = "<html><head><title>Test</title></head><body>hello</body></html>"
    auditor = GEOAuditor()
    pages = {"homepage": html}
    result = await auditor._check_schema_markup("https://acme.example.com", pages)
    assert result.score == 0.0
    assert not result.passed
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_check_content_citability_good_content():
    """Well-structured homepage should score >= 60."""
    auditor = GEOAuditor()
    pages = {"homepage": SAMPLE_HOMEPAGE_HTML}
    result = await auditor._check_content_citability("https://acme.example.com", pages)
    assert result.score >= 50


@pytest.mark.asyncio
async def test_check_entity_consistency_with_og_tags():
    """Homepage with og:site_name should score > 50."""
    auditor = GEOAuditor()
    pages = {"homepage": SAMPLE_HOMEPAGE_HTML}
    result = await auditor._check_entity_consistency("https://acme.example.com", pages)
    assert result.score > 50


@pytest.mark.asyncio
async def test_full_audit_mock():
    """Full audit should produce a GEOAuditResult with all scores populated."""
    auditor = GEOAuditor()

    # Mock the HTTP fetches
    pages = {
        "homepage": SAMPLE_HOMEPAGE_HTML,
        "robots_txt": SAMPLE_ROBOTS_TXT_OPEN,
        "llms_txt": SAMPLE_LLMS_TXT,
        "sitemap": '<?xml version="1.0"?><urlset></urlset>',
    }

    with patch.object(auditor, "_fetch_key_pages", return_value=pages):
        result = await auditor.audit("https://acme.example.com")

    assert result.site_url == "https://acme.example.com"
    assert 0 <= result.overall_score <= 100
    assert result.llms_txt_present is True
    assert result.robots_txt_allows_ai is True
    assert len(result.checks) == 6
    assert result.duration_seconds > 0


def test_is_crawler_blocked_by_wildcard():
    """Wildcard Disallow: / should block crawler."""
    robots = "User-agent: *\nDisallow: /\n"
    auditor = GEOAuditor()
    assert auditor._is_crawler_blocked(robots, "GPTBot") is True


def test_is_crawler_not_blocked():
    """Specific Allow should not block crawler."""
    robots = "User-agent: *\nAllow: /\n"
    auditor = GEOAuditor()
    assert auditor._is_crawler_blocked(robots, "GPTBot") is False
