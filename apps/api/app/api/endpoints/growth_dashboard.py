"""
Growth Dashboard API — real-time growth data for frontend charts.

Endpoints:
  GET /growth/dashboard/{channel}      — full dashboard payload for X or Instagram
  GET /growth/followers/{channel}      — follower timeseries (chart data)
  GET /growth/posts/performance        — post ranking by engagement score
  GET /growth/insights                 — what worked / what failed / what's next
  GET /growth/ads/summary              — ad campaign performance + recommendations
  POST /growth/ads/register            — register a launched campaign for tracking
  POST /growth/ads/recommendations/{id}/dismiss — dismiss a recommendation
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.store.growth_metrics_store import (
    get_follower_history,
    get_latest_follower_count,
    get_follower_delta,
    get_active_ad_campaigns,
    get_all_ad_campaigns,
    get_pending_recommendations,
    register_ad_campaign,
    dismiss_recommendation,
    get_campaign_performance_history,
)
from app.core.store.content_metrics_store import (
    get_channel_metrics,
    get_top_performers,
    get_performance_summary,
)
from app.core.store.learning_store import (
    get_learning_summary,
    get_suppressed_strategies,
    get_promoted_strategies,
)
from app.core.store.growth_experiment_store import get_active_experiment, create_experiment

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Follower Timeseries ──────────────────────────────────────────────────────

@router.get("/growth/followers/{channel}")
async def get_follower_timeseries(
    channel: Literal["x", "instagram"],
    days: int = Query(default=30, ge=1, le=90),
    user=Depends(get_current_user),
):
    """
    Return follower count timeseries for chart rendering.
    Points: [{ts, follower_count}, ...]  oldest first.
    """
    user_id = str(user.id)
    history = get_follower_history(user_id, channel, days=days)
    current = get_latest_follower_count(user_id, channel)
    delta_7d = get_follower_delta(user_id, channel, days=7)
    delta_30d = get_follower_delta(user_id, channel, days=30)

    return {
        "channel": channel,
        "current_followers": current,
        "delta_7d": delta_7d,
        "delta_30d": delta_30d,
        "points": [
            {"ts": s["ts"], "count": s["follower_count"]}
            for s in history
        ],
        "has_data": len(history) > 0,
    }


# ─── Post Performance ─────────────────────────────────────────────────────────

@router.get("/growth/posts/performance")
async def get_post_performance(
    channel: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user=Depends(get_current_user),
):
    """
    Return post performance metrics ranked by engagement score.
    Used for "what worked / what failed" display.
    """
    user_id = str(user.id)
    snapshots = get_channel_metrics(user_id, channel or "x", limit=limit) if channel else []

    if not channel:
        # Return top performers across all channels
        top = get_top_performers(user_id, limit=limit)
        bottom = sorted(
            [s for s in get_channel_metrics(user_id, "x", limit=50)],
            key=lambda x: x["engagement_score"],
        )[:5]
        return {
            "top_performers": top,
            "worst_performers": bottom,
            "total_measured": len(top) + len(bottom),
        }

    sorted_by_score = sorted(snapshots, key=lambda x: x["engagement_score"], reverse=True)
    top = sorted_by_score[:5]
    worst = sorted_by_score[-5:] if len(sorted_by_score) >= 5 else []

    return {
        "channel": channel,
        "top_performers": top,
        "worst_performers": worst,
        "all_posts": snapshots,
        "avg_engagement_score": (
            round(sum(s["engagement_score"] for s in snapshots) / len(snapshots), 4)
            if snapshots else 0.0
        ),
    }


# ─── Learning Insights ────────────────────────────────────────────────────────

@router.get("/growth/insights")
async def get_growth_insights(
    niche: Optional[str] = Query(default=None),
    user=Depends(get_current_user),
):
    """
    Return learning insights: what worked, what failed, what to try next.
    Synthesizes data from:
      - content_metrics_store (post engagement)
      - learning_store (strategy outcomes, suppressed/promoted patterns)
      - growth_experiment_store (current experiment state)
    """
    user_id = str(user.id)

    # Resolve niche from active experiment if not provided
    if not niche:
        exp = get_active_experiment(user_id)
        if exp:
            niche = exp.get("niche", "general")

    learning = get_learning_summary(user_id, niche=niche)
    suppressed = get_suppressed_strategies(niche=niche)
    promoted = get_promoted_strategies(niche=niche)
    perf = get_performance_summary(user_id)

    # Build "what to try next" based on promoted patterns and top performers
    what_next = _generate_next_actions(promoted, suppressed, perf, niche)

    return {
        "niche": niche,
        "what_worked": {
            "count": learning["total_successes"],
            "patterns": promoted[:3],
            "top_posts": perf.get("top_performers", [])[:3],
        },
        "what_failed": {
            "count": learning["total_failures"],
            "patterns": suppressed[:3],
        },
        "what_to_try_next": what_next,
        "overall": {
            "success_rate": learning.get("success_rate"),
            "total_measured": learning["total_measured"],
            "avg_engagement": perf.get("avg_engagement_score", 0.0),
            "best_channel": perf.get("best_channel"),
        },
    }


def _generate_next_actions(
    promoted: list[dict],
    suppressed: list[dict],
    perf: dict,
    niche: Optional[str],
) -> list[dict]:
    """Synthesize actionable next steps from learning data."""
    actions = []

    # Promoted patterns → double down
    for p in promoted[:2]:
        actions.append({
            "action": "double_down",
            "description": f"More {p['strategy_type']} content — {p['success_rate']:.0%} success rate",
            "evidence": p.get("note", ""),
            "priority": "high",
        })

    # Suppressed patterns → avoid
    for s in suppressed[:2]:
        actions.append({
            "action": "avoid",
            "description": f"Reduce {s['strategy_type']} content — {s['failure_rate']:.0%} failure rate",
            "evidence": s.get("note", ""),
            "priority": "medium",
        })

    # If no data yet, suggest starting actions
    if not actions:
        actions = [
            {
                "action": "start",
                "description": "Post your first batch of content and let the system measure engagement",
                "evidence": "No performance data yet — start posting to activate the learning loop",
                "priority": "high",
            },
            {
                "action": "experiment",
                "description": "Try different content types: educational, opinion, and engagement posts",
                "evidence": "Mix content formats to identify what resonates with your audience",
                "priority": "medium",
            },
        ]

    # If avg engagement is low, suggest hooks
    avg_score = perf.get("avg_engagement_score", 0.0)
    if avg_score < 0.05 and perf.get("total_posts_measured", 0) >= 5:
        actions.append({
            "action": "optimize_hooks",
            "description": "Engagement is below 5% — test stronger opening hooks",
            "evidence": f"Current avg engagement score: {avg_score:.2%}",
            "priority": "high",
        })

    return actions[:5]


# ─── Full Dashboard ───────────────────────────────────────────────────────────

@router.get("/growth/dashboard/{channel}")
async def get_growth_dashboard(
    channel: Literal["x", "instagram"],
    user=Depends(get_current_user),
):
    """
    Full dashboard payload for X or Instagram growth page.
    Single endpoint to minimize round trips.
    """
    user_id = str(user.id)

    # Follower data
    follower_history = get_follower_history(user_id, channel, days=30)
    current_followers = get_latest_follower_count(user_id, channel)
    delta_7d = get_follower_delta(user_id, channel, days=7)

    # Post performance
    recent_posts = get_channel_metrics(user_id, channel, limit=20)
    top_posts = get_top_performers(user_id, channel=channel, limit=5)
    worst_posts = sorted(recent_posts, key=lambda x: x["engagement_score"])[:3] if len(recent_posts) >= 3 else []

    # Active experiment — auto-create a default if none exists so Generate Posts works
    exp = get_active_experiment(user_id)
    if not exp:
        exp = create_experiment(
            user_id=user_id,
            niche="general",
            goal="followers",
            posting_mode="review",
        )
        logger.info("[growth_dashboard] auto-created default experiment for user=%s", user_id)
    niche = exp.get("niche", "general")

    # Learning
    learning = get_learning_summary(user_id, niche=niche)
    promoted = get_promoted_strategies(niche=niche)
    suppressed = get_suppressed_strategies(niche=niche)
    perf = get_performance_summary(user_id)
    what_next = _generate_next_actions(promoted, suppressed, perf, niche)

    return {
        "channel": channel,
        "followers": {
            "current": current_followers,
            "delta_7d": delta_7d,
            "chart": [{"ts": s["ts"], "count": s["follower_count"]} for s in follower_history],
            "has_data": len(follower_history) > 0,
        },
        "posts": {
            "total_measured": len(recent_posts),
            "avg_engagement": (
                round(sum(p["engagement_score"] for p in recent_posts) / len(recent_posts), 4)
                if recent_posts else 0.0
            ),
            "top": top_posts,
            "worst": worst_posts,
        },
        "learning": {
            "success_rate": learning.get("success_rate"),
            "total_measured": learning["total_measured"],
            "promoted_patterns": promoted[:3],
            "suppressed_patterns": suppressed[:3],
        },
        "next_actions": what_next,
        "experiment": {
            "id": exp["id"] if exp else None,
            "niche": niche,
            "stage": exp.get("stage") if exp else None,
            "posts_drafted": exp.get("posts_drafted", 0) if exp else 0,
        } if exp else None,
    }


# ─── Ads Summary ─────────────────────────────────────────────────────────────

@router.get("/growth/ads/summary")
async def get_ads_summary(user=Depends(get_current_user)):
    """Return active ad campaigns + optimization recommendations."""
    user_id = str(user.id)
    active = get_active_ad_campaigns(user_id)
    all_campaigns = get_all_ad_campaigns(user_id)
    recommendations = get_pending_recommendations(user_id)

    return {
        "active_campaigns": active,
        "all_campaigns": all_campaigns,
        "pending_recommendations": recommendations,
        "total_active": len(active),
        "total_campaigns": len(all_campaigns),
    }


class RegisterCampaignRequest(BaseModel):
    platform: str
    campaign_id: str
    name: str
    objective: str
    daily_budget_usd: float
    landing_page_url: str
    ad_set_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    ad_id: Optional[str] = None


@router.post("/growth/ads/register")
async def register_campaign(
    body: RegisterCampaignRequest,
    user=Depends(get_current_user),
):
    """Register a launched ad campaign for performance tracking."""
    record = register_ad_campaign(
        user_id=str(user.id),
        platform=body.platform,
        campaign_id=body.campaign_id,
        name=body.name,
        objective=body.objective,
        daily_budget_usd=body.daily_budget_usd,
        landing_page_url=body.landing_page_url,
        ad_set_id=body.ad_set_id,
        ad_group_id=body.ad_group_id,
        ad_id=body.ad_id,
    )
    return {"success": True, "record": record}


@router.post("/growth/ads/recommendations/{rec_id}/dismiss")
async def dismiss_rec(rec_id: str, user=Depends(get_current_user)):
    dismiss_recommendation(rec_id)
    return {"success": True}


@router.get("/growth/ads/campaigns/{record_id}/history")
async def get_campaign_history(record_id: str, user=Depends(get_current_user)):
    history = get_campaign_performance_history(record_id)
    return {"history": history, "count": len(history)}
