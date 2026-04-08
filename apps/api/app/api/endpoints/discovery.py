"""Company Intelligence Discovery — Adaptive AI Interview endpoints."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.discovery.discovery_engine import DiscoveryEngine

router = APIRouter(prefix="/api/v1/discovery", tags=["Discovery"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out: dict = {}
    for k, v in row._mapping.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


@router.get("/status")
async def get_discovery_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current discovery status for this workspace."""
    r = await db.execute(
        text("SELECT * FROM company_profiles WHERE workspace_id=:wid"),
        {"wid": _wid(current_user)},
    )
    row = r.fetchone()
    if not row:
        return {"status": "not_started", "profile": None, "question_count": 0}

    profile = _row_to_dict(row)
    return {
        "status": "completed" if profile.get("discovery_completed") else "in_progress",
        "profile": profile,
        "question_count": profile.get("question_count", 0),
    }


@router.post("/start")
async def start_discovery(
    data: dict | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start (or restart) the discovery process."""
    data = data or {}
    engine = DiscoveryEngine()
    first_question = engine.get_opening_question(data.get("business_type"))

    await db.execute(
        text(
            """
            INSERT INTO company_profiles
                (workspace_id, discovery_transcript, discovery_completed, question_count)
            VALUES (:wid, CAST(:transcript AS jsonb), false, 1)
            ON CONFLICT(workspace_id) DO UPDATE SET
                discovery_transcript = EXCLUDED.discovery_transcript,
                discovery_completed = false,
                question_count = 1,
                updated_at = NOW()
            """
        ),
        {
            "wid": _wid(current_user),
            "transcript": json.dumps(
                [{"role": "assistant", "content": first_question, "type": "question"}]
            ),
        },
    )
    await db.commit()
    return {"question": first_question, "question_number": 1}


@router.post("/answer")
async def submit_answer(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer and get the next question."""
    answer = (data or {}).get("answer", "").strip()
    if not answer:
        raise HTTPException(400, "Answer cannot be empty")

    r = await db.execute(
        text(
            "SELECT discovery_transcript, question_count FROM company_profiles "
            "WHERE workspace_id=:wid"
        ),
        {"wid": _wid(current_user)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Discovery not started. Call /start first.")

    mapping = row._mapping
    transcript = mapping.get("discovery_transcript") or []
    if not isinstance(transcript, list):
        transcript = []

    transcript.append({"role": "user", "content": answer, "type": "answer"})

    engine = DiscoveryEngine()
    knowledge = engine.extract_company_knowledge(transcript) or {}
    next_question = engine.generate_next_question(transcript, knowledge)
    completed = next_question == "[COMPLETE]"

    if not completed:
        transcript.append({"role": "assistant", "content": next_question, "type": "question"})

    q_count = len([t for t in transcript if t.get("role") == "assistant"])
    summary: str | None = None

    if completed:
        summary = engine.generate_company_summary(knowledge, transcript)
        await db.execute(
            text(
                """
                UPDATE company_profiles SET
                    discovery_transcript = CAST(:transcript AS jsonb),
                    discovery_completed = true,
                    discovery_completed_at = NOW(),
                    question_count = :qc,
                    ai_summary = :summary,
                    company_name = :company_name,
                    industry = :industry,
                    stage = :stage,
                    business_model = :bm,
                    primary_goal = :goal,
                    biggest_challenge = :challenge,
                    target_customer = :customer,
                    avg_order_value = :aov,
                    monthly_ad_spend = :spend,
                    current_roas = :roas,
                    break_even_roas = :be_roas,
                    active_channels = :channels,
                    updated_at = NOW()
                WHERE workspace_id = :wid
                """
            ),
            {
                "wid": _wid(current_user),
                "transcript": json.dumps(transcript),
                "qc": q_count,
                "summary": summary,
                "company_name": knowledge.get("company_name"),
                "industry": knowledge.get("industry"),
                "stage": knowledge.get("stage"),
                "bm": knowledge.get("business_model"),
                "goal": knowledge.get("primary_goal"),
                "challenge": knowledge.get("biggest_challenge"),
                "customer": knowledge.get("target_customer"),
                "aov": knowledge.get("avg_order_value"),
                "spend": knowledge.get("monthly_ad_spend"),
                "roas": knowledge.get("current_roas"),
                "be_roas": knowledge.get("break_even_roas"),
                "channels": knowledge.get("active_channels") or [],
            },
        )
    else:
        await db.execute(
            text(
                """
                UPDATE company_profiles SET
                    discovery_transcript = CAST(:transcript AS jsonb),
                    question_count = :qc,
                    updated_at = NOW()
                WHERE workspace_id = :wid
                """
            ),
            {
                "wid": _wid(current_user),
                "transcript": json.dumps(transcript),
                "qc": q_count,
            },
        )
    await db.commit()

    return {
        "completed": completed,
        "next_question": None if completed else next_question,
        "question_number": q_count,
        "profile": knowledge if completed else None,
        "summary": summary if completed else None,
    }


@router.get("/profile")
async def get_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the completed company profile."""
    r = await db.execute(
        text("SELECT * FROM company_profiles WHERE workspace_id=:wid"),
        {"wid": _wid(current_user)},
    )
    row = r.fetchone()
    if not row:
        return {"profile": None}
    return {"profile": _row_to_dict(row)}
