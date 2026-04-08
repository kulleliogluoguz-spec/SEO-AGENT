"""
Phase 2 Calling — `/api/v1/calls` compatibility router.

Adds the literal `/contacts`, `/leads`, and `/livekit/token` sub-routes to
the `/api/v1/calls` prefix so that frontends and verification scripts
following the original Phase 2 spec see them at the expected paths. Must be
registered BEFORE the legacy `calls_router` so literal paths win against its
`/{call_id}` parameterized matcher.
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.shared.data_bridge import DataBridge

router = APIRouter(prefix="/api/v1/calls", tags=["Calling Compat"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out = {}
    for k, v in row._mapping.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


# ─── CONTACTS ──────────────────────────────────────────────────────────────
@router.get("/contacts")
async def list_contacts(
    search: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = "WHERE c.workspace_id=:wid"
    params: dict = {"wid": _wid(current_user)}
    if search:
        where += " AND (c.full_name ILIKE :s OR c.company_name ILIKE :s OR c.email ILIKE :s)"
        params["s"] = f"%{search}%"
    r = await db.execute(
        text(
            f"""
            SELECT c.*, l.status AS lead_status, l.qualification_score,
                   l.category, l.last_contact_date, l.ai_next_action, l.id AS lead_id
            FROM contacts c
            LEFT JOIN leads l ON l.contact_id=c.id AND l.workspace_id=c.workspace_id
            {where}
            ORDER BY l.qualification_score DESC NULLS LAST, c.created_at DESC
            LIMIT 100
            """
        ),
        params,
    )
    contacts = [_row_to_dict(row) for row in r.fetchall()]
    return {"contacts": contacts, "total": len(contacts)}


@router.post("/contacts")
async def create_contact(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bridge = DataBridge(db, _wid(current_user))
    contact = await bridge.get_or_create_contact(
        email=data.get("email"),
        phone=data.get("phone"),
        full_name=data.get("full_name"),
        company_name=data.get("company_name"),
        source="manual",
    )
    if contact and contact.get("id"):
        await bridge.get_or_create_lead(str(contact["id"]))
    return {"contact": contact}


# ─── LEADS ─────────────────────────────────────────────────────────────────
@router.get("/leads")
async def list_leads(
    status: str | None = None,
    category: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = "WHERE l.workspace_id=:wid"
    params: dict = {"wid": _wid(current_user)}
    if status:
        where += " AND l.status=:status"
        params["status"] = status
    if category:
        where += " AND l.category=:category"
        params["category"] = category
    r = await db.execute(
        text(
            f"""
            SELECT l.*, c.full_name, c.company_name, c.email, c.phone, c.industry,
                   (SELECT COUNT(*) FROM calls ca WHERE ca.lead_id=l.id) AS total_calls,
                   (SELECT MAX(started_at) FROM calls ca WHERE ca.lead_id=l.id) AS last_call
            FROM leads l
            JOIN contacts c ON c.id=l.contact_id
            {where}
            ORDER BY l.qualification_score DESC, l.updated_at DESC
            """
        ),
        params,
    )
    leads = [_row_to_dict(row) for row in r.fetchall()]
    return {"leads": leads, "total": len(leads)}


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bridge = DataBridge(db, _wid(current_user))
    profile = await bridge.get_lead_full_profile(lead_id)
    if not profile:
        raise HTTPException(404, "Lead not found")
    return {"lead": profile}


@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = [
        "status",
        "category",
        "notes",
        "next_follow_up_date",
        "estimated_deal_value",
        "qualification_score",
    ]
    parts, params = [], {"id": lead_id}
    for f in allowed:
        if f in data:
            parts.append(f"{f}=:{f}")
            params[f] = data[f]
    if not parts:
        raise HTTPException(400, "No valid fields")
    await db.execute(
        text(f"UPDATE leads SET {', '.join(parts)}, updated_at=NOW() WHERE id=:id"),
        params,
    )
    await db.commit()
    bridge = DataBridge(db, _wid(current_user))
    await bridge.add_timeline_event(
        lead_id, "manual_update", "Lead manually updated", metadata=data
    )
    return {"success": True}


# ─── LIVEKIT ───────────────────────────────────────────────────────────────
@router.get("/livekit/token")
@router.post("/livekit/token")
async def get_livekit_token(
    data: dict | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a LiveKit room token for browser-based calling.

    Both GET and POST are accepted:
    - GET returns a token for a freshly-minted call_id (useful for quick
      verification from curl / health checks).
    - POST accepts `{call_id?, contact_id?, identity?}` for a real call.
    """
    from app.services.calling.livekit_engine import LiveKitEngine

    data = data or {}
    call_id = data.get("call_id") or str(uuid.uuid4())
    contact_id = data.get("contact_id")
    identity = data.get("identity") or f"user_{getattr(current_user, 'id', 'demo')}"

    engine = LiveKitEngine()
    room_name = engine.create_room_name(call_id)
    token = engine.generate_token(room_name, identity)

    if not token:
        # Graceful degradation: return 200 with a message so the verification
        # script can tell "not configured" from "broken". A missing SDK or
        # missing credentials is expected in the dev/CI environment.
        return {
            "call_id": call_id,
            "room_name": room_name,
            "token": None,
            "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
            "configured": False,
            "message": (
                "LiveKit not configured. Install livekit-api and set "
                "LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env."
            ),
        }

    await db.execute(
        text(
            """
            INSERT INTO calls(
                id, workspace_id, contact_id, direction, status, provider, consent_given
            )
            VALUES(:id, :wid, :cid, 'outbound', 'active', 'livekit', true)
            ON CONFLICT(id) DO NOTHING
            """
        ),
        {"id": call_id, "wid": _wid(current_user), "cid": contact_id},
    )
    await db.commit()

    return {
        "call_id": call_id,
        "room_name": room_name,
        "token": token,
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
        "configured": True,
    }
