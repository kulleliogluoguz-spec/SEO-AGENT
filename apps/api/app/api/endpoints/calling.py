"""
Phase 2 Calling Module — Postgres-backed calls, leads, contacts.

NOTE: prefix is `/api/v1/calling` to avoid colliding with the legacy
`/api/v1/calls` endpoint that uses JSON-file storage. The frontend pages
under `/dashboard/calls/*` consume this new module via the `calling` prefix.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.calling.call_engine import CallEngine
from app.services.calling.lead_qualifier import LeadQualifier
from app.services.calling.transcription_engine import TranscriptionEngine
from app.services.shared.data_bridge import DataBridge

router = APIRouter(prefix="/api/v1/calling", tags=["Calling"])
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
    search: Optional[str] = None,
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
    status: Optional[str] = None,
    category: Optional[str] = None,
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
    # Stringify nested values
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


# ─── CALLS ─────────────────────────────────────────────────────────────────
@router.post("/initiate")
async def initiate_call(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = CallEngine(db, _wid(current_user))
    return await engine.initiate_twilio_call(
        to_phone=data["to_phone"],
        from_phone=os.getenv("TWILIO_PHONE_NUMBER", ""),
        contact_id=data.get("contact_id"),
        lead_id=data.get("lead_id"),
    )


@router.post("/upload")
async def upload_call(
    file: UploadFile = File(...),
    contact_id: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    call_id = str(uuid.uuid4())
    suffix = Path(file.filename or "audio.wav").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    engine = CallEngine(db, _wid(current_user))
    result = await engine.upload_recording(call_id, tmp_path, contact_id=contact_id)
    if "error" not in result:
        background_tasks.add_task(
            _bg_process_upload, call_id, result["recording_path"]
        )
    return result


async def _bg_process_upload(call_id: str, recording_path: str) -> None:
    """Background pipeline: transcribe + qualify uploaded call."""
    from app.core.db.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            segments = await TranscriptionEngine().transcribe_call(call_id, recording_path, db)
            if segments:
                await LeadQualifier().analyze_call(call_id, segments, db)
    except Exception as e:
        logger.error("upload background processing failed for %s: %s", call_id, e)


@router.get("")
async def list_calls(
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = "WHERE ca.workspace_id=:wid"
    params: dict = {"wid": _wid(current_user)}
    if contact_id:
        where += " AND ca.contact_id=:cid"
        params["cid"] = contact_id
    if lead_id:
        where += " AND ca.lead_id=:lid"
        params["lid"] = lead_id
    r = await db.execute(
        text(
            f"""
            SELECT ca.*, c.full_name, c.company_name,
                   an.qualification_score, an.qualification_category,
                   an.summary, an.intent
            FROM calls ca
            LEFT JOIN contacts c ON c.id=ca.contact_id
            LEFT JOIN call_analysis an ON an.call_id=ca.id
            {where}
            ORDER BY ca.started_at DESC NULLS LAST, ca.created_at DESC
            LIMIT 50
            """
        ),
        params,
    )
    calls = [_row_to_dict(row) for row in r.fetchall()]
    return {"calls": calls, "total": len(calls)}


@router.get("/{call_id}/transcript")
async def get_transcript(
    call_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        text(
            "SELECT * FROM call_transcripts WHERE call_id=:cid ORDER BY start_time"
        ),
        {"cid": call_id},
    )
    segs = [_row_to_dict(row) for row in r.fetchall()]
    ar = await db.execute(
        text("SELECT * FROM call_analysis WHERE call_id=:cid"), {"cid": call_id}
    )
    row = ar.fetchone()
    return {
        "call_id": call_id,
        "segments": segs,
        "analysis": _row_to_dict(row),
    }


@router.post("/{call_id}/reanalyze")
async def reanalyze(
    call_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        text(
            "SELECT * FROM call_transcripts WHERE call_id=:cid ORDER BY start_time"
        ),
        {"cid": call_id},
    )
    segs = [_row_to_dict(row) for row in r.fetchall()]
    if not segs:
        raise HTTPException(404, "No transcript found")
    analysis = await LeadQualifier().analyze_call(call_id, segs, db)
    return {"analysis": analysis}


# ─── WEBHOOKS ──────────────────────────────────────────────────────────────
@router.get("/twiml/{call_id}")
async def get_twiml(call_id: str):
    engine = CallEngine(None, "")
    return Response(
        content=engine.get_twiml_response(call_id), media_type="application/xml"
    )


@router.post("/recording-webhook/{call_id}")
async def recording_webhook(
    call_id: str,
    background_tasks: BackgroundTasks,
    recording_url: str = "",
    recording_duration: int = 0,
    db: AsyncSession = Depends(get_db),
):
    engine = CallEngine(db, "")
    background_tasks.add_task(
        engine.handle_recording_webhook, call_id, recording_url, recording_duration
    )
    return {"status": "processing"}


@router.post("/status-webhook/{call_id}")
async def status_webhook(
    call_id: str,
    call_status: str = "",
    db: AsyncSession = Depends(get_db),
):
    status_map = {
        "completed": "completed",
        "no-answer": "missed",
        "busy": "missed",
        "failed": "failed",
        "canceled": "missed",
    }
    s = status_map.get(call_status, call_status)
    await db.execute(
        text("UPDATE calls SET status=:s WHERE id=:id"),
        {"s": s, "id": call_id},
    )
    await db.commit()
    return {"status": "updated"}
