"""AI Learning endpoints — feedback capture + learned preference summary."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.ai.memory_service import AIMemoryService

router = APIRouter(prefix="/api/v1/ai-learning", tags=["AI Learning"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


@router.get("/summary")
async def get_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AIMemoryService(_wid(current_user))
    return await svc.get_summary(db)


@router.post("/feedback")
async def record_feedback(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AIMemoryService(_wid(current_user))
    await svc.record_feedback(
        db,
        module=data["module"],
        recommendation=data["recommendation"],
        action=data["action"],
        modification=data.get("modification"),
    )
    return {"success": True}


@router.get("/preferences/{module}")
async def get_preferences(
    module: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AIMemoryService(_wid(current_user))
    return {"preferences": await svc.get_preferences(db, module)}
