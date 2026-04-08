"""
Create Phase 2 extras tables:
- platform_events (event bus persistence)
- product_costs (true profitability — COGS / shipping / returns)
- campaign_profit_analysis (kill/scale signal history)
- company_profiles (adaptive discovery output)

Idempotent: re-running won't duplicate rows. All CREATEs use IF NOT EXISTS.

Usage:
    DATABASE_URL='postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo' \
        python3 scripts/create_phase2_extras.py
"""

from __future__ import annotations

import asyncio
import os

import asyncpg


def _dsn() -> str:
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo")
    return url.replace("postgresql+asyncpg://", "postgresql://")


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Event bus
CREATE TABLE IF NOT EXISTS platform_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    source_module VARCHAR(50) NOT NULL,
    workspace_id UUID,
    payload JSONB DEFAULT '{}'::jsonb,
    processed_by TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_type_workspace
    ON platform_events(event_type, workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created
    ON platform_events(created_at DESC);

-- Product costs (for true profitability)
CREATE TABLE IF NOT EXISTS product_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    product_name VARCHAR(500),
    sku VARCHAR(255),
    cogs NUMERIC(12,4) NOT NULL DEFAULT 0,
    shipping_cost NUMERIC(12,4) DEFAULT 0,
    return_rate NUMERIC(5,4) DEFAULT 0.05,
    currency VARCHAR(10) DEFAULT 'USD',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_product_costs_workspace
    ON product_costs(workspace_id);

-- Campaign profit analysis (references analytics_ad_campaigns, not the
-- mktg_001 ad_campaigns table that holds creative copy)
CREATE TABLE IF NOT EXISTS campaign_profit_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES analytics_ad_campaigns(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    reported_roas NUMERIC(10,4),
    estimated_true_roas NUMERIC(10,4),
    contribution_margin NUMERIC(8,4),
    gross_profit NUMERIC(14,2),
    break_even_roas NUMERIC(10,4),
    kill_signal BOOLEAN DEFAULT FALSE,
    scale_signal BOOLEAN DEFAULT FALSE,
    signal_reason TEXT,
    confidence NUMERIC(5,4) DEFAULT 0.7,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id, analysis_date)
);
CREATE INDEX IF NOT EXISTS idx_profit_analysis_campaign
    ON campaign_profit_analysis(campaign_id, analysis_date DESC);

-- Company profiles (adaptive discovery output)
CREATE TABLE IF NOT EXISTS company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL UNIQUE,
    company_name TEXT,
    industry TEXT,
    stage TEXT,
    business_model TEXT,
    primary_goal TEXT,
    biggest_challenge TEXT,
    success_metric TEXT,
    target_customer TEXT,
    avg_order_value NUMERIC(12,2),
    customer_ltv NUMERIC(12,2),
    monthly_ad_spend NUMERIC(12,2),
    current_roas NUMERIC(10,4),
    break_even_roas NUMERIC(10,4),
    active_channels TEXT[],
    ai_summary TEXT,
    ai_insights TEXT[],
    discovery_transcript JSONB DEFAULT '[]'::jsonb,
    discovery_completed BOOLEAN DEFAULT FALSE,
    discovery_completed_at TIMESTAMPTZ,
    question_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_company_profiles_workspace
    ON company_profiles(workspace_id);
"""


async def create_tables() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(SCHEMA_SQL)
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' "
            "AND tablename = ANY($1::text[]) ORDER BY tablename",
            [
                "platform_events",
                "product_costs",
                "campaign_profit_analysis",
                "company_profiles",
            ],
        )
        for r in rows:
            print(f"OK {r['tablename']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_tables())
