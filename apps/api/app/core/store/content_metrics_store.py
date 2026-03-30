"""
Content Metrics Store — post performance data from publisher APIs.

Stores engagement metrics (likes, views, reach, etc.) per published post.
These feed the learning loop: high/low performers inform future content strategy.

Structure: storage/content_metrics.json
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "content_metrics.json"


def _load() -> dict:
    if not STORE_PATH.exists():
        return {"snapshots": [], "aggregates": {}}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"snapshots": [], "aggregates": {}}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def record_post_metrics(
    user_id: str,
    draft_id: str,
    scheduled_post_id: str,
    channel: str,
    platform_post_id: str,
    metrics: dict,
    post_text: Optional[str] = None,
    topic: Optional[str] = None,
    content_type: Optional[str] = None,
) -> dict:
    """
    Record a performance snapshot for a published post.

    metrics dict may contain any subset of:
      impressions, reach, likes, comments, shares, saves,
      views, plays, profile_visits, link_clicks, bookmarks
    """
    data = _load()
    now = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "draft_id": draft_id,
        "scheduled_post_id": scheduled_post_id,
        "channel": channel,
        "platform_post_id": platform_post_id,
        "post_text": (post_text or "")[:300],
        "topic": topic or "",
        "content_type": content_type or "text_post",
        "metrics": {
            "impressions": metrics.get("impressions", 0),
            "reach": metrics.get("reach", 0),
            "likes": metrics.get("likes", 0),
            "comments": metrics.get("comments", 0),
            "shares": metrics.get("shares", 0),
            "saves": metrics.get("saves", 0),
            "views": metrics.get("views", 0),
            "plays": metrics.get("plays", 0),
            "profile_visits": metrics.get("profile_visits", 0),
            "link_clicks": metrics.get("link_clicks", 0),
            "bookmarks": metrics.get("bookmarks", 0),
        },
        "engagement_score": _compute_engagement_score(metrics),
        "recorded_at": now,
    }

    data["snapshots"].append(snapshot)

    # Update per-channel aggregate
    ch_agg = data["aggregates"].setdefault(channel, {
        "total_posts": 0,
        "total_impressions": 0,
        "total_likes": 0,
        "total_comments": 0,
        "total_shares": 0,
        "total_profile_visits": 0,
        "total_link_clicks": 0,
        "avg_engagement_score": 0.0,
        "best_post_id": None,
        "best_post_score": 0.0,
    })
    ch_agg["total_posts"] += 1
    ch_agg["total_impressions"] += metrics.get("impressions", 0)
    ch_agg["total_likes"] += metrics.get("likes", 0)
    ch_agg["total_comments"] += metrics.get("comments", 0)
    ch_agg["total_shares"] += metrics.get("shares", 0)
    ch_agg["total_profile_visits"] += metrics.get("profile_visits", 0)
    ch_agg["total_link_clicks"] += metrics.get("link_clicks", 0)

    # Rolling avg engagement score
    prev_avg = ch_agg["avg_engagement_score"]
    n = ch_agg["total_posts"]
    ch_agg["avg_engagement_score"] = round(
        (prev_avg * (n - 1) + snapshot["engagement_score"]) / n, 4
    )
    if snapshot["engagement_score"] > ch_agg["best_post_score"]:
        ch_agg["best_post_score"] = snapshot["engagement_score"]
        ch_agg["best_post_id"] = scheduled_post_id

    _save(data)
    return snapshot


def _compute_engagement_score(metrics: dict) -> float:
    """
    Composite engagement score normalized to [0, 1].
    Weighted: likes 30%, comments 25%, shares 20%, saves 15%, link_clicks 10%.
    Uses tanh normalization to handle outliers.
    """
    from math import tanh
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", 0)
    clicks = metrics.get("link_clicks", 0)

    score = (
        tanh(likes / 100) * 0.30
        + tanh(comments / 20) * 0.25
        + tanh(shares / 30) * 0.20
        + tanh(saves / 20) * 0.15
        + tanh(clicks / 50) * 0.10
    )
    return round(score, 4)


def get_post_metrics(scheduled_post_id: str, user_id: str) -> Optional[dict]:
    """Return the most recent metrics snapshot for a specific post."""
    data = _load()
    matches = [
        s for s in data["snapshots"]
        if s["scheduled_post_id"] == scheduled_post_id and s["user_id"] == user_id
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda x: x["recorded_at"], reverse=True)[0]


def get_channel_metrics(user_id: str, channel: str, limit: int = 20) -> list[dict]:
    """Return recent metrics snapshots for a channel, newest first."""
    data = _load()
    matches = [
        s for s in data["snapshots"]
        if s["user_id"] == user_id and s["channel"] == channel
    ]
    return sorted(matches, key=lambda x: x["recorded_at"], reverse=True)[:limit]


def get_top_performers(user_id: str, channel: Optional[str] = None, limit: int = 5) -> list[dict]:
    """Return top performing posts by engagement score."""
    data = _load()
    matches = [s for s in data["snapshots"] if s["user_id"] == user_id]
    if channel:
        matches = [s for s in matches if s["channel"] == channel]
    return sorted(matches, key=lambda x: x["engagement_score"], reverse=True)[:limit]


def get_performance_summary(user_id: str) -> dict:
    """Return aggregate performance stats across all channels."""
    data = _load()
    user_snapshots = [s for s in data["snapshots"] if s["user_id"] == user_id]

    if not user_snapshots:
        return {
            "total_posts_measured": 0,
            "avg_engagement_score": 0.0,
            "best_channel": None,
            "by_channel": {},
            "top_performers": [],
        }

    by_channel: dict[str, dict] = {}
    for snap in user_snapshots:
        ch = snap["channel"]
        if ch not in by_channel:
            by_channel[ch] = {"posts": 0, "total_score": 0.0, "total_impressions": 0}
        by_channel[ch]["posts"] += 1
        by_channel[ch]["total_score"] += snap["engagement_score"]
        by_channel[ch]["total_impressions"] += snap["metrics"].get("impressions", 0)

    for ch, stats in by_channel.items():
        stats["avg_score"] = round(stats["total_score"] / stats["posts"], 4)

    best_channel = max(by_channel.items(), key=lambda kv: kv[1]["avg_score"])[0] if by_channel else None

    return {
        "total_posts_measured": len(user_snapshots),
        "avg_engagement_score": round(
            sum(s["engagement_score"] for s in user_snapshots) / len(user_snapshots), 4
        ),
        "best_channel": best_channel,
        "by_channel": by_channel,
        "top_performers": get_top_performers(user_id, limit=3),
    }
