"""
Publishing Endpoints — direct publish control, connection validation, and status.

POST /api/v1/publishing/publish-now/{content_id}   — immediately publish a draft
POST /api/v1/publishing/validate-connection/{channel} — test channel credentials
GET  /api/v1/publishing/connections                — all channel connection statuses
GET  /api/v1/publishing/audit                      — recent audit log events
GET  /api/v1/publishing/summary                    — compact publish stats
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.store.content_queue_store import (
    get_draft,
    mark_post_published,
    mark_post_failed,
    schedule_post,
)
from app.core.store.audit_store import get_recent_events, get_publish_summary
from app.services.publishers import get_publisher, PUBLISHER_REGISTRY
from app.services.publishers.base import PublisherStatus

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_CHANNELS = list(PUBLISHER_REGISTRY.keys())


class PublishNowRequest(BaseModel):
    channel: str
    caption_override: Optional[str] = None


# ─── Validate Connection ──────────────────────────────────────────────────────

@router.post("/publishing/validate-connection/{channel}")
async def validate_connection(channel: str, user=Depends(get_current_user)):
    """
    Test whether credentials for a channel are valid and have required scopes.
    Used by the Connections page to show READY / INVALID / MISSING_SCOPES states.
    """
    try:
        publisher = get_publisher(channel, str(user.id))
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No publisher for channel '{channel}'")

    status = await publisher.check_status()
    return {
        "channel": channel,
        "status": status.value,
        "ready": status == PublisherStatus.READY,
        "message": _status_message(status, channel),
    }


@router.get("/publishing/connections")
async def get_all_connections(user=Depends(get_current_user)):
    """
    Return connection health for all supported channels in parallel.
    Used by the Connections page header and autonomy summary.
    """
    channels = ["x", "instagram", "tiktok"]  # channels with real publishers

    async def _check(ch: str):
        try:
            pub = get_publisher(ch, str(user.id))
            st = await pub.check_status()
            return {"channel": ch, "status": st.value, "ready": st == PublisherStatus.READY, "message": _status_message(st, ch)}
        except Exception as e:
            return {"channel": ch, "status": "unavailable", "ready": False, "message": str(e)}

    results = await asyncio.gather(*[_check(ch) for ch in channels])
    ready_count = sum(1 for r in results if r["ready"])
    return {
        "connections": list(results),
        "ready_count": ready_count,
        "total": len(channels),
    }


# ─── Publish Now ─────────────────────────────────────────────────────────────

@router.post("/publishing/publish-now/{draft_id}")
async def publish_now(
    draft_id: str,
    body: PublishNowRequest,
    user=Depends(get_current_user),
):
    """
    Immediately publish a content draft to the specified channel.
    Bypasses the scheduled queue — fires the publish call synchronously.
    Returns the publish result including platform post ID and URL.
    """
    draft = get_draft(draft_id)
    if not draft or draft.get("user_id") != str(user.id):
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.get("status") not in ("approved", "generated", "needs_review", "scheduled"):
        raise HTTPException(
            status_code=400,
            detail=f"Draft status '{draft.get('status')}' cannot be published. Must be approved or generated."
        )

    text = body.caption_override or draft.get("generated_text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text content to publish")

    try:
        publisher = get_publisher(body.channel, str(user.id))
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No publisher for channel '{body.channel}'")

    result = await publisher.publish_text_post(text)

    if result.success:
        # Create a scheduled post entry and mark it published immediately
        try:
            from datetime import datetime, timezone
            post_entry = schedule_post(
                draft_id=draft_id,
                user_id=str(user.id),
                channel=body.channel,
                scheduled_at=datetime.now(timezone.utc).isoformat(),
                caption_override=body.caption_override,
            )
            if post_entry:
                mark_post_published(post_entry["id"], result.post_id or "")
        except Exception as e:
            logger.debug("publish_now.queue_update_failed: %s", e)

        return {
            "success": True,
            "channel": body.channel,
            "post_id": result.post_id,
            "post_url": result.post_url,
            "published_at": result.published_at,
        }
    else:
        return {
            "success": False,
            "channel": body.channel,
            "error": result.error,
            "rate_limited": result.rate_limited,
            "retry_after_seconds": result.retry_after_seconds,
        }


# ─── Audit Log ───────────────────────────────────────────────────────────────

@router.get("/publishing/audit")
async def get_audit_log(
    limit: int = 50,
    channel: Optional[str] = None,
    action_prefix: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Return recent audit events for the current user, newest first."""
    events = get_recent_events(
        user_id=str(user.id),
        limit=min(limit, 200),
        action_prefix=action_prefix,
        channel=channel,
    )
    return {"events": events, "count": len(events)}


@router.get("/publishing/summary")
async def get_publishing_summary(user=Depends(get_current_user)):
    """Return compact publish stats by channel."""
    summary = get_publish_summary(str(user.id))
    return summary


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _status_message(status: PublisherStatus, channel: str) -> str:
    messages = {
        PublisherStatus.READY: f"{channel.title()} is connected and ready to publish.",
        PublisherStatus.NO_CREDENTIALS: f"No {channel.title()} credentials found. Connect your account in Connections.",
        PublisherStatus.INVALID_CREDENTIALS: f"{channel.title()} credentials are invalid or expired. Reconnect your account.",
        PublisherStatus.MISSING_SCOPES: f"{channel.title()} token is missing required publishing scopes. Reconnect with full permissions.",
        PublisherStatus.RATE_LIMITED: f"{channel.title()} is currently rate-limiting requests. Try again in a few minutes.",
        PublisherStatus.UNAVAILABLE: f"{channel.title()} API is unreachable. Check your connection and try again.",
        PublisherStatus.NOT_IMPLEMENTED: f"{channel.title()} publisher is not yet available.",
    }
    return messages.get(status, "Unknown status.")
