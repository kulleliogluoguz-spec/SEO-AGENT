"""
Content Queue API endpoints — lifecycle management for content drafts and scheduled posts.

Routes:
  GET  /api/v1/content-queue/drafts             — list drafts by status/type
  POST /api/v1/content-queue/drafts             — save a generated draft
  GET  /api/v1/content-queue/drafts/{id}        — get single draft
  POST /api/v1/content-queue/drafts/{id}/approve
  POST /api/v1/content-queue/drafts/{id}/reject
  POST /api/v1/content-queue/drafts/{id}/schedule  — schedule for a channel
  GET  /api/v1/content-queue/scheduled          — list scheduled posts
  POST /api/v1/content-queue/drafts/{id}/archive
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.core.store.content_queue_store import (
    create_draft,
    get_draft,
    list_drafts,
    list_scheduled_posts,
    schedule_post,
    transition_status,
    update_draft_text,
)
from app.core.store.autonomy_store import is_auto_publish_allowed

router = APIRouter(prefix="/content-queue", tags=["content-queue"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class DraftCreate(BaseModel):
    title: str
    content_type: str
    topic: str
    generated_text: str
    niche: Optional[str] = None
    trend_keyword: Optional[str] = None
    objective: Optional[str] = None
    channels: Optional[list[str]] = None


class ScheduleRequest(BaseModel):
    channel: str
    scheduled_at: str = Field(..., description="ISO 8601 datetime, e.g. 2025-04-01T14:00:00Z")
    caption_override: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/drafts")
async def list_content_drafts(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
) -> dict:
    """List content drafts for the current user, optionally filtered by status or type."""
    drafts = list_drafts(str(current_user.id), status=status, content_type=content_type, limit=limit)
    # Group by status for summary
    status_counts: dict[str, int] = {}
    for d in drafts:
        s = d.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    return {
        "drafts": drafts,
        "total": len(drafts),
        "status_counts": status_counts,
    }


@router.post("/drafts", status_code=201)
async def save_draft(
    payload: DraftCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """Save a generated content draft to the queue."""
    draft = create_draft(
        user_id=str(current_user.id),
        title=payload.title,
        content_type=payload.content_type,
        topic=payload.topic,
        generated_text=payload.generated_text,
        niche=payload.niche,
        trend_keyword=payload.trend_keyword,
        objective=payload.objective,
        channels=payload.channels,
    )
    return {"draft": draft, "message": "Draft saved to queue."}


@router.get("/drafts/{draft_id}")
async def get_content_draft(
    draft_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Approve a draft — moves it from needs_review/generated to approved."""
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")

    current_status = draft.get("status")
    if current_status not in ("generated", "needs_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve draft in '{current_status}' status. Must be 'generated' or 'needs_review'.",
        )

    updated = transition_status(draft_id, "approved", actor=str(current_user.id))
    return {"draft": updated, "message": "Draft approved."}


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(
    draft_id: str,
    payload: RejectRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """Reject a draft — sends it back to needs_review with optional reason."""
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.get("status") in ("published", "archived"):
        raise HTTPException(status_code=400, detail=f"Cannot reject a {draft.get('status')} draft.")

    updated = transition_status(draft_id, "needs_review", actor=str(current_user.id), reason=payload.reason)
    return {"draft": updated, "message": "Draft sent back for revision."}


@router.post("/drafts/{draft_id}/schedule")
async def schedule_draft(
    draft_id: str,
    payload: ScheduleRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Schedule an approved draft for publishing on a channel.

    If auto-publish is enabled for the channel (autonomy policy), this will be
    picked up by the publish_sweep_job automatically. Otherwise, publishing
    requires manual confirmation.
    """
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.get("status") not in ("approved", "generated"):
        raise HTTPException(
            status_code=400,
            detail=f"Draft must be 'approved' before scheduling. Current: {draft.get('status')}",
        )

    # Check autonomy policy
    auto_ok = is_auto_publish_allowed(str(current_user.id), payload.channel)

    try:
        post = schedule_post(
            draft_id=draft_id,
            user_id=str(current_user.id),
            channel=payload.channel,
            scheduled_at=payload.scheduled_at,
            caption_override=payload.caption_override,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "scheduled_post": post,
        "auto_publish_enabled": auto_ok,
        "message": (
            f"Post scheduled for {payload.channel} at {payload.scheduled_at}. "
            + ("Will publish automatically." if auto_ok else "Awaiting manual publish confirmation.")
        ),
    }


@router.post("/drafts/{draft_id}/archive")
async def archive_draft(
    draft_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Archive a draft — removes it from the active queue."""
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")

    updated = transition_status(draft_id, "archived", actor=str(current_user.id))
    return {"draft": updated, "message": "Draft archived."}


@router.get("/scheduled")
async def list_scheduled(
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
) -> dict:
    """List scheduled posts for the current user."""
    posts = list_scheduled_posts(str(current_user.id), status=status)
    return {"posts": posts, "total": len(posts)}


@router.get("/summary")
async def queue_summary(current_user=Depends(get_current_user)) -> dict:
    """
    Compact summary of the content queue.
    Used by command center and Growth Engine.
    """
    from app.core.store.content_queue_store import _load
    data = _load()
    user_id = str(current_user.id)

    drafts = [d for d in data.get("content_drafts", []) if d.get("user_id") == user_id]
    posts = [p for p in data.get("scheduled_posts", []) if p.get("user_id") == user_id]

    counts = {s: 0 for s in ["generated", "needs_review", "approved", "scheduled", "publishing", "published", "failed", "archived"]}
    for d in drafts:
        counts[d.get("status", "generated")] = counts.get(d.get("status", "generated"), 0) + 1

    upcoming = [p for p in posts if p.get("status") == "scheduled"]
    upcoming.sort(key=lambda p: p.get("scheduled_at", ""))

    return {
        "draft_counts": counts,
        "total_drafts": len(drafts),
        "scheduled_upcoming": len(upcoming),
        "next_scheduled_at": upcoming[0].get("scheduled_at") if upcoming else None,
        "needs_action": counts.get("needs_review", 0) + counts.get("generated", 0),
    }
