"""
TechnicalSEOAuditAgent — Layer 4

Audits crawled pages for technical SEO issues and produces
structured recommendations with impact/effort/confidence scoring.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class TechnicalSEOInput(BaseModel):
    site_id: uuid.UUID
    crawl_id: uuid.UUID
    pages: list[dict]  # Simplified crawl page dicts


class SEOIssue(BaseModel):
    issue_type: str
    severity: str  # critical | high | medium | low
    affected_count: int
    affected_urls: list[str]
    description: str
    recommendation: str
    impact_score: float
    effort_score: float


class TechnicalSEOOutput(BaseModel):
    site_id: uuid.UUID
    issues: list[SEOIssue]
    health_score: float  # 0–100
    total_pages_audited: int
    critical_issues: int
    high_issues: int
    summary: str


class TechnicalSEOAuditAgent(LLMAgent[TechnicalSEOInput, TechnicalSEOOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="TechnicalSEOAuditAgent",
        layer=4,
        description="Audits technical SEO issues from crawl data",
        max_retries=2,
        timeout_seconds=180,
    )

    async def _execute(
        self,
        input_data: TechnicalSEOInput,
        context: AgentRunContext,
    ) -> TechnicalSEOOutput:
        pages = input_data.pages
        issues: list[SEOIssue] = []

        # ── Rule-based checks (no LLM needed) ─────────────────────────────

        # Missing titles
        missing_title = [p["url"] for p in pages if not p.get("title")]
        if missing_title:
            issues.append(SEOIssue(
                issue_type="missing_title",
                severity="critical",
                affected_count=len(missing_title),
                affected_urls=missing_title[:10],
                description="Pages missing <title> tags",
                recommendation="Add unique, descriptive title tags to all pages",
                impact_score=0.9,
                effort_score=0.3,
            ))

        # Missing meta descriptions
        missing_meta = [p["url"] for p in pages if not p.get("meta_description")]
        if missing_meta:
            issues.append(SEOIssue(
                issue_type="missing_meta_description",
                severity="high",
                affected_count=len(missing_meta),
                affected_urls=missing_meta[:10],
                description="Pages missing meta description tags",
                recommendation="Add unique meta descriptions targeting relevant queries",
                impact_score=0.7,
                effort_score=0.3,
            ))

        # Missing H1
        missing_h1 = [p["url"] for p in pages if not p.get("h1")]
        if missing_h1:
            issues.append(SEOIssue(
                issue_type="missing_h1",
                severity="high",
                affected_count=len(missing_h1),
                affected_urls=missing_h1[:10],
                description="Pages missing H1 heading",
                recommendation="Ensure each page has exactly one H1 tag with primary keyword",
                impact_score=0.7,
                effort_score=0.2,
            ))

        # Thin content (under 300 words)
        thin = [p["url"] for p in pages if p.get("word_count", 0) < 300 and p.get("status_code") == 200]
        if thin:
            issues.append(SEOIssue(
                issue_type="thin_content",
                severity="medium",
                affected_count=len(thin),
                affected_urls=thin[:10],
                description=f"{len(thin)} pages have fewer than 300 words",
                recommendation="Expand thin content or consolidate into stronger pages",
                impact_score=0.6,
                effort_score=0.6,
            ))

        # Broken links (4xx responses)
        broken = [p["url"] for p in pages if p.get("status_code", 200) in (404, 410)]
        if broken:
            issues.append(SEOIssue(
                issue_type="broken_pages",
                severity="critical",
                affected_count=len(broken),
                affected_urls=broken[:10],
                description=f"{len(broken)} pages returning 4xx status codes",
                recommendation="Fix or redirect broken pages; remove internal links to them",
                impact_score=0.85,
                effort_score=0.4,
            ))

        # Compute health score
        critical_count = sum(1 for i in issues if i.severity == "critical")
        high_count = sum(1 for i in issues if i.severity == "high")
        total = len(pages) or 1
        penalty = (critical_count * 15 + high_count * 8) / total * 100
        health_score = max(0.0, min(100.0, 100.0 - penalty))

        # LLM enrichment: summary
        summary = await self._generate_summary(issues, len(pages), context)

        return TechnicalSEOOutput(
            site_id=input_data.site_id,
            issues=issues,
            health_score=round(health_score, 1),
            total_pages_audited=len(pages),
            critical_issues=critical_count,
            high_issues=high_count,
            summary=summary,
        )

    async def _generate_summary(
        self,
        issues: list[SEOIssue],
        page_count: int,
        context: AgentRunContext,
    ) -> str:
        if context.demo_mode or not self._llm:
            return (
                f"Technical SEO audit complete. Found {len(issues)} issue types "
                f"across {page_count} pages. Focus on critical issues first."
            )

        issues_text = "\n".join(
            f"- {i.issue_type} ({i.severity}): {i.affected_count} pages — {i.description}"
            for i in issues[:10]
        )
        system = (
            "You are a senior SEO technical auditor. Write a 2-3 sentence summary of "
            "these technical SEO issues for a non-technical growth team. "
            "Be specific, prioritized, and actionable."
        )
        user = f"Pages audited: {page_count}\nIssues found:\n{issues_text}"
        text, _ = await self._call_llm(system, user, max_tokens=300)
        return text or "Technical SEO audit complete."
