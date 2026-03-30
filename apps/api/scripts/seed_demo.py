#!/usr/bin/env python3
"""
Seed Demo Data for AI CMO OS.

Run from inside the api container:
    docker compose exec api python scripts/seed_demo.py

Or locally (from apps/api):
    python scripts/seed_demo.py
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

# Ensure app is importable from apps/api directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Fixed UUIDs for demo data (stable across re-seeds) ──────────────────────
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ORG_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")
WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0002-000000000001")
SITE_ID = uuid.UUID("00000000-0000-0000-0003-000000000001")
CRAWL_ID = uuid.UUID("00000000-0000-0000-0004-000000000001")
CONTENT_BLOG_ID = uuid.UUID("00000000-0000-0000-0005-000000000001")
CONTENT_COMPARISON_ID = uuid.UUID("00000000-0000-0000-0005-000000000002")
APPROVAL_ID = uuid.UUID("00000000-0000-0000-0006-000000000001")


async def seed(session: AsyncSession) -> None:
    print("🌱 Seeding demo data...")

    # ── Users ──────────────────────────────────────────────────────────────
    session.add(User(
        id=USER_ID,
        email="demo@aicmo.os",
        hashed_password=hash_password("Demo1234!"),
        full_name="Demo User",
        is_active=True,
        is_superuser=False,
    ))
    session.add(User(
        id=ADMIN_ID,
        email="admin@aicmo.os",
        hashed_password=hash_password("Admin1234!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    ))

    # ── Org ────────────────────────────────────────────────────────────────
    session.add(Organization(
        id=ORG_ID,
        name="Acme Corp",
        slug="acme-corp",
        plan="pro",
        is_active=True,
    ))
    await session.flush()

    # ── Membership ─────────────────────────────────────────────────────────
    session.add(Membership(
        id=uuid.uuid4(),
        user_id=USER_ID,
        organization_id=ORG_ID,
        role=MemberRole.OWNER,
        accepted_at=utcnow(),
    ))

    # ── Workspace ──────────────────────────────────────────────────────────
    session.add(Workspace(
        id=WORKSPACE_ID,
        organization_id=ORG_ID,
        name="Acme Growth",
        slug="acme-growth",
        description="Main growth workspace",
        autonomy_level=1,
        is_active=True,
    ))
    await session.flush()

    # ── Site ───────────────────────────────────────────────────────────────
    session.add(Site(
        id=SITE_ID,
        workspace_id=WORKSPACE_ID,
        url="https://example-saas.com",
        domain="example-saas.com",
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
    ))
    await session.flush()

    # ── Crawl ──────────────────────────────────────────────────────────────
    session.add(Crawl(
        id=CRAWL_ID,
        site_id=SITE_ID,
        status=CrawlStatus.COMPLETED,
        max_pages=100,
        pages_crawled=6,
        pages_failed=0,
        started_at=utcnow() - timedelta(hours=2, minutes=5),
        completed_at=utcnow() - timedelta(hours=2),
    ))

    # ── Crawl Pages ────────────────────────────────────────────────────────
    demo_pages = [
        {"url": "/", "title": "Acme SaaS — AI-Powered Project Management",
         "meta_description": "Ship software faster with AI sprint planning.",
         "h1": "Ship software 2x faster", "word_count": 680, "status_code": 200},
        {"url": "/pricing", "title": None, "meta_description": None,
         "h1": "Simple, Transparent Pricing", "word_count": 320, "status_code": 200},
        {"url": "/features", "title": "Features", "meta_description": "Explore Acme features.",
         "h1": "Features", "word_count": 180, "status_code": 200},
        {"url": "/blog", "title": "Blog — Acme SaaS",
         "meta_description": "Engineering leadership insights.",
         "h1": "Blog", "word_count": 90, "status_code": 200},
        {"url": "/about", "title": "About Acme", "meta_description": "Our story.",
         "h1": "About Us", "word_count": 420, "status_code": 200},
        {"url": "/old-page", "title": "Old Page", "meta_description": None,
         "h1": None, "word_count": 0, "status_code": 404},
    ]
    base = "https://example-saas.com"
    for pd in demo_pages:
        session.add(CrawlPage(
            id=uuid.uuid4(),
            crawl_id=CRAWL_ID,
            url=base + pd["url"],
            title=pd["title"],
            meta_description=pd["meta_description"],
            h1=pd["h1"],
            word_count=pd["word_count"],
            status_code=pd["status_code"],
            issues=[],
            crawled_at=utcnow() - timedelta(hours=2),
        ))

    # ── Recommendations ────────────────────────────────────────────────────
    recs = [
        Recommendation(
            id=uuid.uuid4(),
            site_id=SITE_ID, workspace_id=WORKSPACE_ID,
            title="Add missing title tag to /pricing page",
            category="technical_seo", subcategory="metadata",
            summary="The /pricing page is missing a <title> tag, harming CTR in search results.",
            rationale="Pages without title tags get auto-generated SERP snippets with 20-30% lower CTR than optimized titles.",
            evidence=[{"type": "crawl", "url": base + "/pricing", "finding": "No title tag found in <head>"}],
            affected_urls=[base + "/pricing"],
            proposed_action="Add: <title>Pricing — Acme SaaS | AI-Powered Project Management</title>",
            rollback_plan="Revert title tag to previous value if CTR drops.",
            impact_score=0.85, effort_score=0.10, confidence_score=1.0, urgency_score=0.90,
            priority_score=0.91, target_metric="organic_ctr",
            status=RecommendationStatus.PENDING, approval_required=False,
            generated_by_agent="TechnicalSEOAuditAgent",
        ),
        Recommendation(
            id=uuid.uuid4(),
            site_id=SITE_ID, workspace_id=WORKSPACE_ID,
            title="Expand thin content on /features page (180 words)",
            category="on_page_seo", subcategory="content_quality",
            summary="The /features page has only 180 words — well below the 600-word minimum for competitive feature queries.",
            rationale="Thin content pages rank poorly. Feature pages for SaaS typically need 800-1200 words with structured comparison.",
            evidence=[{"type": "crawl", "url": base + "/features", "finding": "word_count=180 (threshold: 300)"}],
            affected_urls=[base + "/features"],
            proposed_action="Expand to 1000+ words: add feature details, use cases, screenshots, FAQ, and comparison table.",
            rollback_plan="N/A — adding content is low-risk.",
            impact_score=0.72, effort_score=0.45, confidence_score=0.85, urgency_score=0.65,
            priority_score=0.69, target_metric="organic_traffic",
            status=RecommendationStatus.PENDING, approval_required=False,
            generated_by_agent="OnPageSEOAuditAgent",
        ),
        Recommendation(
            id=uuid.uuid4(),
            site_id=SITE_ID, workspace_id=WORKSPACE_ID,
            title="Create 'vs competitor' comparison landing pages",
            category="content_gap", subcategory="comparison_pages",
            summary="High-intent comparison queries (e.g., 'Acme vs Jira') have no dedicated pages. Bottom-of-funnel traffic lost to review sites.",
            rationale="Comparison pages capture purchase-intent traffic. Companies with vs-pages report 25-40% higher demo conversion from organic.",
            evidence=[
                {"type": "crawl", "finding": "No /vs/ pages found in 6-page crawl sample"},
                {"type": "keyword", "finding": "'acme vs jira' returns 0 branded pages in top 10"},
            ],
            affected_urls=[],
            proposed_action="Create /vs/jira, /vs/asana, /vs/monday pages. Each 1000+ words with comparison table, use case alignment, CTA.",
            rollback_plan="Archive pages if negative brand signals emerge.",
            impact_score=0.88, effort_score=0.60, confidence_score=0.80, urgency_score=0.75,
            priority_score=0.77, target_metric="organic_leads",
            status=RecommendationStatus.APPROVED, approval_required=True,
            generated_by_agent="ContentGapAgent",
        ),
        Recommendation(
            id=uuid.uuid4(),
            site_id=SITE_ID, workspace_id=WORKSPACE_ID,
            title="Improve AI citation readiness with structured FAQ content",
            category="geo_aeo", subcategory="answer_surfaces",
            summary="No structured FAQ pages exist. LLM assistants cannot cite the site for common product category questions.",
            rationale="LLMs prefer citing pages with clear Q&A structure. Adding FAQ pages increases citation likelihood for category queries.",
            evidence=[{"type": "analysis", "finding": "No FAQ schema or Q&A structured content found in crawl"}],
            affected_urls=[],
            proposed_action="Add FAQ sections to /features and /pricing. Create /faq with 30+ questions in FAQ schema.",
            rollback_plan="N/A — additive change.",
            impact_score=0.65, effort_score=0.40, confidence_score=0.60, urgency_score=0.55,
            priority_score=0.60, target_metric="ai_visibility",
            risk_flags=["GEO/AEO module is experimental — measurement surfaces are indirect"],
            status=RecommendationStatus.PENDING, approval_required=False,
            generated_by_agent="AIVisibilityAgent",
        ),
    ]
    for r in recs:
        session.add(r)

    # ── Content Assets (IDs set explicitly before Approval references them) ──
    blog_asset = ContentAsset(
        id=CONTENT_BLOG_ID,
        workspace_id=WORKSPACE_ID, site_id=SITE_ID,
        title="How to Run Effective Engineering Sprints in 2025",
        asset_type="blog", status=ContentStatus.REVIEW,
        content="""# How to Run Effective Engineering Sprints in 2025

> **REVIEW REQUIRED** — AI-generated content. Verify all claims before publishing.

## Introduction

Sprint planning is one of the highest-leverage rituals in any engineering team.
This guide covers the framework we have seen work across hundreds of teams.

## The Core Problem

Most sprint planning sessions fail for the same reasons: too much time on
estimation, unclear dependencies, no connection to business goals.

## A Better Approach

Start with alignment, not tasks. Before pulling tickets, spend 10 minutes
answering: what does success look like this sprint?

## Conclusion

Effective sprint planning is a practice, not a process. Start with goal clarity,
calibrate capacity with data, and keep retrospectives honest.
""",
        brief={"topic": "Engineering Sprints", "content_type": "blog", "target_keyword": "engineering sprint planning"},
        compliance_flags=["Review all statistics before publishing", "No unverified claims found in this draft"],
        risk_score=0.10,
        generated_by_agent="LongFormWriterAgent",
    )
    comparison_asset = ContentAsset(
        id=CONTENT_COMPARISON_ID,
        workspace_id=WORKSPACE_ID, site_id=SITE_ID,
        title="Acme vs Jira: Which Tool is Right for Your Team?",
        asset_type="comparison_page", status=ContentStatus.DRAFT,
        brief={"topic": "Acme vs Jira", "content_type": "comparison_page", "target_keyword": "acme vs jira"},
        compliance_flags=[
            "IMPORTANT: All competitor claims must be independently verified before publishing",
            "Do not state pricing claims without citing current sources",
        ],
        risk_score=0.35,
        generated_by_agent="ContentBriefAgent",
    )
    session.add(blog_asset)
    session.add(comparison_asset)
    await session.flush()  # Ensure IDs are set before Approval references them

    # ── Approval (references the blog asset ID) ───────────────────────────
    session.add(Approval(
        id=APPROVAL_ID,
        workspace_id=WORKSPACE_ID,
        entity_type="content_asset",
        entity_id=CONTENT_BLOG_ID,  # Use explicit ID, not .id attribute
        title="Blog Post: How to Run Effective Engineering Sprints",
        description="AI-generated blog post (1 compliance flag) ready for final review before publishing.",
        risk_level="low",
        policy_flags=["LEVEL_1: Human approval required before any publishing action"],
        status=ApprovalStatus.PENDING,
        requested_by_id=USER_ID,
    ))

    # ── Report ─────────────────────────────────────────────────────────────
    now = utcnow()
    session.add(Report(
        id=uuid.uuid4(),
        workspace_id=WORKSPACE_ID, site_id=SITE_ID,
        report_type="weekly",
        title=f"Weekly Growth Report — {(now - timedelta(days=7)).strftime('%b %d')} to {now.strftime('%b %d, %Y')}",
        summary=(
            "This week the team completed a full site audit identifying 2 critical and 2 high-priority "
            "issues. Two content pieces are in the pipeline. Top opportunity: comparison page creation "
            "for 5 competitor terms with estimated 4,200 combined monthly searches."
        ),
        kpis={
            "organic_sessions": {"value": 1240, "delta": 8.3},
            "organic_leads": {"value": 23, "delta": -4.2},
            "avg_position": {"value": 18.4, "delta": -1.2},
            "impressions": {"value": 45200, "delta": 12.1},
            "clicks": {"value": 1180, "delta": 6.8},
        },
        sections=[
            {"title": "Technical SEO", "content": "2 critical issues: missing title on /pricing, 404 on /old-page."},
            {"title": "Content Pipeline", "content": "1 blog post in review (low risk), 1 comparison page in draft (medium risk — competitor claims need verification)."},
            {"title": "Pending Approvals", "content": "1 item awaiting human approval."},
            {"title": "AI Visibility", "content": "Score: 42/100. Priority: add FAQ structured content to improve LLM citation readiness."},
        ],
        content_md="# Weekly Report\n\nSee dashboard for full report.",
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
            id=uuid.uuid4(),
            workspace_id=WORKSPACE_ID, user_id=USER_ID,
            action=action, entity_type=entity_type,
            details={"demo": True, "seeded": True},
            created_at=utcnow() - timedelta(hours=1),
        ))

    await session.commit()
    print("✅ Demo data seeded successfully!")
    print()
    print("  📧  Login:    demo@aicmo.os")
    print("  🔑  Password: Demo1234!")
    print()
    print("  🌐  Frontend:  http://localhost:3000")
    print("  📚  API docs:  http://localhost:8000/docs")
    print("  ⚡  Temporal:  http://localhost:8088")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        existing = await session.execute(select(User).where(User.email == "demo@aicmo.os"))
        if existing.scalar_one_or_none():
            print("⚠️  Demo data already exists. Skipping.")
            print("   To reseed: docker compose down -v && docker compose up -d && make migrate && make seed")
            return
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
