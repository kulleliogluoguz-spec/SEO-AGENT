"""
Seed realistic Phase 2 demo data — contacts, leads, calls, transcripts,
analyses, invoices, AI feedback samples.

Idempotent: re-running won't duplicate rows. Uses asyncpg directly to avoid
the SQLAlchemy session lifecycle.

Usage:
    DATABASE_URL='postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo' \
        python3 scripts/seed_full_demo.py
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


def _dsn() -> str:
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo")
    return url.replace("postgresql+asyncpg://", "postgresql://")


CONTACTS = [
    (
        "Ahmet Yılmaz",
        "TechSoft A.Ş.",
        "ahmet@techsoft.com.tr",
        "+90 532 111 2233",
        "Software",
        "Istanbul",
        "call",
    ),
    (
        "Ayşe Kaya",
        "Marketing Pro",
        "ayse@marketingpro.com",
        "+90 533 222 3344",
        "Marketing",
        "Ankara",
        "email",
    ),
    (
        "Mehmet Demir",
        "Retail Plus",
        "mehmet@retailplus.com",
        "+90 541 333 4455",
        "Retail",
        "Izmir",
        "call",
    ),
    (
        "Fatma Şahin",
        "E-Commerce Hub",
        "fatma@ecommhub.com",
        "+90 542 444 5566",
        "E-Commerce",
        "Istanbul",
        "ad",
    ),
    (
        "Ali Çelik",
        "B2B Solutions",
        "ali@b2bsolutions.com",
        "+90 505 555 6677",
        "Consulting",
        "Bursa",
        "call",
    ),
    (
        "Zeynep Arslan",
        "Digital First",
        "zeynep@digitalfirst.com",
        "+90 506 666 7788",
        "Digital Agency",
        "Antalya",
        "call",
    ),
]

LEADS = [
    (
        82,
        "hot",
        "qualified",
        "Very interested in enterprise plan. Has budget approval. Wants demo next week.",
        "interested",
        "high",
        "Schedule product demo for next Tuesday",
    ),
    (
        65,
        "warm",
        "contacted",
        "Currently evaluating 3 vendors. Price is main concern. Has 3-month timeline.",
        "evaluating",
        "medium",
        "Send competitive pricing comparison document",
    ),
    (
        45,
        "warm",
        "contacted",
        "Interested but not urgent. Will revisit in Q2. Asked for case studies.",
        "evaluating",
        "low",
        "Send relevant case studies and follow up in 30 days",
    ),
    (
        78,
        "hot",
        "qualified",
        "Strong buying signals. Budget approved. Needs quick implementation.",
        "interested",
        "high",
        "Send proposal and schedule technical call",
    ),
    (
        20,
        "cold",
        "contacted",
        "Not the right time. Company restructuring. May revisit in 6 months.",
        "not_interested",
        "low",
        "Add to cold reactivation sequence for Q4",
    ),
    (
        55,
        "warm",
        "new",
        "Left voicemail twice. Engaged via email. Interested in growth package.",
        "follow_up_needed",
        "medium",
        "Try WhatsApp contact or connect on LinkedIn",
    ),
]

INVOICES = [
    ("AWS Turkey", "AWS-2024-001", "incoming", "software", 2400.0, 432.0, 18, "USD", 5),
    (
        "Acme Corp",
        "ACME-2024-089",
        "outgoing",
        "professional_services",
        15000.0,
        3000.0,
        20,
        "TRY",
        10,
    ),
    ("Google Ads", "GADS-2024-112", "incoming", "advertising", 5800.0, 1160.0, 20, "TRY", 15),
    ("Microsoft 365", "MS365-2024-003", "incoming", "software", 890.0, 178.0, 20, "USD", 20),
    ("TechSoft A.Ş.", "TS-2024-056", "outgoing", "software", 22000.0, 4400.0, 20, "TRY", 3),
]


async def ensure_workspace(conn: asyncpg.Connection) -> None:
    org = await conn.fetchrow("SELECT id FROM organizations WHERE id = $1", DEMO_ORG_ID)
    if not org:
        await conn.execute(
            "INSERT INTO organizations(id, name, slug) VALUES($1, 'Demo Org', 'demo-org') "
            "ON CONFLICT (id) DO NOTHING",
            DEMO_ORG_ID,
        )
    ws = await conn.fetchrow("SELECT id FROM workspaces WHERE id = $1", DEMO_WORKSPACE_ID)
    if not ws:
        await conn.execute(
            "INSERT INTO workspaces(id, organization_id, name, slug) "
            "VALUES($1, $2, 'Demo Workspace', 'demo') ON CONFLICT (id) DO NOTHING",
            DEMO_WORKSPACE_ID,
            DEMO_ORG_ID,
        )


async def seed_contacts(conn: asyncpg.Connection) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for full_name, company, email, phone, industry, city, source in CONTACTS:
        existing = await conn.fetchrow(
            "SELECT id FROM contacts WHERE workspace_id=$1 AND email=$2",
            DEMO_WORKSPACE_ID,
            email,
        )
        if existing:
            ids.append(existing["id"])
            continue
        cid = await conn.fetchval(
            """
            INSERT INTO contacts(workspace_id, full_name, company_name, email, phone,
                                 industry, city, source)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id
            """,
            DEMO_WORKSPACE_ID,
            full_name,
            company,
            email,
            phone,
            industry,
            city,
            source,
        )
        ids.append(cid)
    return ids


async def seed_leads(conn: asyncpg.Connection, contact_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    lead_ids: list[uuid.UUID] = []
    for contact_id, lead in zip(contact_ids, LEADS, strict=False):
        score, cat, status, summary, intent, urgency, next_action = lead
        existing = await conn.fetchrow(
            "SELECT id FROM leads WHERE contact_id=$1 AND workspace_id=$2",
            contact_id,
            DEMO_WORKSPACE_ID,
        )
        if existing:
            lead_ids.append(existing["id"])
            continue
        lid = await conn.fetchval(
            """
            INSERT INTO leads(contact_id, workspace_id, status, qualification_score,
                              category, ai_summary, ai_intent, ai_urgency, ai_next_action,
                              last_contact_date)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,
                   NOW() - ($10::int || ' days')::interval)
            RETURNING id
            """,
            contact_id,
            DEMO_WORKSPACE_ID,
            status,
            score,
            cat,
            summary,
            intent,
            urgency,
            next_action,
            random.randint(0, 14),
        )
        lead_ids.append(lid)
    return lead_ids


SAMPLE_TRANSCRIPT = [
    ("SPEAKER_0", "Merhaba, aramanızın sebebi nedir acaba?", 0, 4),
    ("SPEAKER_1", "Evet merhaba, ürününüzle ilgili bilgi almak istiyordum.", 4, 9),
    ("SPEAKER_0", "Tabii, hangi konuda yardımcı olabilirim?", 9, 13),
    ("SPEAKER_1", "Fiyatlandırma konusunda daha detaylı bilgi alabilir miyim?", 13, 19),
    ("SPEAKER_0", "Elbette, size özel bir teklif hazırlayabiliriz.", 19, 24),
    ("SPEAKER_1", "Harika, bütçemiz var bu konuda ilerleyebiliriz.", 24, 30),
]


async def seed_calls(
    conn: asyncpg.Connection,
    contact_ids: list[uuid.UUID],
    lead_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    call_ids: list[uuid.UUID] = []
    for i, (cid, lid) in enumerate(zip(contact_ids[:4], lead_ids[:4], strict=False)):
        existing = await conn.fetchrow(
            "SELECT id FROM calls WHERE workspace_id=$1 AND contact_id=$2 LIMIT 1",
            DEMO_WORKSPACE_ID,
            cid,
        )
        if existing:
            call_ids.append(existing["id"])
            continue

        call_id = uuid.uuid4()
        days_ago = random.randint(0, 21)
        duration = random.randint(240, 1800)
        await conn.execute(
            """
            INSERT INTO calls(id, workspace_id, contact_id, lead_id, direction, status,
                              started_at, ended_at, duration_seconds, provider, consent_given,
                              transcription_status, analysis_status)
            VALUES($1, $2, $3, $4, 'outbound', 'completed',
                   NOW() - ($5::int || ' days')::interval,
                   NOW() - ($5::int || ' days')::interval + ($6::int || ' seconds')::interval,
                   $6, 'manual_upload', true, 'completed', 'completed')
            """,
            call_id,
            DEMO_WORKSPACE_ID,
            cid,
            lid,
            days_ago,
            duration,
        )
        call_ids.append(call_id)

        for spk, txt, start, end in SAMPLE_TRANSCRIPT:
            await conn.execute(
                """
                INSERT INTO call_transcripts(call_id, speaker, text, start_time, end_time, confidence)
                VALUES($1, $2, $3, $4, $5, 0.92)
                """,
                call_id,
                spk,
                txt,
                start,
                end,
            )

        scores = [82, 65, 78, 55]
        cats = ["hot", "warm", "hot", "warm"]
        await conn.execute(
            """
            INSERT INTO call_analysis(call_id, overall_sentiment, customer_sentiment,
                                      intent, urgency, objections, buying_signals, action_items,
                                      qualification_score, qualification_category, summary,
                                      next_action, follow_up_days, ai_model_used,
                                      processing_duration_ms)
            VALUES($1, 'mixed_positive', 'positive', 'interested', 'medium',
                   $2, $3, $4, $5, $6, $7, $8, 3, 'qwen3:8b', 4500)
            ON CONFLICT(call_id) DO NOTHING
            """,
            call_id,
            ["price", "timing"],
            ["mentioned budget", "asked about implementation"],
            ["send proposal", "schedule follow-up"],
            scores[i],
            cats[i],
            f"Customer showed interest in the product. Main concern was pricing. "
            f"Call lasted {duration // 60} minutes.",
            "Send detailed proposal with pricing options",
        )

    # Timeline events
    for lid in lead_ids[:4]:
        events = [
            ("call_made", "Outbound call completed", "12-minute discovery call completed."),
            ("email_sent", "Follow-up email sent", "Sent pricing document as requested."),
            (
                "score_updated",
                "Lead score updated",
                "AI qualification score updated based on call analysis.",
            ),
        ]
        for etype, title, desc in events:
            existing = await conn.fetchrow(
                "SELECT id FROM lead_timeline WHERE lead_id=$1 AND event_type=$2 AND title=$3",
                lid,
                etype,
                title,
            )
            if existing:
                continue
            await conn.execute(
                """
                INSERT INTO lead_timeline(lead_id, event_type, title, description, metadata)
                VALUES($1, $2, $3, $4, '{}'::jsonb)
                """,
                lid,
                etype,
                title,
                desc,
            )
    return call_ids


async def seed_invoices(conn: asyncpg.Connection) -> int:
    inserted = 0
    for vendor, num, direction, cat, total, vat, vat_rate, currency, days_back in INVOICES:
        existing = await conn.fetchrow(
            "SELECT id FROM invoices WHERE workspace_id=$1 AND invoice_number=$2",
            DEMO_WORKSPACE_ID,
            num,
        )
        if existing:
            continue
        sub = total - vat
        deductible = direction == "incoming"
        tax_impact = (
            f"KDV mahsup: {vat:.0f} {currency}"
            if deductible
            else f"KDV beyan edilmeli: {vat:.0f} {currency}"
        )
        await conn.execute(
            """
            INSERT INTO invoices(id, workspace_id, file_name, file_type, invoice_number,
                                 invoice_date, vendor_name, currency, subtotal, tax_amount,
                                 total_amount, direction, category, vat_rate, vat_amount,
                                 is_deductible, estimated_tax_impact, ai_notes,
                                 extraction_status, confidence_score)
            VALUES($1,$2,$3,'pdf',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,'completed',0.91)
            """,
            uuid.uuid4(),
            DEMO_WORKSPACE_ID,
            f"{vendor.replace(' ', '_')}_invoice.pdf",
            num,
            date.today() - timedelta(days=days_back),
            vendor,
            currency,
            sub,
            vat,
            total,
            direction,
            cat,
            vat_rate,
            vat,
            deductible,
            tax_impact,
            f"Fatura analizi tamamlandı. {tax_impact}\n\n⚠️ Bu bir tahmindir. Mali müşavirinize danışın.",
        )
        inserted += 1
    return inserted


async def seed_ai_feedback(conn: asyncpg.Connection) -> int:
    """Idempotent — only seeds if no rows exist for the demo workspace yet."""
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM ai_feedback WHERE workspace_id=$1", DEMO_WORKSPACE_ID
    )
    if existing and existing > 0:
        return 0
    inserted = 0
    for module in ["ad_analytics", "lead_qualification", "invoice"]:
        for _ in range(random.randint(3, 8)):
            action = random.choice(["accepted", "rejected", "accepted", "accepted"])
            await conn.execute(
                """
                INSERT INTO ai_feedback(workspace_id, module, feedback_type,
                                        original_recommendation, user_action)
                VALUES($1, $2, $3,
                       '{"type":"scale","priority":"high"}'::jsonb,
                       '{"action":"applied"}'::jsonb)
                """,
                DEMO_WORKSPACE_ID,
                module,
                action,
            )
            inserted += 1
    return inserted


async def main() -> None:
    random.seed(42)
    conn = await asyncpg.connect(_dsn())
    try:
        await ensure_workspace(conn)
        contact_ids = await seed_contacts(conn)
        lead_ids = await seed_leads(conn, contact_ids)
        call_ids = await seed_calls(conn, contact_ids, lead_ids)
        invoice_count = await seed_invoices(conn)
        feedback_count = await seed_ai_feedback(conn)
        print(
            f"OK contacts={len(contact_ids)} leads={len(lead_ids)} "
            f"calls={len(call_ids)} invoices+={invoice_count} feedback+={feedback_count}"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
