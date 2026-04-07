"""
Seed realistic demo data for the Ad Analytics platform.

Creates:
- 1 demo workspace (if missing)
- 2 ad accounts (Google + Meta)
- 8 campaigns with varied performance characteristics
- 60 days of daily performance data per campaign
- 4 AI recommendations covering critical/high/medium priorities

Run:
    DATABASE_URL='postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo' \\
        python3 scripts/seed_ad_demo.py
"""

from __future__ import annotations

import asyncio
import os
import random
import uuid
from datetime import date, timedelta

import asyncpg

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")
DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _asyncpg_dsn() -> str:
    """Convert SQLAlchemy DATABASE_URL to plain asyncpg DSN."""
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo")
    return url.replace("postgresql+asyncpg://", "postgresql://")


CAMPAIGNS = [
    # name, platform, type, daily_budget, base_roas, weekly_trend, base_ctr, base_freq
    ("Brand Search - Exact", "google_ads", "SEARCH", 150, 4.8, 0.05, 0.030, None),
    ("Competitor Keywords", "google_ads", "SEARCH", 80, 2.1, -0.12, 0.022, None),
    ("Shopping - All Products", "google_ads", "SHOPPING", 200, 3.4, 0.08, 0.018, None),
    ("Display Remarketing", "google_ads", "DISPLAY", 50, 0.9, -0.20, 0.005, None),
    ("Prospecting - Lookalike 1%", "meta_ads", "REACH", 120, 2.8, 0.15, 0.013, 2.4),
    ("Retargeting - 30 Day", "meta_ads", "CONVERSIONS", 90, 5.2, 0.03, 0.024, 3.2),
    ("Interest Targeting - Broad", "meta_ads", "CONVERSIONS", 60, 1.4, -0.08, 0.011, 4.1),
    ("Video Views - Awareness", "meta_ads", "VIDEO_VIEWS", 40, 1.1, -0.05, 0.009, 8.7),
]

RECOMMENDATIONS = [
    {
        "type": "pause_campaign",
        "priority": "critical",
        "title": "STOP: Display Remarketing is losing money",
        "description": "Campaign ROAS is 0.9x — losing $0.10 for every $1 spent over the last 7 days.",
        "expected_impact": "Stop immediate budget loss of ~$45/day",
        "ai_reasoning": "7-day ROAS of 0.9 is below break-even (1.0). Pause and review targeting/creative.",
        "campaign_idx": 3,
    },
    {
        "type": "scale_budget",
        "priority": "high",
        "title": "Scale: Retargeting - 30 Day at 5.2x ROAS",
        "description": "Your best performing campaign has room to grow. Recommend +25% budget.",
        "expected_impact": "+$450/week additional profit at 25% budget increase",
        "ai_reasoning": "ROAS 5.2 with frequency 3.2 — healthy metrics with scaling headroom.",
        "campaign_idx": 5,
    },
    {
        "type": "creative_refresh",
        "priority": "high",
        "title": "Creative fatigue: Video Views - Awareness",
        "description": "Frequency 8.7 — audience has seen this ad too many times. CTR declining.",
        "expected_impact": "+25% CTR improvement with fresh creative",
        "ai_reasoning": "Frequency of 8.7 exceeds the fatigue threshold of 7.0.",
        "campaign_idx": 7,
    },
    {
        "type": "reduce_budget",
        "priority": "medium",
        "title": "Reduce: Competitor Keywords underperforming",
        "description": "ROAS 2.1 and trending down -12% week-over-week.",
        "expected_impact": "Reallocate $40/day to higher-ROAS campaigns",
        "ai_reasoning": "Negative trend + below-target ROAS. Reduce before it hits critical.",
        "campaign_idx": 1,
    },
]


async def ensure_workspace(conn: asyncpg.Connection) -> None:
    """Make sure the demo workspace exists (and its parent org)."""
    org = await conn.fetchrow("SELECT id FROM organizations WHERE id = $1", DEMO_ORG_ID)
    if not org:
        await conn.execute(
            """
            INSERT INTO organizations (id, name, slug)
            VALUES ($1, 'Demo Org', 'demo-org')
            ON CONFLICT (id) DO NOTHING
            """,
            DEMO_ORG_ID,
        )

    ws = await conn.fetchrow("SELECT id FROM workspaces WHERE id = $1", DEMO_WORKSPACE_ID)
    if not ws:
        await conn.execute(
            """
            INSERT INTO workspaces (id, organization_id, name, slug)
            VALUES ($1, $2, 'Demo Workspace', 'demo')
            ON CONFLICT (id) DO NOTHING
            """,
            DEMO_WORKSPACE_ID,
            DEMO_ORG_ID,
        )


async def seed_account(
    conn: asyncpg.Connection, platform: str, name: str, account_id: str
) -> uuid.UUID:
    """Create or fetch an ad account row."""
    existing = await conn.fetchrow(
        "SELECT id FROM ad_accounts WHERE workspace_id = $1 AND platform = $2 AND account_id = $3",
        DEMO_WORKSPACE_ID,
        platform,
        account_id,
    )
    if existing:
        return existing["id"]

    new_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO ad_accounts (id, workspace_id, platform, account_id, account_name, currency, is_active)
        VALUES ($1, $2, $3, $4, $5, 'USD', true)
        """,
        new_id,
        DEMO_WORKSPACE_ID,
        platform,
        account_id,
        name,
    )
    return new_id


async def seed_campaign(
    conn: asyncpg.Connection,
    ad_account_id: uuid.UUID,
    name: str,
    platform_campaign_id: str,
    campaign_type: str,
    daily_budget: float,
) -> uuid.UUID:
    """Create or fetch a campaign row."""
    existing = await conn.fetchrow(
        "SELECT id FROM analytics_ad_campaigns WHERE ad_account_id = $1 AND platform_campaign_id = $2",
        ad_account_id,
        platform_campaign_id,
    )
    if existing:
        return existing["id"]

    new_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO analytics_ad_campaigns
            (id, ad_account_id, platform_campaign_id, name, status, campaign_type, daily_budget)
        VALUES ($1, $2, $3, $4, 'ENABLED', $5, $6)
        """,
        new_id,
        ad_account_id,
        platform_campaign_id,
        name,
        campaign_type,
        daily_budget,
    )
    return new_id


async def seed_performance(
    conn: asyncpg.Connection,
    campaign_id: uuid.UUID,
    daily_budget: float,
    base_roas: float,
    weekly_trend: float,
    base_ctr: float,
    base_frequency: float | None,
    days: int = 60,
) -> int:
    """Generate `days` of daily performance rows with realistic noise + trend."""
    # Wipe existing perf rows for this campaign so re-runs are idempotent
    await conn.execute("DELETE FROM ad_performance_daily WHERE campaign_id = $1", campaign_id)

    base_spend = daily_budget * random.uniform(0.7, 0.95)
    inserted = 0

    for days_ago in range(days, 0, -1):
        d = date.today() - timedelta(days=days_ago)
        # Linear trend over the period
        day_factor = 1 + ((days - days_ago) / days) * weekly_trend
        weekend_factor = 1.15 if d.weekday() >= 5 else 1.0
        noise = random.uniform(0.85, 1.15)

        spend = base_spend * weekend_factor * random.uniform(0.8, 1.2)
        roas = max(base_roas * day_factor * weekend_factor * noise, 0)
        revenue = spend * roas

        cpm = random.uniform(5, 15)
        impressions = int((spend / cpm) * 1000) if cpm > 0 else 0
        ctr = base_ctr * random.uniform(0.85, 1.15)
        clicks = int(impressions * ctr)
        cvr = random.uniform(0.02, 0.08)
        conversions = max(clicks * cvr, 0)
        cpa = spend / conversions if conversions > 0 else None
        cpc = spend / clicks if clicks > 0 else None

        if base_frequency is not None:
            frequency = base_frequency * random.uniform(0.9, 1.1)
            reach = int(impressions / frequency) if frequency > 0 else None
        else:
            frequency = None
            reach = None

        await conn.execute(
            """
            INSERT INTO ad_performance_daily
                (id, campaign_id, date, impressions, clicks, conversions,
                 spend, revenue, roas, cpa, ctr, cpm, cpc, frequency, reach)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
            uuid.uuid4(),
            campaign_id,
            d,
            impressions,
            clicks,
            conversions,
            spend,
            revenue,
            roas,
            cpa,
            ctr,
            cpm,
            cpc,
            frequency,
            reach,
        )
        inserted += 1
    return inserted


async def seed_recommendations(conn: asyncpg.Connection, campaign_ids: list[uuid.UUID]) -> int:
    """Insert demo AI recommendations linked to seeded campaigns."""
    # Wipe existing recs for the demo workspace so re-runs are idempotent
    await conn.execute("DELETE FROM ai_recommendations WHERE workspace_id = $1", DEMO_WORKSPACE_ID)

    inserted = 0
    for rec in RECOMMENDATIONS:
        idx = rec["campaign_idx"]
        if idx >= len(campaign_ids):
            continue
        await conn.execute(
            """
            INSERT INTO ai_recommendations
                (id, workspace_id, campaign_id, recommendation_type, priority,
                 title, description, expected_impact, ai_reasoning,
                 confidence_score, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending')
            """,
            uuid.uuid4(),
            DEMO_WORKSPACE_ID,
            campaign_ids[idx],
            rec["type"],
            rec["priority"],
            rec["title"],
            rec["description"],
            rec["expected_impact"],
            rec["ai_reasoning"],
            round(random.uniform(0.72, 0.95), 4),
        )
        inserted += 1
    return inserted


async def main() -> None:
    random.seed(42)  # deterministic for repeatable demos
    conn = await asyncpg.connect(_asyncpg_dsn())
    try:
        await ensure_workspace(conn)

        google_account = await seed_account(
            conn, "google_ads", "Acme Growth - Google Ads", "1234567890"
        )
        meta_account = await seed_account(
            conn, "meta_ads", "Acme Growth - Meta Ads", "act_9876543210"
        )

        campaign_ids: list[uuid.UUID] = []
        total_perf_rows = 0
        for name, platform, ctype, budget, base_roas, trend, base_ctr, base_freq in CAMPAIGNS:
            account = google_account if platform == "google_ads" else meta_account
            slug = name.lower().replace(" ", "_").replace("-", "_")
            cid = await seed_campaign(conn, account, name, f"demo_{slug}", ctype, budget)
            campaign_ids.append(cid)
            n = await seed_performance(conn, cid, budget, base_roas, trend, base_ctr, base_freq)
            total_perf_rows += n

        rec_count = await seed_recommendations(conn, campaign_ids)

        print("✅ Demo data seeded:")
        print(f"   - Workspace: {DEMO_WORKSPACE_ID}")
        print("   - Ad accounts: 2 (Google Ads + Meta Ads)")
        print(f"   - Campaigns: {len(campaign_ids)}")
        print(f"   - Performance rows: {total_perf_rows}")
        print(f"   - AI recommendations: {rec_count}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
