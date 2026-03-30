"""
Growth Metrics Store — account-level follower timeseries + ad campaign tracking.

Stores:
  - Follower count snapshots (per user, per channel) — append-only timeseries
  - Ad campaign records (launch + performance history)
  - Ads optimization recommendations

Timeseries design: each snapshot is one row. Query with date window to get delta.
In production: migrate to TimescaleDB or InfluxDB hypertable.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "growth_metrics_store.json"

_DEFAULT: dict = {
    "follower_snapshots": [],      # {id, user_id, channel, follower_count, ts}
    "ad_campaigns": [],            # {id, user_id, platform, campaign_id, name, status, ...}
    "ad_performance_snapshots": [], # {id, campaign_record_id, ts, impressions, clicks, spend, ...}
    "optimization_recommendations": [], # {id, user_id, campaign_record_id, suggestion, ...}
}


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        data = {k: list(v) for k, v in _DEFAULT.items()}
        _save(data)
        return data
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
        for k, v in _DEFAULT.items():
            if k not in data:
                data[k] = list(v)
        return data
    except (json.JSONDecodeError, OSError):
        return {k: list(v) for k, v in _DEFAULT.items()}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Follower Timeseries ───────────────────────────────────────────────────────

def append_follower_snapshot(
    user_id: str,
    channel: str,
    follower_count: int,
    extra: Optional[dict] = None,
) -> dict:
    """Record a follower count snapshot. Call this on schedule (e.g. every 6h)."""
    snap = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": channel,
        "follower_count": follower_count,
        "extra": extra or {},   # e.g. {"following": 500, "tweet_count": 120}
        "ts": _now(),
    }
    data = _load()
    data["follower_snapshots"].append(snap)
    _save(data)
    return snap


def get_follower_history(
    user_id: str,
    channel: str,
    days: int = 30,
) -> list[dict]:
    """Return follower snapshots for the last N days, oldest first."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = _load()
    snaps = [
        s for s in data["follower_snapshots"]
        if s["user_id"] == user_id
        and s["channel"] == channel
        and s["ts"] >= cutoff
    ]
    return sorted(snaps, key=lambda x: x["ts"])


def get_latest_follower_count(user_id: str, channel: str) -> Optional[int]:
    """Return the most recent follower count for this user+channel, or None."""
    data = _load()
    snaps = [
        s for s in data["follower_snapshots"]
        if s["user_id"] == user_id and s["channel"] == channel
    ]
    if not snaps:
        return None
    latest = max(snaps, key=lambda x: x["ts"])
    return latest["follower_count"]


def get_follower_delta(user_id: str, channel: str, days: int = 7) -> Optional[int]:
    """Return follower gain/loss over the last N days. None if no data."""
    history = get_follower_history(user_id, channel, days=days)
    if len(history) < 2:
        return None
    return history[-1]["follower_count"] - history[0]["follower_count"]


# ── Ad Campaign Records ───────────────────────────────────────────────────────

def register_ad_campaign(
    user_id: str,
    platform: str,              # "meta" | "google"
    campaign_id: str,           # Platform campaign ID
    name: str,
    objective: str,
    daily_budget_usd: float,
    landing_page_url: str,
    ad_set_id: Optional[str] = None,
    ad_group_id: Optional[str] = None,
    ad_id: Optional[str] = None,
) -> dict:
    """Register a newly launched ad campaign for performance tracking."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "campaign_id": campaign_id,
        "name": name,
        "objective": objective,
        "daily_budget_usd": daily_budget_usd,
        "landing_page_url": landing_page_url,
        "ad_set_id": ad_set_id,
        "ad_group_id": ad_group_id,
        "ad_id": ad_id,
        "status": "paused",   # paused | active | optimizing | paused_poor_performance
        "launched_at": _now(),
        "last_checked_at": None,
        "total_spend_usd": 0.0,
        "total_impressions": 0,
        "total_clicks": 0,
        "avg_ctr": 0.0,
        "avg_cpc": 0.0,
    }
    data = _load()
    data["ad_campaigns"].append(record)
    _save(data)
    return record


def get_active_ad_campaigns(user_id: str) -> list[dict]:
    """Return campaigns with status 'active' or 'optimizing'."""
    data = _load()
    return [
        c for c in data["ad_campaigns"]
        if c["user_id"] == user_id and c["status"] in ("active", "optimizing")
    ]


def get_all_ad_campaigns(user_id: str) -> list[dict]:
    data = _load()
    return [c for c in data["ad_campaigns"] if c["user_id"] == user_id]


def update_campaign_status(record_id: str, status: str) -> None:
    data = _load()
    for c in data["ad_campaigns"]:
        if c["id"] == record_id:
            c["status"] = status
            c["last_checked_at"] = _now()
            break
    _save(data)


# ── Ad Performance Snapshots ─────────────────────────────────────────────────

def append_ad_performance_snapshot(
    campaign_record_id: str,
    user_id: str,
    platform: str,
    metrics: dict,
) -> dict:
    """
    Record a performance snapshot for an ad campaign.
    metrics dict: impressions, clicks, spend_usd, cpc, ctr, conversions, reach
    """
    snap = {
        "id": str(uuid.uuid4()),
        "campaign_record_id": campaign_record_id,
        "user_id": user_id,
        "platform": platform,
        "ts": _now(),
        "impressions": metrics.get("impressions", 0),
        "clicks": metrics.get("clicks", 0),
        "spend_usd": metrics.get("spend_usd", 0.0),
        "cpc": metrics.get("cpc", 0.0),
        "ctr": metrics.get("ctr", 0.0),
        "conversions": metrics.get("conversions", 0),
        "reach": metrics.get("reach", 0),
        "cost_per_conversion": (
            metrics.get("spend_usd", 0) / metrics.get("conversions", 1)
            if metrics.get("conversions", 0) > 0
            else None
        ),
    }
    data = _load()
    data["ad_performance_snapshots"].append(snap)

    # Update campaign aggregate
    for c in data["ad_campaigns"]:
        if c["id"] == campaign_record_id:
            c["total_spend_usd"] = round(c.get("total_spend_usd", 0) + snap["spend_usd"], 4)
            c["total_impressions"] += snap["impressions"]
            c["total_clicks"] += snap["clicks"]
            c["last_checked_at"] = snap["ts"]
            if c["total_impressions"] > 0:
                c["avg_ctr"] = round(c["total_clicks"] / c["total_impressions"], 6)
            if c["total_clicks"] > 0:
                c["avg_cpc"] = round(c["total_spend_usd"] / c["total_clicks"], 4)
            break

    _save(data)
    return snap


def get_campaign_performance_history(campaign_record_id: str) -> list[dict]:
    data = _load()
    snaps = [
        s for s in data["ad_performance_snapshots"]
        if s["campaign_record_id"] == campaign_record_id
    ]
    return sorted(snaps, key=lambda x: x["ts"])


# ── Optimization Recommendations ─────────────────────────────────────────────

def add_optimization_recommendation(
    user_id: str,
    campaign_record_id: str,
    platform: str,
    issue: str,                 # e.g. "high_cpc", "low_ctr", "poor_conversion"
    suggestion: str,            # Human-readable recommendation
    action_type: str,           # "pause" | "budget_cut" | "budget_increase" | "new_creative" | "new_audience"
    urgency: str = "medium",    # "low" | "medium" | "high"
    metrics_snapshot: Optional[dict] = None,
) -> dict:
    rec = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "campaign_record_id": campaign_record_id,
        "platform": platform,
        "issue": issue,
        "suggestion": suggestion,
        "action_type": action_type,
        "urgency": urgency,
        "metrics_snapshot": metrics_snapshot or {},
        "status": "pending",    # pending | applied | dismissed
        "created_at": _now(),
        "applied_at": None,
    }
    data = _load()
    data["optimization_recommendations"].append(rec)
    _save(data)
    return rec


def get_pending_recommendations(user_id: str) -> list[dict]:
    data = _load()
    recs = [
        r for r in data["optimization_recommendations"]
        if r["user_id"] == user_id and r["status"] == "pending"
    ]
    return sorted(recs, key=lambda x: x["created_at"], reverse=True)


def dismiss_recommendation(rec_id: str) -> None:
    data = _load()
    for r in data["optimization_recommendations"]:
        if r["id"] == rec_id:
            r["status"] = "dismissed"
            break
    _save(data)
