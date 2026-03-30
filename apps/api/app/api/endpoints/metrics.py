"""
Content Metrics & Traffic Goals Endpoints.

POST /api/v1/metrics/posts/{post_id}        — record metrics for a published post
GET  /api/v1/metrics/posts/{post_id}        — get metrics for a post
GET  /api/v1/metrics/channel/{channel}      — recent metrics for a channel
GET  /api/v1/metrics/summary                — aggregate performance summary
GET  /api/v1/metrics/top-performers         — top performing posts
POST /api/v1/metrics/refresh/{post_id}      — pull live metrics from publisher API

POST /api/v1/traffic-goals                  — create/update a traffic goal
GET  /api/v1/traffic-goals                  — list traffic goals
POST /api/v1/traffic-goals/{id}/outcome     — record acquisition outcome
GET  /api/v1/traffic-goals/summary          — acquisition performance summary
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.store.content_metrics_store import (
    record_post_metrics,
    get_post_metrics,
    get_channel_metrics,
    get_top_performers,
    get_performance_summary,
)
from app.core.store.traffic_goals_store import (
    upsert_traffic_goal,
    get_traffic_goals,
    record_acquisition_outcome,
    get_acquisition_summary,
    VALID_GOAL_TYPES,
    VALID_CHANNELS,
)
from app.core.store.content_queue_store import list_scheduled_posts

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Schema ──────────────────────────────────────────────────────────────────

class PostMetricsInput(BaseModel):
    draft_id: str
    channel: str
    platform_post_id: str
    post_text: Optional[str] = None
    topic: Optional[str] = None
    content_type: Optional[str] = None
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    profile_visits: int = 0
    link_clicks: int = 0
    bookmarks: int = 0


class TrafficGoalInput(BaseModel):
    goal_type: str
    destination_url: str
    target_monthly: int
    channel: str = "all"
    destination_description: Optional[str] = None
    utm_source: Optional[str] = None


class AcquisitionOutcomeInput(BaseModel):
    channel: str
    count: int
    source_post_id: Optional[str] = None
    source_campaign_id: Optional[str] = None
    session_quality: Optional[float] = None


# ─── Metrics Endpoints ────────────────────────────────────────────────────────

@router.post("/metrics/posts/{post_id}")
async def record_metrics(
    post_id: str,
    body: PostMetricsInput,
    user=Depends(get_current_user),
):
    """Manually record performance metrics for a published post."""
    snapshot = record_post_metrics(
        user_id=str(user.id),
        draft_id=body.draft_id,
        scheduled_post_id=post_id,
        channel=body.channel,
        platform_post_id=body.platform_post_id,
        metrics={
            "impressions": body.impressions,
            "reach": body.reach,
            "likes": body.likes,
            "comments": body.comments,
            "shares": body.shares,
            "saves": body.saves,
            "views": body.views,
            "profile_visits": body.profile_visits,
            "link_clicks": body.link_clicks,
            "bookmarks": body.bookmarks,
        },
        post_text=body.post_text,
        topic=body.topic,
        content_type=body.content_type,
    )
    return {"snapshot": snapshot}


@router.get("/metrics/posts/{post_id}")
async def get_metrics(post_id: str, user=Depends(get_current_user)):
    """Get latest metrics snapshot for a specific post."""
    snapshot = get_post_metrics(post_id, str(user.id))
    if not snapshot:
        return {"snapshot": None, "has_metrics": False}
    return {"snapshot": snapshot, "has_metrics": True}


@router.post("/metrics/refresh/{post_id}")
async def refresh_metrics_from_publisher(
    post_id: str,
    user=Depends(get_current_user),
):
    """
    Pull live metrics from the publisher API for a post.
    Looks up the post in the content queue to find channel + platform_post_id.
    """
    from app.core.store.content_queue_store import list_scheduled_posts
    from app.services.publishers import get_publisher

    # Find the scheduled post record
    posts = list_scheduled_posts(str(user.id))
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    platform_id = post.get("platform_post_id", "")
    channel = post.get("channel", "")

    if not platform_id:
        raise HTTPException(status_code=400, detail="Post has no platform ID — metrics not yet available")

    try:
        publisher = get_publisher(channel, str(user.id))
        raw_metrics = await publisher.get_post_metrics(platform_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"No publisher for channel '{channel}'")

    if not raw_metrics:
        return {"snapshot": None, "message": "Publisher returned no metrics (may need time to accumulate)"}

    from app.core.store.content_queue_store import get_draft
    draft = get_draft(post.get("draft_id", ""))
    snapshot = record_post_metrics(
        user_id=str(user.id),
        draft_id=post.get("draft_id", ""),
        scheduled_post_id=post_id,
        channel=channel,
        platform_post_id=platform_id,
        metrics=raw_metrics,
        post_text=post.get("caption_override") or (draft.get("generated_text", "")[:200] if draft else ""),
        topic=draft.get("topic") if draft else None,
        content_type=draft.get("content_type") if draft else None,
    )

    return {"snapshot": snapshot, "refreshed_from_api": True}


@router.get("/metrics/channel/{channel}")
async def get_channel_perf(
    channel: str,
    limit: int = 20,
    user=Depends(get_current_user),
):
    """Return recent performance snapshots for a specific channel."""
    snapshots = get_channel_metrics(str(user.id), channel, limit=limit)
    return {"snapshots": snapshots, "count": len(snapshots), "channel": channel}


@router.get("/metrics/top-performers")
async def get_top_performing_posts(
    channel: Optional[str] = None,
    limit: int = 5,
    user=Depends(get_current_user),
):
    """Return top-performing posts by engagement score."""
    posts = get_top_performers(str(user.id), channel=channel, limit=limit)
    return {"posts": posts, "count": len(posts)}


@router.get("/metrics/summary")
async def get_metrics_summary(user=Depends(get_current_user)):
    """Return aggregate performance summary across all channels."""
    summary = get_performance_summary(str(user.id))
    return summary


# ─── Traffic Goals Endpoints ──────────────────────────────────────────────────

@router.post("/traffic-goals")
async def set_traffic_goal(body: TrafficGoalInput, user=Depends(get_current_user)):
    """Create or update a traffic/acquisition goal."""
    if body.goal_type not in VALID_GOAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid goal_type. Must be one of: {VALID_GOAL_TYPES}")
    if body.channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Invalid channel. Must be one of: {VALID_CHANNELS}")
    if body.target_monthly < 1:
        raise HTTPException(status_code=400, detail="target_monthly must be >= 1")

    goal = upsert_traffic_goal(
        user_id=str(user.id),
        goal_type=body.goal_type,
        destination_url=body.destination_url,
        target_monthly=body.target_monthly,
        channel=body.channel,
        destination_description=body.destination_description,
        utm_source=body.utm_source,
    )
    return {"goal": goal}


@router.get("/traffic-goals")
async def list_goals(user=Depends(get_current_user)):
    """Return all active traffic goals for the user."""
    goals = get_traffic_goals(str(user.id))
    return {"goals": goals, "count": len(goals)}


@router.post("/traffic-goals/{goal_id}/outcome")
async def record_outcome(
    goal_id: str,
    body: AcquisitionOutcomeInput,
    user=Depends(get_current_user),
):
    """Record an acquisition outcome for a goal."""
    goals = get_traffic_goals(str(user.id))
    goal = next((g for g in goals if g["id"] == goal_id), None)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    outcome = record_acquisition_outcome(
        user_id=str(user.id),
        goal_id=goal_id,
        channel=body.channel,
        count=body.count,
        source_post_id=body.source_post_id,
        source_campaign_id=body.source_campaign_id,
        session_quality=body.session_quality,
    )
    return {"outcome": outcome}


@router.get("/traffic-goals/summary")
async def acquisition_summary(user=Depends(get_current_user)):
    """Return acquisition performance summary for the dashboard."""
    summary = get_acquisition_summary(str(user.id))
    return summary
