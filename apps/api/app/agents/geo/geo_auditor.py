"""
GEO Auditor Agent — Generative Engine Optimization analysis.

Inspects a website for AI discoverability: how well can LLM-based answer
engines (ChatGPT, Perplexity, Gemini, etc.) find, understand, and cite this site?

Checks performed:
  1. llms.txt — presence and quality
  2. robots.txt — AI crawler access (GPTBot, Claude-Web, PerplexityBot, etc.)
  3. Structured data / JSON-LD — schema markup completeness
  4. Content citability — are pages structured as citable answer fragments?
  5. Entity consistency — brand name, product name, and key facts are consistent
  6. Canonical signals — canonical tags, hreflang, sitemap
  7. AI-readable content — clarity, fact density, answer-readiness

This agent uses ONLY local LLM inference and local tools.
No external AI API is called.

Inspired by: geo-seo-claude, geo-optimizer-skill, next-geo (see docs/architecture/target-architecture.md)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ── Result Types ──────────────────────────────────────────────────────────────

@dataclass
class GEOCheckResult:
    """Result of a single GEO check."""
    check_name: str
    score: float              # 0-100
    passed: bool
    evidence: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GEOAuditResult:
    """Complete GEO audit result for a site."""
    site_url: str
    overall_score: float
    citability_score: float
    ai_crawler_score: float
    schema_score: float
    entity_score: float
    content_clarity_score: float
    llms_txt_present: bool
    llms_txt_quality: float
    robots_txt_allows_ai: bool
    structured_data_types: list[str]
    checks: list[GEOCheckResult]
    issues: list[dict]
    recommendations: list[dict]
    duration_seconds: float
    ai_model_used: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── AI Crawler User-Agent patterns ────────────────────────────────────────────
AI_CRAWLERS = [
    "GPTBot",           # OpenAI
    "ChatGPT-User",     # OpenAI ChatGPT
    "Claude-Web",       # Anthropic
    "ClaudeBot",        # Anthropic
    "PerplexityBot",    # Perplexity
    "Googlebot",        # Google (for AI Overviews)
    "Google-Extended",  # Google AI training
    "Bingbot",          # Bing (Copilot)
    "CCBot",            # Common Crawl (used by many AI companies)
    "anthropic-ai",     # Anthropic
    "cohere-ai",        # Cohere
]


# ── GEO Auditor ───────────────────────────────────────────────────────────────

class GEOAuditor:
    """
    Performs a complete GEO audit on a website.

    All checks are rule-based + heuristic. An optional LLM analysis
    pass can be enabled for content citability scoring.
    """

    def __init__(
        self,
        http_timeout: float = 30.0,
        llm_client: Any = None,          # Optional: local LLM for content analysis
    ) -> None:
        self.http_timeout = http_timeout
        self.llm_client = llm_client

    async def audit(self, site_url: str) -> GEOAuditResult:
        """
        Run a complete GEO audit on the given site URL.
        Returns a GEOAuditResult with scores, issues, and recommendations.
        """
        start = time.time()
        site_url = site_url.rstrip("/")
        checks: list[GEOCheckResult] = []

        # Fetch key pages concurrently
        pages = await self._fetch_key_pages(site_url)

        # Run all checks
        checks.append(await self._check_llms_txt(site_url, pages))
        checks.append(await self._check_robots_txt(site_url, pages))
        checks.append(await self._check_schema_markup(site_url, pages))
        checks.append(await self._check_canonical_signals(site_url, pages))
        checks.append(await self._check_content_citability(site_url, pages))
        checks.append(await self._check_entity_consistency(site_url, pages))

        # Aggregate scores
        llms_check = next(c for c in checks if c.check_name == "llms_txt")
        robots_check = next(c for c in checks if c.check_name == "robots_txt")
        schema_check = next(c for c in checks if c.check_name == "schema_markup")
        citability_check = next(c for c in checks if c.check_name == "content_citability")
        entity_check = next(c for c in checks if c.check_name == "entity_consistency")

        citability_score = citability_check.score
        ai_crawler_score = (robots_check.score + llms_check.score) / 2
        schema_score = schema_check.score
        entity_score = entity_check.score
        content_clarity_score = citability_check.metadata.get("clarity_score", 50.0)

        overall_score = (
            citability_score * 0.30
            + ai_crawler_score * 0.20
            + schema_score * 0.20
            + entity_score * 0.15
            + content_clarity_score * 0.15
        )

        # Collect all issues + recommendations
        all_issues = []
        all_recommendations = []
        for check in checks:
            for issue in check.issues:
                all_issues.append({
                    "check": check.check_name,
                    "issue": issue,
                    "severity": "high" if check.score < 40 else "medium" if check.score < 70 else "low",
                })
            for rec in check.recommendations:
                all_recommendations.append({
                    "check": check.check_name,
                    "recommendation": rec,
                    "impact": "high" if check.score < 40 else "medium",
                })

        # Sort recommendations by impact
        all_recommendations.sort(key=lambda r: 0 if r["impact"] == "high" else 1)

        structured_data_types = schema_check.metadata.get("schema_types", [])

        return GEOAuditResult(
            site_url=site_url,
            overall_score=round(overall_score, 1),
            citability_score=round(citability_score, 1),
            ai_crawler_score=round(ai_crawler_score, 1),
            schema_score=round(schema_score, 1),
            entity_score=round(entity_score, 1),
            content_clarity_score=round(content_clarity_score, 1),
            llms_txt_present=llms_check.metadata.get("present", False),
            llms_txt_quality=llms_check.score,
            robots_txt_allows_ai=robots_check.metadata.get("allows_all_ai", True),
            structured_data_types=structured_data_types,
            checks=checks,
            issues=all_issues,
            recommendations=all_recommendations,
            duration_seconds=round(time.time() - start, 2),
        )

    async def _fetch_key_pages(self, site_url: str) -> dict[str, Optional[str]]:
        """Fetch homepage, robots.txt, llms.txt, and sitemap in parallel."""
        urls = {
            "homepage": site_url,
            "robots_txt": urljoin(site_url, "/robots.txt"),
            "llms_txt": urljoin(site_url, "/llms.txt"),
            "sitemap": urljoin(site_url, "/sitemap.xml"),
        }

        async def fetch_one(key: str, url: str) -> tuple[str, Optional[str]]:
            try:
                async with httpx.AsyncClient(
                    timeout=self.http_timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "AIGrowthOS/1.0 (GEO-audit; +https://github.com/ai-growth-os)"},
                ) as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        return key, r.text
                    return key, None
            except Exception as e:
                logger.debug(f"Failed to fetch {url}: {e}")
                return key, None

        results = await asyncio.gather(*[fetch_one(k, v) for k, v in urls.items()])
        return dict(results)

    async def _check_llms_txt(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check for llms.txt — the emerging standard for AI-readable site summaries."""
        content = pages.get("llms_txt")
        check = GEOCheckResult(check_name="llms_txt", score=0.0, passed=False)

        if not content:
            check.score = 0.0
            check.passed = False
            check.issues.append("No llms.txt file found")
            check.recommendations.extend([
                "Create /llms.txt following the llms.txt specification",
                "Include: company name, product description, key URLs, usage policy",
                "See https://llmstxt.org for the specification",
            ])
            check.metadata["present"] = False
            return check

        check.metadata["present"] = True
        check.metadata["length"] = len(content)
        score = 40.0  # Base score for having the file

        # Check content quality
        content_lower = content.lower()
        quality_signals = {
            "has_description": any(kw in content_lower for kw in ["#", "description", "about"]),
            "has_links": "http" in content_lower,
            "has_product_info": any(kw in content_lower for kw in ["product", "service", "feature"]),
            "has_contact": any(kw in content_lower for kw in ["contact", "email", "support"]),
            "reasonable_length": 100 < len(content) < 10000,
        }

        passing_signals = sum(v for v in quality_signals.values())
        score += (passing_signals / len(quality_signals)) * 60

        check.score = score
        check.passed = score >= 60
        check.evidence.append(f"Found llms.txt ({len(content)} chars)")
        check.metadata["quality_signals"] = quality_signals

        if not quality_signals["has_description"]:
            check.recommendations.append("Add a clear product description to llms.txt")
        if not quality_signals["has_links"]:
            check.recommendations.append("Add key page URLs to llms.txt for AI navigation")
        if not quality_signals["reasonable_length"]:
            check.recommendations.append("Expand llms.txt with more comprehensive information")

        return check

    async def _check_robots_txt(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check robots.txt for AI crawler access."""
        content = pages.get("robots_txt")
        check = GEOCheckResult(check_name="robots_txt", score=0.0, passed=False)

        if not content:
            check.score = 80.0  # No robots.txt = all crawlers allowed
            check.passed = True
            check.evidence.append("No robots.txt found — all crawlers permitted by default")
            check.metadata["allows_all_ai"] = True
            return check

        check.metadata["robots_txt_length"] = len(content)
        blocked_crawlers = []
        allowed_crawlers = []

        for crawler in AI_CRAWLERS:
            if self._is_crawler_blocked(content, crawler):
                blocked_crawlers.append(crawler)
            else:
                allowed_crawlers.append(crawler)

        check.metadata["blocked_crawlers"] = blocked_crawlers
        check.metadata["allowed_crawlers"] = allowed_crawlers
        check.metadata["allows_all_ai"] = len(blocked_crawlers) == 0

        if not blocked_crawlers:
            check.score = 100.0
            check.passed = True
            check.evidence.append(f"All AI crawlers permitted ({len(allowed_crawlers)} checked)")
        elif len(blocked_crawlers) < len(AI_CRAWLERS) / 2:
            check.score = 60.0
            check.passed = True
            check.evidence.append(f"{len(blocked_crawlers)} AI crawlers blocked: {', '.join(blocked_crawlers)}")
            check.recommendations.append(
                f"Consider allowing these AI crawlers for better discoverability: {', '.join(blocked_crawlers)}"
            )
        else:
            check.score = 20.0
            check.passed = False
            check.issues.append(f"Majority of AI crawlers are blocked ({len(blocked_crawlers)}/{len(AI_CRAWLERS)})")
            check.recommendations.append(
                "Review robots.txt AI crawler restrictions — blocking AI crawlers limits discoverability in AI search"
            )
            for crawler in blocked_crawlers:
                check.recommendations.append(f"Consider allowing {crawler} in robots.txt")

        return check

    def _is_crawler_blocked(self, robots_txt: str, crawler_name: str) -> bool:
        """Check if a specific crawler is blocked in robots.txt."""
        lines = robots_txt.lower().split("\n")
        current_agents = []
        in_relevant_block = False

        for line in lines:
            line = line.strip()
            if line.startswith("user-agent:"):
                agent = line.replace("user-agent:", "").strip()
                current_agents = [agent]
                in_relevant_block = (
                    agent == "*" or crawler_name.lower() in agent
                )
            elif line.startswith("disallow:") and in_relevant_block:
                disallow_path = line.replace("disallow:", "").strip()
                if disallow_path == "/" or disallow_path == "/*":
                    return True

        return False

    async def _check_schema_markup(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check for JSON-LD structured data on the homepage."""
        homepage = pages.get("homepage", "")
        check = GEOCheckResult(check_name="schema_markup", score=0.0, passed=False)

        if not homepage:
            check.score = 0.0
            check.issues.append("Homepage not accessible")
            return check

        soup = BeautifulSoup(homepage, "lxml")
        schema_scripts = soup.find_all("script", {"type": "application/ld+json"})

        if not schema_scripts:
            check.score = 0.0
            check.passed = False
            check.issues.append("No JSON-LD structured data found on homepage")
            check.recommendations.extend([
                "Add JSON-LD structured data (Organization, Product, WebSite schemas)",
                "Use schema.org/Organization to establish brand identity for AI systems",
                "Add FAQ schema on key landing pages for AI-extractable answers",
            ])
            check.metadata["schema_types"] = []
            return check

        schema_types = []
        score = 40.0  # Base for having any schema

        for script in schema_scripts:
            try:
                data = json.loads(script.string or "")
                schema_type = data.get("@type", "")
                if isinstance(schema_type, list):
                    schema_types.extend(schema_type)
                elif schema_type:
                    schema_types.append(schema_type)
            except json.JSONDecodeError:
                check.issues.append("Invalid JSON-LD found on page")

        check.metadata["schema_types"] = schema_types
        check.metadata["schema_count"] = len(schema_scripts)

        # Score based on presence of high-value schema types
        high_value_types = {"Organization", "Product", "WebSite", "FAQPage", "HowTo", "Article"}
        found_high_value = set(schema_types) & high_value_types

        score += (len(found_high_value) / max(len(high_value_types), 1)) * 60

        check.score = min(score, 100.0)
        check.passed = check.score >= 50
        check.evidence.append(f"Found {len(schema_scripts)} JSON-LD blocks: {', '.join(schema_types)}")

        if "Organization" not in schema_types:
            check.recommendations.append(
                "Add Organization schema with name, url, logo, description for brand identity"
            )
        if "FAQPage" not in schema_types:
            check.recommendations.append(
                "Add FAQPage schema on key pages — AI systems extract FAQ answers directly"
            )
        if not found_high_value:
            check.recommendations.append(
                "Add high-value schema types: Organization, Product, FAQPage, HowTo"
            )

        return check

    async def _check_canonical_signals(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check canonical tags, hreflang, and sitemap."""
        homepage = pages.get("homepage", "")
        sitemap = pages.get("sitemap")
        check = GEOCheckResult(check_name="canonical_signals", score=0.0, passed=False)

        if not homepage:
            check.score = 0.0
            return check

        soup = BeautifulSoup(homepage, "lxml")
        score = 60.0  # Baseline

        # Check canonical tag
        canonical = soup.find("link", {"rel": "canonical"})
        if canonical:
            check.evidence.append(f"Canonical tag: {canonical.get('href', '')}")
            score += 15.0
        else:
            check.issues.append("No canonical tag on homepage")
            check.recommendations.append("Add <link rel='canonical'> to all pages")

        # Check sitemap
        if sitemap:
            check.evidence.append("Sitemap.xml accessible")
            score += 15.0
        else:
            check.issues.append("No sitemap.xml found")
            check.recommendations.append("Create and submit sitemap.xml for better crawlability")

        # Check meta description (important for AI snippets)
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            check.evidence.append(f"Meta description present ({len(meta_desc['content'])} chars)")
        else:
            check.issues.append("No meta description on homepage")
            check.recommendations.append(
                "Add a clear meta description — AI systems use this as a primary summary signal"
            )
            score -= 10.0

        check.score = min(max(score, 0.0), 100.0)
        check.passed = check.score >= 60
        return check

    async def _check_content_citability(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check if content is structured for AI citation and extraction."""
        homepage = pages.get("homepage", "")
        check = GEOCheckResult(check_name="content_citability", score=0.0, passed=False)

        if not homepage:
            check.score = 0.0
            return check

        soup = BeautifulSoup(homepage, "lxml")
        score = 0.0

        # Extract text content
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())

        # Check for heading structure (H1, H2, H3)
        h1s = soup.find_all("h1")
        h2s = soup.find_all("h2")
        has_good_headings = len(h1s) >= 1 and len(h2s) >= 2

        if has_good_headings:
            score += 25.0
            check.evidence.append(f"Good heading structure: {len(h1s)} H1, {len(h2s)} H2")
        else:
            check.issues.append("Poor heading hierarchy")
            check.recommendations.append(
                "Use clear H1/H2/H3 heading structure — AI systems use headings to parse content"
            )

        # Check for value proposition clarity
        if word_count > 100:
            score += 20.0
            check.evidence.append(f"Substantial content: {word_count} words")
        else:
            check.issues.append(f"Thin content on homepage ({word_count} words)")

        # Check for answer-like fragments (direct answers)
        answer_patterns = [
            r"\b(is|are|helps|enables|allows|provides|offers)\b",
            r"\bwhat is\b",
            r"\bhow (to|does|it works)\b",
        ]
        answer_matches = sum(
            1 for p in answer_patterns if re.search(p, text.lower())
        )
        if answer_matches >= 2:
            score += 20.0
            check.evidence.append("Content contains answer-structured fragments")
        else:
            check.recommendations.append(
                "Add clear 'what is X' and 'how does X work' sections — AI systems extract these as answers"
            )

        # Check for list/bullet content (highly citable)
        lists = soup.find_all(["ul", "ol"])
        if lists:
            score += 15.0
            check.evidence.append(f"Contains {len(lists)} list elements (high citability)")
        else:
            check.recommendations.append(
                "Add bullet lists to present features and benefits — LLMs prefer structured lists"
            )

        # Check for clear entity mentions (brand, product names)
        title = soup.find("title")
        if title and title.string:
            score += 10.0
            check.evidence.append(f"Page title: {title.string}")

        # Open Graph tags
        og_tags = soup.find_all("meta", property=lambda p: p and p.startswith("og:"))
        if og_tags:
            score += 10.0
            check.evidence.append(f"OpenGraph tags present ({len(og_tags)} tags)")
        else:
            check.recommendations.append(
                "Add OpenGraph meta tags — these help AI systems understand page identity"
            )

        check.score = min(score, 100.0)
        check.passed = check.score >= 60
        check.metadata["word_count"] = word_count
        check.metadata["clarity_score"] = score  # Used for content_clarity_score

        return check

    async def _check_entity_consistency(self, site_url: str, pages: dict) -> GEOCheckResult:
        """Check brand/entity name consistency across key signals."""
        homepage = pages.get("homepage", "")
        check = GEOCheckResult(check_name="entity_consistency", score=50.0, passed=True)

        if not homepage:
            check.score = 0.0
            return check

        soup = BeautifulSoup(homepage, "lxml")
        score = 50.0

        # Extract entity signals
        title_tag = soup.find("title")
        og_site_name = soup.find("meta", property="og:site_name")
        h1 = soup.find("h1")
        logo_alt = None
        logo_img = soup.find("img", {"class": re.compile("logo", re.I)})
        if logo_img:
            logo_alt = logo_img.get("alt", "")

        title_text = title_tag.string if title_tag else ""
        og_name_text = og_site_name.get("content", "") if og_site_name else ""
        h1_text = h1.get_text(strip=True) if h1 else ""

        entities = [t for t in [title_text, og_name_text, h1_text, logo_alt] if t]
        check.metadata["entities_found"] = entities

        if og_site_name:
            score += 20.0
            check.evidence.append(f"og:site_name: {og_name_text}")
        else:
            check.recommendations.append(
                "Add og:site_name meta tag — AI systems use this to identify the brand"
            )

        if logo_alt:
            score += 15.0
            check.evidence.append(f"Logo alt text: {logo_alt}")
        else:
            check.recommendations.append(
                "Add descriptive alt text to logo image with brand name"
            )

        if h1_text:
            score += 15.0

        check.score = min(score, 100.0)
        check.passed = check.score >= 60
        return check
