"""Create Tax Intelligence tables — idempotent (IF NOT EXISTS)."""

from __future__ import annotations

import asyncio

import asyncpg

SQL = """
CREATE TABLE IF NOT EXISTS company_tax_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL UNIQUE,
    company_name VARCHAR(500),
    company_type VARCHAR(100),
    country_code VARCHAR(10) NOT NULL DEFAULT 'TR',
    country_name VARCHAR(100),
    city VARCHAR(200),
    region VARCHAR(200),
    tax_id VARCHAR(100),
    vat_id VARCHAR(100),
    registration_number VARCHAR(100),
    is_vat_registered BOOLEAN DEFAULT TRUE,
    vat_rate NUMERIC(5,2),
    vat_filing_frequency VARCHAR(20) DEFAULT 'monthly',
    tax_year_start VARCHAR(10) DEFAULT '01-01',
    accounting_period VARCHAR(20) DEFAULT 'calendar_year',
    industry VARCHAR(200),
    annual_revenue_estimate VARCHAR(50),
    employee_count_range VARCHAR(20),
    founded_year INTEGER,
    applicable_taxes JSONB DEFAULT '[]'::jsonb,
    tax_authority_name VARCHAR(500),
    tax_authority_portal VARCHAR(500),
    tax_authority_portal_name VARCHAR(200),
    profile_completed BOOLEAN DEFAULT FALSE,
    setup_step INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoice_tax_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL,
    country_code VARCHAR(10),
    tax_regime VARCHAR(100),
    invoice_direction VARCHAR(20),
    vat_amount NUMERIC(14,2),
    vat_rate NUMERIC(5,2),
    vat_treatment VARCHAR(100),
    vat_action VARCHAR(500),
    other_taxes JSONB DEFAULT '[]'::jsonb,
    total_tax_impact NUMERIC(14,2),
    net_tax_payable NUMERIC(14,2),
    filing_period VARCHAR(50),
    filing_deadline VARCHAR(100),
    filing_deadline_date DATE,
    authority_name VARCHAR(500),
    authority_portal_url VARCHAR(500),
    authority_portal_name VARCHAR(200),
    instructions JSONB DEFAULT '[]'::jsonb,
    ai_explanation TEXT,
    ai_warnings TEXT[],
    confidence_score NUMERIC(5,4) DEFAULT 0.85,
    ai_model_used VARCHAR(100),
    web_sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tax_analysis_invoice
    ON invoice_tax_analysis(invoice_id);
CREATE INDEX IF NOT EXISTS idx_tax_analysis_workspace
    ON invoice_tax_analysis(workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tax_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    tax_type VARCHAR(100),
    tax_name VARCHAR(200),
    period VARCHAR(100),
    due_date DATE NOT NULL,
    estimated_amount NUMERIC(14,2),
    status VARCHAR(50) DEFAULT 'upcoming',
    authority_name VARCHAR(500),
    authority_url VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, tax_type, period)
);
CREATE INDEX IF NOT EXISTS idx_tax_calendar_workspace
    ON tax_calendar(workspace_id, due_date);
"""


async def main() -> None:
    conn = await asyncpg.connect("postgresql://aicmo:aicmo_dev@localhost:5432/aicmo")
    try:
        await conn.execute(SQL)
        for t in ["company_tax_profiles", "invoice_tax_analysis", "tax_calendar"]:
            exists = await conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name=$1", t
            )
            print(f"{'OK' if exists else 'MISS':4s} {t}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
