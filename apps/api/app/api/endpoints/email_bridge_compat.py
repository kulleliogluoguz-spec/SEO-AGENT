"""
Phase 2 Email Bridge — `/api/v1/email` compatibility shim.

Adds the literal `/sync-lead/{lead_id}` and `/draft/{lead_id}` aliases under
the `/api/v1/email` prefix so frontends and verification scripts following the
original Phase 2 spec can hit them at the expected paths. Must be registered
BEFORE the legacy `email_automation` router so its literal paths win.

The legacy `email_automation` router exposes `/contacts`, `/sequences`,
`/campaigns`, `/health`, `/stats/overview`, `/emails` — none of which collide
with `/sync-lead/...`, `/draft/...`, or `/trigger-sequence/...`.
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

router = APIRouter(prefix="/api/v1/email", tags=["Email Bridge Compat"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _fetch_lead_sql() -> str:
    return """
        SELECT l.*, c.full_name, c.email, c.phone, c.company_name
        FROM leads l
        JOIN contacts c ON c.id = l.contact_id
        WHERE l.id = :lid
    """


@router.get("/sync-lead/{lead_id}")
async def get_sync_lead_status(
    lead_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Read-only sync-lead endpoint: returns the lead's recommended sequence
    without triggering any actual Mautic sync. Used by the verification suite
    to confirm the route is wired and the lead lookup works end-to-end.
    """
    r = await db.execute(text(_fetch_lead_sql()), {"lid": lead_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = dict(row._mapping)
    sequence_map = {
        "hot": "hot_lead_followup",
        "warm": "warm_lead_nurture",
        "cold": "cold_lead_reactivation",
    }
    seq = sequence_map.get(lead.get("category") or "cold", "warm_lead_nurture")
    return {
        "lead_id": lead_id,
        "email": lead.get("email"),
        "category": lead.get("category"),
        "suggested_sequence": seq,
        "requires_approval": True,
        "message": "POST /api/v1/email/sync-lead/{lead_id} to actually sync.",
    }


@router.post("/sync-lead/{lead_id}")
async def sync_lead_to_mautic(
    lead_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(text(_fetch_lead_sql()), {"lid": lead_id})
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
