#!/usr/bin/env python3
"""
Seed Demo Data for AI CMO OS.

Creates:
  - Demo user (demo@aicmo.os / Demo1234!)
  - Demo organization + workspace
  - Sample site (example.com)
  - Sample crawl with pages
  - Sample SEO recommendations
  - Sample content assets
  - Sample approvals
  - Sample report

Usage:
  python scripts/seed_demo.py
  # or from Docker:
  docker compose exec api python scripts/seed_demo.py
"""
import asyncio
import sys
import os

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config.settings import get_settings
from app.core.security.auth import hash_password
from app.models.models import (
    ActivityLog,
    Approval,
    ApprovalStatus,
    ContentAsset,
    ContentStatus,
    Crawl,
    CrawlPage,
    CrawlStatus,
    Membership,
    MemberRole,
    Organization,
    Recommendation,
    RecommendationStatus,
    Report,
    Site,
    SiteStatus,
    User,
    Workspace,
)

settings = get_settings()


def utcnow():
    return datetime.now(timezone.utc)


DEMO_SITE_URL = "https://example-saas.com"
DEMO_DOMAIN = "example-saas.com"


async def seed(session: AsyncSession) -> None:
    print("🌱 Starting demo seed...")

    # ── User ───────────────────────────────────────────────────────────────
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="demo@aicmo.os",
        hashed_password=hash_password("Demo1234!"),
        full_name="Demo User",
        is_active=True,
        is_superuser=False,
    )
    session.add(user)

    admin_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="admin@aicmo.os",
        hashed_password=hash_password("Admin1234!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    session.add(admin_user)

    # ── Organization ───────────────────────────────────────────────────────
    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0001-000000000001"),
        name="Acme Corp",
        slug="acme-corp",
        plan="pro",
    )
    session.add(org)
    await session.flush()

    # ── Memberships ────────────────────────────────────────────────────────
    session.add(Membership(
        user_id=user.id,
        organization_id=org.id,
        role=MemberRole.OWNER,
        accepted_at=utcnow(),
    ))

    # ── Workspace ──────────────────────────────────────────────────────────
    workspace = Workspace(
        id=uuid.UUID("00000000-0000-0000-0002-000000000001"),
        organization_id=org.id,
        name="Acme Growth",
        slug="acme-growth",
        description="Main growth workspace for Acme Corp",
        autonomy_level=1,
    )
    session.add(workspace)
    await session.flush()

    # ── Site ───────────────────────────────────────────────────────────────
    site = Site(
        id=uuid.UUID("00000000-0000-0000-0003-000000000001"),
        workspace_id=workspace.id,
        url=DEMO_SITE_URL,
        domain=DEMO_DOMAIN,
        name="Acme SaaS",
        status=SiteStatus.ACTIVE,
        product_summary=(
            "Acme SaaS is a B2B project management platform for engineering teams. "
            "It helps teams plan, track, and ship software faster with AI-powered "
            "sprint planning and automated progress reports."
        ),
        category="B2B SaaS / Project Management",
        icp_summary=(
            "Engineering leaders (VP Eng, CTO) at 50-500 person software companies "
            "struggling with sprint planning and cross-team visibility."
        ),
        last_crawled_at=utcnow() - timedelta(hours=2),
    )
    session.add(site)
    await session.flush()

    # ── Crawl ──────────────────────────────────────────────────────────────
    crawl = Crawl(
        id=uuid.UUID("00000000-0000-0000-0004-000000000001"),
        site_id=site.id,
        status=CrawlStatus.COMPLETED,
        max_pages=100,
        pages_crawled=12,
        pages_failed=0,
        started_at=utcnow() - timedelta(hours=2, minutes=5),
        completed_at=utcnow() - timedelta(hours=2),
    )
    session.add(crawl)
    await session.flush()

    # ── Crawl Pages ────────────────────────────────────────────────────────
    demo_pages = [
        {
            "url": DEMO_SITE_URL + "/",
            "title": "Acme SaaS — AI-Powered Project Management",
            "meta_description": "Ship software faster with AI sprint planning.",
            "h1": "Ship software 2x faster",
            "word_count": 680,
            "status_code": 200,
        },
        {
            "url": DEMO_SITE_URL + "/pricing",
            "title": None,  # Missing title — SEO issue
            "meta_description": None,
            "h1": "Simple, Transparent Pricing",
            "word_count": 320,
            "status_code": 200,
        },
        {
            "url": DEMO_SITE_URL + "/features",
            "title": "Features",
            "meta_description": "Explore Acme features.",
            "h1": "Features",
            "word_count": 180,  # Thin content
            "status_code": 200,
        },
        {
            "url": DEMO_SITE_URL + "/blog",
            "title": "Blog — Acme SaaS",
            "meta_description": "Engineering leadership insights.",
            "h1": "Blog",
            "word_count": 90,
            "status_code": 200,
        },
        {
            "url": DEMO_SITE_URL + "/about",
            "title": "About Acme",
            "meta_description": "Our story and mission.",
            "h1": "About Us",
            "word_count": 420,
            "status_code": 200,
        },
        {
            "url": DEMO_SITE_URL + "/old-page",
            "title": "Old Page",
            "meta_description": None,
            "h1": None,
            "word_count": 0,
            "status_code": 404,
        },
    ]

    for pd in demo_pages:
        session.add(CrawlPage(
            crawl_id=crawl.id,
            url=pd["url"],
            title=pd["title"],
            meta_description=pd["meta_description"],
            h1=pd["h1"],
            word_count=pd["word_count"],
            status_code=pd["status_code"],
            issues=[],
            crawled_at=utcnow() - timedelta(hours=2),
        ))

    # ── Recommendations ────────────────────────────────────────────────────
    recommendations = [
        Recommendation(
            site_id=site.id,
            workspace_id=workspace.id,
            title="Add missing title tag to /pricing page",
            category="technical_seo",
            subcategory="metadata",
            summary="The /pricing page is missing a <title> tag, which harms CTR in search results.",
            rationale="Pages without title tags use the URL or generic text in SERPs, significantly reducing click-through rates.",
            evidence=[{"type": "crawl", "url": DEMO_SITE_URL + "/pricing", "finding": "No title tag found"}],
            affected_urls=[DEMO_SITE_URL + "/pricing"],
            proposed_action="Add: <title>Pricing — Acme SaaS | AI-Powered Project Management</title>",
            impact_score=0.85,
            effort_score=0.1,
            confidence_score=1.0,
            urgency_score=0.9,
            priority_score=0.91,
            target_metric="organic_ctr",
            status=RecommendationStatus.PENDING,
            approval_required=False,
            generated_by_agent="TechnicalSEOAuditAgent",
        ),
        Recommendation(
            site_id=site.id,
            workspace_id=workspace.id,
            title="Expand thin content on /features page",
            category="on_page_seo",
            subcategory="content_quality",
            summary="The /features page has only 180 words, which is insufficient for ranking on competitive feature-related queries.",
            rationale="Thin content pages underperform in search. Feature pages for SaaS products typically need 800-1200 words with structured comparison tables.",
            evidence=[{"type": "crawl", "url": DEMO_SITE_URL + "/features", "finding": "180 words (below 300 threshold)"}],
            affected_urls=[DEMO_SITE_URL + "/features"],
            proposed_action="Expand to 1000+ words with: feature descriptions, use cases, screenshots, and FAQ section",
            impact_score=0.72,
            effort_score=0.45,
            confidence_score=0.85,
            urgency_score=0.65,
            priority_score=0.69,
            target_metric="organic_traffic",
            status=RecommendationStatus.PENDING,
            approval_required=False,
            generated_by_agent="OnPageSEOAuditAgent",
        ),
        Recommendation(
            site_id=site.id,
            workspace_id=workspace.id,
            title="Create 'vs competitor' comparison pages",
            category="content_gap",
            subcategory="comparison_pages",
            summary="High-intent comparison queries (e.g., 'Acme vs Jira') have no dedicated landing pages.",
            rationale="Comparison pages capture bottom-of-funnel traffic with high purchase intent. Missing these pages cedes ground to review sites and competitors.",
            evidence=[{"type": "analysis", "finding": "No /vs/ pages found in crawl"}],
            affected_urls=[],
            proposed_action="Create pages for top 5 competitor comparisons. Start with highest-volume queries.",
            impact_score=0.88,
            effort_score=0.6,
            confidence_score=0.80,
            urgency_score=0.75,
            priority_score=0.77,
            target_metric="organic_leads",
            status=RecommendationStatus.APPROVED,
            approval_required=True,
            generated_by_agent="ContentGapAgent",
        ),
        Recommendation(
            site_id=site.id,
            workspace_id=workspace.id,
            title="Improve AI citation readiness with structured FAQ content",
            category="geo_aeo",
            subcategory="answer_surfaces",
            summary="The site lacks structured FAQ pages that would make it citable by AI assistants when users ask questions about project management software.",
            rationale="LLMs prefer citing pages with clear Q&A structures. Adding FAQ pages increases the probability of being recommended in AI-generated answers.",
            evidence=[{"type": "analysis", "finding": "No FAQ or Q&A structured content found"}],
            affected_urls=[],
            proposed_action="Add FAQ sections to /features and /pricing, and create dedicated /faq page with 30+ questions",
            impact_score=0.65,
            effort_score=0.4,
            confidence_score=0.6,
            urgency_score=0.55,
            priority_score=0.60,
            target_metric="ai_visibility",
            risk_flags=["GEO/AEO module is experimental — results may vary"],
            status=RecommendationStatus.PENDING,
            approval_required=False,
            generated_by_agent="AIVisibilityAgent",
        ),
    ]
    for rec in recommendations:
        session.add(rec)

    # ── Content Assets ─────────────────────────────────────────────────────
    content_assets = [
        ContentAsset(
            workspace_id=workspace.id,
            site_id=site.id,
            title="How to Run Effective Engineering Sprints in 2025",
            asset_type="blog",
            status=ContentStatus.REVIEW,
            content="""# How to Run Effective Engineering Sprints in 2025

## Introduction

Sprint planning is one of the most impactful rituals in any engineering team. Get it right and your team ships consistently. Get it wrong and you'll be in endless re-planning meetings.

This guide covers the framework we've seen work across hundreds of engineering teams.

## The Core Problem with Traditional Sprint Planning

Most sprint planning sessions fail for the same reasons:
- Too much time on estimation, not enough on alignment
- Unclear dependencies between teams
- No connection between sprint work and business goals

## A Better Approach

[Content continues — this is demo content for review]

## Conclusion

Effective sprint planning is a practice, not a process. Start with clarity on goals, use data to calibrate capacity, and keep retrospectives honest.
""",
            brief={
                "topic": "Effective Engineering Sprints",
                "content_type": "blog",
                "target_keyword": "engineering sprint planning",
            },
            compliance_flags=["Review statistics before publishing"],
            risk_score=0.1,
            generated_by_agent="LongFormWriterAgent",
        ),
        ContentAsset(
            workspace_id=workspace.id,
            site_id=site.id,
            title="Acme vs Jira: Which Project Management Tool is Right for Your Team?",
            asset_type="comparison_page",
            status=ContentStatus.DRAFT,
            brief={
                "topic": "Acme vs Jira comparison",
                "content_type": "comparison_page",
                "target_keyword": "acme vs jira",
            },
            compliance_flags=[
                "IMPORTANT: All competitor claims must be verified before publishing",
                "Do not make statements about competitor pricing without citing sources",
            ],
            risk_score=0.35,
            generated_by_agent="ContentBriefAgent",
        ),
    ]
    for asset in content_assets:
        session.add(asset)

    # ── Approvals ──────────────────────────────────────────────────────────
    session.add(Approval(
        workspace_id=workspace.id,
        entity_type="content_asset",
        entity_id=content_assets[0].id if content_assets[0].id else uuid.uuid4(),
        title="Blog Post: How to Run Effective Engineering Sprints",
        description="AI-generated blog post ready for final review before publishing.",
        risk_level="low",
        policy_flags=[],
        status=ApprovalStatus.PENDING,
        requested_by_id=user.id,
    ))

    # ── Report ─────────────────────────────────────────────────────────────
    now = utcnow()
    session.add(Report(
        workspace_id=workspace.id,
        site_id=site.id,
        report_type="weekly",
        title=f"Weekly Growth Report — {(now - timedelta(days=7)).strftime('%b %d')} to {now.strftime('%b %d, %Y')}",
        summary=(
            "This week the team completed a full site audit identifying 2 critical and 4 high-priority "
            "issues. Three content pieces are in the pipeline. Top opportunity: comparison page creation "
            "for 5 competitor terms with estimated combined monthly search volume of 4,200."
        ),
        kpis={
            "organic_sessions": {"value": 1240, "delta": 8.3},
            "organic_leads": {"value": 23, "delta": -4.2},
            "avg_position": {"value": 18.4, "delta": -1.2},
            "impressions": {"value": 45200, "delta": 12.1},
        },
        sections=[
            {
                "title": "Technical SEO",
                "content": "2 critical issues found: missing title on /pricing, broken /old-page link.",
            },
            {
                "title": "Content Pipeline",
                "content": "1 blog post in review, 1 comparison page in draft.",
            },
            {
                "title": "Pending Approvals",
                "content": "1 item awaiting approval.",
            },
        ],
        content_md="# Weekly Report\n\nSee full report in dashboard.",
        period_start=now - timedelta(days=7),
        period_end=now,
        generated_by_agent="WeeklyReportAgent",
    ))

    # ── Activity Logs ──────────────────────────────────────────────────────
    for action, entity_type in [
        ("site.onboarded", "site"),
        ("crawl.completed", "crawl"),
        ("recommendations.generated", "recommendation"),
        ("report.generated", "report"),
    ]:
        session.add(ActivityLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            details={"demo": True},
            created_at=utcnow() - timedelta(hours=1),
        ))

    await session.commit()
    print("✅ Demo seed complete!")
    print(f"\n📧 Login: demo@aicmo.os")
    print(f"🔑 Password: Demo1234!")
    print(f"🌐 Frontend: http://localhost:3000")
    print(f"📚 API docs: http://localhost:8000/docs")


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Check if already seeded
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "demo@aicmo.os"))
        if result.scalar_one_or_none():
            print("⚠️  Demo data already exists. Skipping seed.")
            print("   To reseed, clear the database first: make clean && make up")
            return

        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
