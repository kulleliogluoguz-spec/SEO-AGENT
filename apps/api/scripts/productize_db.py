"""
Productization DB schema — adds the two new tables required by the
PRODUCTIZE.md plan and verifies the existing Phase 2 tables are still
present.

Idempotent: every CREATE uses IF NOT EXISTS so it's safe to re-run.

Notes on FK targets:
- `ad_performance_daily.campaign_id` already FKs to `analytics_ad_campaigns(id)`
  via the 20260407_0004 alembic migration.
- The PRODUCTIZE.md spec creates `campaign_profit_analysis` with a FK to
  `ad_campaigns(id)`, but `ad_campaigns` is the mktg_001 creative-copy
  table — the correct target is `analytics_ad_campaigns(id)`. The Phase 2
  ensure_all_tables script already created `campaign_profit_analysis` with
  the correct FK, so we keep IF NOT EXISTS and never overwrite it here.

Usage:
    DATABASE_URL='postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo' \
        python3 scripts/productize_db.py
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

-- ─────────────────────────────────────────────
-- WORKSPACE SETTINGS (dashboard-driven config)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workspace_settings (
    workspace_id UUID PRIMARY KEY,
    company_name VARCHAR(500),
    industry VARCHAR(200),
    default_currency VARCHAR(10) DEFAULT 'USD',
    monthly_ad_budget NUMERIC(14,2),
    break_even_roas NUMERIC(10,4) DEFAULT 2.5,
    avg_order_value NUMERIC(12,2),
    cogs_per_unit NUMERIC(12,4) DEFAULT 0,
    shipping_cost NUMERIC(12,4) DEFAULT 0,
    return_rate NUMERIC(5,4) DEFAULT 0.05,
    -- Encrypted credentials (Fernet AES-128-CBC + HMAC-SHA256)
    meta_app_id_enc TEXT,
    meta_app_secret_enc TEXT,
    google_developer_token_enc TEXT,
    google_client_id_enc TEXT,
    google_client_secret_enc TEXT,
    twilio_account_sid_enc TEXT,
    twilio_auth_token_enc TEXT,
    twilio_phone_number VARCHAR(50),
    -- Setup progress
    setup_completed BOOLEAN DEFAULT FALSE,
    setup_step INTEGER DEFAULT 1,
    -- Notifications
    slack_webhook_url TEXT,
    notification_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- AD ACCOUNT CONNECTIONS (OAuth tokens per workspace)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ad_account_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    platform VARCHAR(20) NOT NULL,       -- 'meta' | 'google'
    account_id VARCHAR(200) NOT NULL,    -- Meta: act_123456 | Google: 1234567890
    account_name VARCHAR(500),
    currency VARCHAR(10) DEFAULT 'USD',
    timezone VARCHAR(100),
    -- Encrypted tokens
    access_token_enc TEXT,
    refresh_token_enc TEXT,
    long_lived_token_enc TEXT,           -- Meta: 60-day token
    -- Token management
    token_expires_at TIMESTAMPTZ,
    token_type VARCHAR(50) DEFAULT 'user',
    scopes TEXT[],
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_status VARCHAR(50) DEFAULT 'pending',
    last_sync_error TEXT,
    -- Timestamps
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,
    UNIQUE(workspace_id, platform, account_id)
);
CREATE INDEX IF NOT EXISTS idx_connections_workspace
    ON ad_account_connections(workspace_id, platform, is_active);
"""


REQUIRED_TABLES = [
    "workspace_settings",
    "ad_account_connections",
    # Existing Phase 2 tables — verified, never recreated:
    "platform_events",
    "product_costs",
    "campaign_profit_analysis",
    "contacts",
    "leads",
    "lead_timeline",
    "calls",
    "call_transcripts",
    "call_analysis",
    "invoices",
    "ai_feedback",
    "ai_memory",
    "company_profiles",
]


async def create_all() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(SCHEMA_SQL)
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        names = {r["tablename"] for r in rows}
        print("\n=== TABLE VERIFICATION ===")
        all_ok = True
        for t in REQUIRED_TABLES:
            ok = t in names
            print(f"{'OK ' if ok else 'MISS'} {t}")
            if not ok:
                all_ok = False
        print("\nAll productization tables present" if all_ok else "Some tables missing!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_all())
