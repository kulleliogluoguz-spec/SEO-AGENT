"""
File-based demo store for all entities that normally require PostgreSQL.
Provides seeded + user-created data so every endpoint works without a DB.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "demo_store.json"

_DEFAULT = {
    "sites": [],
    "content_assets": [],
    "reports": [],
    "approvals": [],
    "recommendations": [],
}

DEMO_WS = "00000000-0000-0000-0002-000000000001"


# ── Persistence ───────────────────────────────────────────────────────────────

def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        data = _seed()
        _save(data)
        return data
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
        # Back-fill missing keys
        for k, v in _DEFAULT.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError, OSError):
        return _seed()


def _save(data: dict):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Seeded data ───────────────────────────────────────────────────────────────

def _seed() -> dict:
    data = {k: list(v) for k, v in _DEFAULT.items()}

    # Seeded site
    site_id = "00000000-0000-0000-0003-000000000001"
    data["sites"].append({
        "id": site_id,
        "workspace_id": DEMO_WS,
        "url": "https://example-brand.com",
        "domain": "example-brand.com",
        "name": "Example Brand Website",
        "status": "active",
        "product_summary": "Health and fitness brand with content about workouts, nutrition, and lifestyle.",
        "category": "Health & Fitness",
        "icp_summary": "Active adults 25-40 interested in sustainable fitness habits.",
        "last_crawled_at": _now(),
        "created_at": _now(),
    })

    # Seeded content assets
    for i, (title, atype, status) in enumerate([
        ("10-Minute Morning Workout Routine", "blog", "approved"),
        ("Why Consistency Beats Intensity", "blog", "review"),
        ("Instagram Bio Optimization Guide", "landing_page", "draft"),
        ("Beginner's Nutrition Basics", "blog", "draft"),
        ("5 Fitness Myths Debunked", "blog", "published"),
    ]):
        data["content_assets"].append({
            "id": str(uuid.uuid4()),
            "workspace_id": DEMO_WS,
            "title": title,
            "asset_type": atype,
            "status": status,
            "content": None,
            "brief": {"topic": title, "content_type": atype},
            "compliance_flags": [],
            "risk_score": 0.0,
            "created_at": _now(),
        })

    weekly_md = """# Weekly Growth Intelligence Report

**Report type:** Weekly Growth
**Period:** Week ending March 29, 2026

---

## Executive Summary

Your brand showed strong momentum this week. Fitness content engagement is up 23%, with beginner-focused posts outperforming by 2×. Organic reach is growing steadily, driven by higher-momentum keyword clusters in the beginner fitness space.

## Key Performance Indicators

| Metric | Value | Change |
|--------|-------|--------|
| Organic Sessions | 1,240 | +8.3% |
| Engagement Rate | 4.2% | +1.1% |
| Trending Keywords | 8 | — |
| Audience Fit Score | 87% | — |

## Trend Highlights

Beginner fitness content is surging with +82% momentum. The top-rising keywords this week are:

- **Beginner fitness content boom** — 62K weekly volume, +100% vs prior week
- **Functional fitness over aesthetics** — 38K weekly volume, strong brand alignment
- **Recovery & sleep optimization** — 44K weekly volume, emerging as #2 opportunity

**Recommended action:** Create a 3-part Reels series on beginner fitness milestones this week to capture the momentum peak.

## Audience Insights

Your highest-fit segment — **Fitness Beginners (6-month journey)** — has 31M potential reach on Instagram. Content angle: zero-judgment, step-by-step, real transformation stories.

Secondary segment — **Busy Professional Wellness Seekers** — is a strong conversion candidate for program or service offers. Content angle: time-efficient workouts, 30-minute routines.

## Top Recommendations

1. **Shift to Reels-first content strategy** — accounts posting 4+ Reels/week see 3–5× organic growth
2. **Optimize your Instagram bio with niche keywords** — include your category, value prop, and a clear CTA
3. **Build a 30-day beginner fitness challenge series** — drives recurring engagement, follows, and saves

## Assumptions & Confidence

- Trend data: **inferred** from niche intelligence engine
- Audience estimates: **estimated** based on fitness niche category
- KPI deltas: **observed** from seeded demo data
- Recommendations: **AI-generated** — review before acting

> *Generated by AI Growth OS · Self-hosted · Private*
"""

    data["reports"].append({
        "id": str(uuid.uuid4()),
        "workspace_id": DEMO_WS,
        "report_type": "weekly_growth",
        "title": "Weekly Growth Intelligence Report",
        "summary": "Your brand showed strong momentum this week. Fitness content engagement is up 23%, with beginner-focused posts outperforming by 2×.",
        "kpis": {
            "organic_sessions": {"value": 1240, "delta": 8.3},
            "engagement_rate": {"value": "4.2%", "delta": 1.1},
            "trending_keywords": {"value": 8},
            "audience_fit_score": {"value": "87%"},
        },
        "period_start": "2026-03-22T00:00:00Z",
        "period_end": "2026-03-29T00:00:00Z",
        "content_md": weekly_md,
        "sections": [
            {"title": "Trend Highlights", "content": "Beginner fitness content is surging (+82% momentum). Recovery and sleep content is emerging as the #2 growth opportunity for your niche."},
            {"title": "Audience Insights", "content": "Your highest-fit segment (Fitness Beginners) has 31M reach on Instagram. Content angle: zero-judgment, step-by-step transformation stories."},
            {"title": "Top Recommendations", "content": "Shift to Reels-first content strategy (4+ Reels/week drives 3–5× growth). Optimize your Instagram bio with niche keywords. Build a 30-day beginner challenge series."},
        ],
        "created_at": _now(),
    })

    media_md = """# Media Planning Report — Fitness Niche

**Report type:** Media Plan
**Generated:** March 2026

---

## Executive Summary

Based on your brand profile and niche intelligence, this report outlines the recommended channel mix, budget allocation, and test strategy for paid media activation in the fitness vertical.

## Recommended Channel Allocation

| Channel | Budget % | Goal | CPM Range |
|---------|----------|------|-----------|
| Instagram | 40% | Community & product sales | $5–14 |
| YouTube | 25% | Deep engagement & trust | $6–18 |
| TikTok | 20% | Viral reach & acquisition | $4–10 |
| Google Search | 15% | High-intent product capture | $1–3 CPC |

## Content Mix

- **70% Organic** — content-led growth through Reels, tutorials, community content
- **30% Paid** — amplification of top-performing organic content + direct response ads

## Monthly Budget Guide

| Stage | Monthly Budget |
|-------|----------------|
| Starter | $1,000–3,000 |
| Growth | $3,000–10,000 |
| Scale | $10,000+ |

## KPI Targets

| Metric | Target |
|--------|--------|
| ROAS | 3–5× |
| CAC | $40–120 |
| CPM | $5–12 |

## Priority A/B Tests

1. **Transformation story Reels vs. workout demo Reels** — hypothesis: transformation content drives 3× more conversions (run 3 weeks)
2. **YouTube 15s vs. 30s pre-roll for brand recall** — hypothesis: 30s ads with strong hook drive 2× brand recall (run 4 weeks)
3. **Retargeting video viewers vs. engagement audiences** — hypothesis: video viewers convert at 2.5× higher rate (run 2 weeks)

## Pre-Spend Checklist

Before activating paid media, ensure:

- [ ] Instagram profile is optimized (bio, highlight covers, link in bio)
- [ ] Website has proper tracking (Meta Pixel / GA4)
- [ ] At least 5 strong organic Reels performing above-average
- [ ] Landing page tested on mobile with clear CTA
- [ ] UTM parameters set up for all paid traffic

## Assumptions & Confidence

- Budget ranges: **estimated** based on fitness niche benchmarks
- CPM/CPC ranges: **estimated** from industry data — actual costs vary
- ROAS targets: **estimated** — dependent on offer, landing page, and audience
- Test plan: **inferred** from niche best practices

> *Generated by AI Growth OS · Self-hosted · Private*
"""

    data["reports"].append({
        "id": str(uuid.uuid4()),
        "workspace_id": DEMO_WS,
        "report_type": "media_plan",
        "title": "Media Planning Report — Fitness Niche",
        "summary": "Recommended channel mix: Instagram (40%), YouTube (25%), TikTok (20%), Google Search (15%). Test budget: $1,000–3,000/month. Priority: organic-first, paid amplification of proven content.",
        "kpis": {
            "recommended_channels": {"value": 4},
            "test_budget": {"value": "$1K–3K/mo"},
            "target_roas": {"value": "3–5×"},
            "content_mix": {"value": "70/30"},
        },
        "period_start": "2026-03-01T00:00:00Z",
        "period_end": "2026-03-29T00:00:00Z",
        "content_md": media_md,
        "sections": [
            {"title": "Channel Allocation", "content": "Instagram 40% (community & product sales, CPM $5–14). YouTube 25% (deep engagement & trust building). TikTok 20% (viral reach & Gen Z acquisition). Google Search 15% (high-intent product capture, CPC $1–3)."},
            {"title": "Budget Guidance", "content": "Starter: $1,000–3,000/month. Growth: $3,000–10,000/month. Scale: $10,000+/month. Begin with organic proof-of-concept before scaling paid."},
            {"title": "Priority Tests", "content": "Test 1: Transformation story Reels vs. workout demo Reels (3 weeks). Test 2: YouTube 15s vs. 30s pre-roll (4 weeks). Test 3: Video viewer retargeting vs. engagement audiences (2 weeks)."},
        ],
        "created_at": _now(),
    })

    # Seeded approvals
    for title, etype, risk in [
        ("Reels strategy shift — publish Reels 5×/week", "recommendation", "low"),
        ("Instagram bio keyword optimization", "recommendation", "low"),
        ("Launch 30-day beginner fitness challenge", "content", "medium"),
    ]:
        data["approvals"].append({
            "id": str(uuid.uuid4()),
            "workspace_id": DEMO_WS,
            "entity_type": etype,
            "entity_id": str(uuid.uuid4()),
            "title": title,
            "description": f"AI-generated suggestion for your brand's growth strategy.",
            "risk_level": risk,
            "policy_flags": [],
            "status": "pending",
            "created_at": _now(),
        })

    # Seeded recommendations (SEO/site)
    for title, category, impact, effort, priority, summary, action in [
        ("Add structured data markup (Schema.org)", "technical_seo", 0.88, 0.35, 0.91,
         "Missing schema markup reduces AI crawlability and rich result eligibility.",
         "Add Organization, WebSite, and Article schema to all pages."),
        ("Optimize meta descriptions for AI snippets", "on_page_seo", 0.82, 0.25, 0.87,
         "Meta descriptions are being truncated or missing on 60% of pages.",
         "Rewrite meta descriptions under 160 chars with brand + keyword signal."),
        ("Create pillar content for 'beginner fitness'", "content_gap", 0.79, 0.55, 0.84,
         "No top-level content targeting the highest-volume beginner fitness keywords.",
         "Publish a comprehensive beginner fitness hub page."),
        ("Fix broken internal links (12 found)", "technical_seo", 0.71, 0.2, 0.79,
         "12 internal links return 404, diluting crawl budget.",
         "Audit and fix all broken links. Redirect where appropriate."),
        ("Improve page speed — LCP > 4s on mobile", "technical_seo", 0.74, 0.65, 0.77,
         "Largest Contentful Paint is 4.2s on mobile, above the 2.5s target.",
         "Compress images, enable lazy loading, optimize render-blocking JS."),
    ]:
        data["recommendations"].append({
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "title": title,
            "category": category,
            "subcategory": None,
            "summary": summary,
            "rationale": summary,
            "evidence": [],
            "affected_urls": [],
            "proposed_action": action,
            "impact_score": impact,
            "effort_score": effort,
            "confidence_score": 0.85,
            "urgency_score": impact,
            "priority_score": priority,
            "target_metric": "organic_traffic",
            "risk_flags": [],
            "status": "open",
            "approval_required": False,
            "generated_by_agent": "seo_agent",
            "created_at": _now(),
        })

    return data


# ── Sites ─────────────────────────────────────────────────────────────────────

def get_sites(workspace_id: str) -> list[dict]:
    return [s for s in _load()["sites"] if s["workspace_id"] == workspace_id]


def get_site(site_id: str) -> dict | None:
    for s in _load()["sites"]:
        if s["id"] == site_id:
            return s
    return None


def create_site(workspace_id: str, url: str, name: str | None, max_pages: int) -> dict:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lstrip("www.") or url
    record = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "url": url,
        "domain": domain,
        "name": name or domain,
        "status": "pending",
        "product_summary": None,
        "category": None,
        "icp_summary": None,
        "last_crawled_at": None,
        "created_at": _now(),
        "_max_pages": max_pages,
    }
    data = _load()
    data["sites"].append(record)
    _save(data)
    return record


# ── Content ───────────────────────────────────────────────────────────────────

def get_content_assets(workspace_id: str, asset_type: str | None = None, status: str | None = None) -> list[dict]:
    items = [c for c in _load()["content_assets"] if c["workspace_id"] == workspace_id]
    if asset_type:
        items = [c for c in items if c["asset_type"] == asset_type]
    if status:
        items = [c for c in items if c["status"] == status]
    return items


def create_content_asset(workspace_id: str, data: dict) -> dict:
    record = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "created_at": _now(),
        **data,
    }
    store = _load()
    store["content_assets"].append(record)
    _save(store)
    return record


# ── Reports ───────────────────────────────────────────────────────────────────

def get_reports(workspace_id: str) -> list[dict]:
    return [r for r in _load()["reports"] if r["workspace_id"] == workspace_id]


def get_report(report_id: str) -> dict | None:
    for r in _load()["reports"]:
        if r["id"] == report_id:
            return r
    return None


# ── Approvals ─────────────────────────────────────────────────────────────────

def get_approvals(workspace_id: str, status: str | None = None) -> list[dict]:
    items = [a for a in _load()["approvals"] if a["workspace_id"] == workspace_id]
    if status:
        items = [a for a in items if a["status"] == status]
    return items


def action_approval(approval_id: str, action: str) -> dict | None:
    data = _load()
    for a in data["approvals"]:
        if a["id"] == approval_id:
            a["status"] = "approved" if action == "approve" else "rejected"
            _save(data)
            return a
    return None


# ── Recommendations ───────────────────────────────────────────────────────────

def get_recommendations(site_id: str, category: str | None = None) -> list[dict]:
    items = [r for r in _load()["recommendations"] if r["site_id"] == site_id]
    if category:
        items = [r for r in items if r["category"] == category]
    return sorted(items, key=lambda x: x["priority_score"], reverse=True)
