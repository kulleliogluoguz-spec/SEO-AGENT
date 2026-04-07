"""
Create the cross-module shared tables used by Phase 2 modules
(Calling Engine, Finance/Invoice Intelligence, AI Learning, Email Bridge).

These tables are intentionally created via raw SQL (not Alembic) so they can
exist alongside other models that use SQLAlchemy declarative metadata without
risk of cross-revision conflicts.

Idempotent: every CREATE uses IF NOT EXISTS.

Usage:
    DATABASE_URL='postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo' \
        python3 scripts/create_shared_tables.py
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

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    full_name VARCHAR(500),
    company_name VARCHAR(500),
    email VARCHAR(255),
    phone VARCHAR(100),
    website VARCHAR(500),
    linkedin_url VARCHAR(500),
    country VARCHAR(100),
    city VARCHAR(100),
    industry VARCHAR(200),
    company_size VARCHAR(50),
    source VARCHAR(100),
    tags TEXT[],
    custom_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id) NOT NULL,
    workspace_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'new',
    qualification_score INTEGER DEFAULT 0,
    category VARCHAR(50),
    last_contact_date TIMESTAMPTZ,
    next_follow_up_date DATE,
    follow_up_count INTEGER DEFAULT 0,
    call_count INTEGER DEFAULT 0,
    email_count INTEGER DEFAULT 0,
    ad_touched BOOLEAN DEFAULT FALSE,
    ai_summary TEXT,
    ai_objections TEXT[],
    ai_intent VARCHAR(100),
    ai_urgency VARCHAR(50),
    ai_next_action TEXT,
    estimated_deal_value NUMERIC(14,2),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) NOT NULL,
    event_type VARCHAR(100),
    title VARCHAR(500),
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID,
    module VARCHAR(100),
    feedback_type VARCHAR(50),
    original_recommendation JSONB,
    user_action JSONB,
    outcome JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    memory_type VARCHAR(50),
    module VARCHAR(100),
    key VARCHAR(255),
    value JSONB,
    confidence NUMERIC(5,4),
    observation_count INTEGER DEFAULT 1,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, module, key)
);

CREATE TABLE IF NOT EXISTS phase2_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    contact_id UUID REFERENCES contacts(id),
    lead_id UUID REFERENCES leads(id),
    direction VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    recording_path VARCHAR(1000),
    recording_size_mb NUMERIC(10,2),
    transcription_status VARCHAR(50) DEFAULT 'pending',
    analysis_status VARCHAR(50) DEFAULT 'pending',
    provider VARCHAR(50),
    provider_call_id VARCHAR(255),
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES phase2_calls(id) NOT NULL,
    speaker VARCHAR(50),
    speaker_label VARCHAR(100),
    text TEXT NOT NULL,
    start_time NUMERIC(10,3),
    end_time NUMERIC(10,3),
    confidence NUMERIC(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES phase2_calls(id) NOT NULL UNIQUE,
    overall_sentiment VARCHAR(50),
    customer_sentiment VARCHAR(50),
    agent_sentiment VARCHAR(50),
    intent VARCHAR(100),
    urgency VARCHAR(50),
    objections TEXT[],
    buying_signals TEXT[],
    action_items TEXT[],
    qualification_score INTEGER,
    qualification_category VARCHAR(50),
    summary TEXT,
    key_points TEXT[],
    next_action TEXT,
    follow_up_days INTEGER,
    ai_model_used VARCHAR(100),
    processing_duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    file_path VARCHAR(1000),
    file_name VARCHAR(500),
    file_type VARCHAR(50),
    invoice_number VARCHAR(255),
    invoice_date DATE,
    due_date DATE,
    vendor_name VARCHAR(500),
    vendor_tax_id VARCHAR(100),
    customer_name VARCHAR(500),
    customer_tax_id VARCHAR(100),
    currency VARCHAR(10) DEFAULT 'TRY',
    subtotal NUMERIC(14,2),
    tax_amount NUMERIC(14,2),
    total_amount NUMERIC(14,2),
    direction VARCHAR(20),
    category VARCHAR(100),
    tax_category VARCHAR(100),
    is_deductible BOOLEAN,
    vat_rate NUMERIC(5,2),
    vat_amount NUMERIC(14,2),
    estimated_tax_impact TEXT,
    extraction_status VARCHAR(50) DEFAULT 'pending',
    confidence_score NUMERIC(5,4),
    needs_human_review BOOLEAN DEFAULT FALSE,
    human_reviewed BOOLEAN DEFAULT FALSE,
    ai_notes TEXT,
    line_items JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_workspace        ON contacts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_leads_contact             ON leads(contact_id);
CREATE INDEX IF NOT EXISTS idx_leads_workspace_status    ON leads(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_phase2_calls_contact      ON phase2_calls(contact_id);
CREATE INDEX IF NOT EXISTS idx_phase2_calls_workspace    ON phase2_calls(workspace_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_call          ON call_transcripts(call_id);
CREATE INDEX IF NOT EXISTS idx_invoices_workspace        ON invoices(workspace_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date             ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_ai_memory_workspace       ON ai_memory(workspace_id, module);
CREATE INDEX IF NOT EXISTS idx_timeline_lead             ON lead_timeline(lead_id);
"""


async def create_tables() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(SCHEMA_SQL)
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' "
            "AND tablename = ANY($1::text[]) ORDER BY tablename",
            [
                "contacts",
                "leads",
                "lead_timeline",
                "ai_feedback",
                "ai_memory",
                "phase2_calls",
                "call_transcripts",
                "call_analysis",
                "invoices",
            ],
        )
        for r in rows:
            print(f"OK {r['tablename']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_tables())
