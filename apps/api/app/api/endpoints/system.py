"""System health monitoring + platform event read endpoints."""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.automation.event_bus import EventBus

router = APIRouter(prefix="/api/v1/system", tags=["System"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


@router.get("/health")
async def system_health(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check health of all platform components."""
    status: dict = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        status["database"] = {"status": "ok"}
    except Exception as e:
        status["database"] = {"status": "error", "detail": str(e)[:100]}

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = {"status": "ok", "models": models}
    except Exception:
        status["ollama"] = {"status": "offline"}

    # n8n — try the configured URL first, fall back to localhost if DNS or
    # connection fails (common when N8N_URL is set to host.docker.internal but
    # the API is running on the host instead of inside docker-compose).
    n8n_urls = [
        os.getenv("N8N_URL", "http://localhost:5678"),
        "http://localhost:5678",
    ]
    status["n8n"] = {"status": "offline"}
    for url in n8n_urls:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{url}/healthz")
                if r.status_code == 200:
                    status["n8n"] = {"status": "ok"}
                    break
                status["n8n"] = {"status": "degraded"}
        except Exception:
            continue

    # Mautic — same fallback. Mautic returns 302 to /s/login on healthy boot,
    # so any 2xx/3xx counts as ok; 4xx/5xx is degraded.
    mautic_urls = [
        os.getenv("MAUTIC_URL", "http://localhost:8181"),
        "http://localhost:8181",
    ]
    status["mautic"] = {"status": "offline"}
    for url in mautic_urls:
        try:
            async with httpx.AsyncClient(timeout=3, follow_redirects=False) as c:
                r = await c.get(f"{url}/")
                if r.status_code < 400:
                    status["mautic"] = {"status": "ok"}
                    break
                status["mautic"] = {"status": "degraded"}
        except Exception:
            continue

    # Recent events (last hour)
    events_last_hour = 0
    try:
        r = await db.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM platform_events "
                "WHERE created_at > NOW() - INTERVAL '1 hour'"
            )
        )
        events_last_hour = int(r.fetchone()[0])
    except Exception:
        events_last_hour = 0

    overall = (
        "ok"
        if all(v.get("status") == "ok" for v in status.values() if isinstance(v, dict))
        else "degraded"
    )

    return {
        "overall": overall,
        "components": status,
        "events_last_hour": events_last_hour,
    }


@router.get("/events")
async def get_recent_events(
    event_type: str | None = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent platform events for monitoring."""
    bus = EventBus(db, _wid(current_user))
    events = await bus.get_recent_events(limit=limit, event_type=event_type)
    return {"events": events, "total": len(events)}
