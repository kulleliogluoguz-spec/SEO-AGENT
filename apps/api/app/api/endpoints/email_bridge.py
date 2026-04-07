"""
Email Bridge — Mautic integration + AI draft endpoints.

NOTE: prefix is `/api/v1/email-bridge` to avoid colliding with the existing
`/api/v1/email` Mautic email-automation endpoint that already ships in the
platform.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.email.mautic_bridge import MauticBridge
from app.services.shared.data_bridge import DataBridge

router = APIRouter(prefix="/api/v1/email-bridge", tags=["Email Bridge"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


@router.post("/sync-lead/{lead_id}")
async def sync_lead_to_mautic(
    lead_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        text(
            """
            SELECT l.*, c.full_name, c.email, c.phone, c.company_name
            FROM leads l
            JOIN contacts c ON c.id = l.contact_id
            WHERE l.id = :lid
            """
        ),
        {"lid": lead_id},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = dict(row._mapping)
    if not lead.get("email"):
        raise HTTPException(400, "Lead has no email address")

    bridge = MauticBridge()
    mautic_id = bridge.sync_contact(lead, lead.get("qualification_score") or 0)
    sequence_map = {
        "hot": "hot_lead_followup",
        "warm": "warm_lead_nurture",
        "cold": "cold_lead_reactivation",
    }
    seq = sequence_map.get(lead.get("category") or "cold", "warm_lead_nurture")
    return {
        "mautic_contact_id": mautic_id,
        "suggested_sequence": seq,
        "requires_approval": True,
        "message": "Confirm to trigger email sequence.",
    }


@router.post("/trigger-sequence/{lead_id}")
async def trigger_sequence(
    lead_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bridge = MauticBridge()
    success = bridge.trigger_sequence(data["mautic_contact_id"], data["sequence"])
    if success:
        db_bridge = DataBridge(db, _wid(current_user))
        await db_bridge.add_timeline_event(
            lead_id,
            "email_sequence_started",
            f"Email sequence: {data['sequence']}",
            metadata=data,
        )
    return {"success": success}


@router.post("/draft/{lead_id}")
async def generate_draft(
    lead_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        text(
            """
            SELECT l.*, c.full_name, c.email, c.company_name,
                   ca.intent, ca.qualification_category, ca.summary, ca.objections
            FROM leads l
            JOIN contacts c ON c.id = l.contact_id
            LEFT JOIN call_analysis ca ON ca.call_id = (
                SELECT id FROM calls
                WHERE lead_id = l.id
                ORDER BY created_at DESC
                LIMIT 1
            )
            WHERE l.id = :lid
            """
        ),
        {"lid": lead_id},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = dict(row._mapping)
    bridge = MauticBridge()
    draft = bridge.generate_email_draft(
        contact=lead,
        analysis={
            "qualification_category": lead.get("qualification_category"),
            "intent": lead.get("intent"),
            "objections": lead.get("objections") or [],
            "summary": lead.get("summary"),
        },
        purpose=(data or {}).get("purpose", "follow_up"),
    )
    return draft
