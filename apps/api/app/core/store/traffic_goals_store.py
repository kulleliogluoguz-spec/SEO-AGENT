"""
Traffic Goals Store — acquisition and traffic objective tracking.

Maps content/campaigns to destination pages and tracks acquisition outcomes.
Closes the gap between social activity and actual business results.

Structure: storage/traffic_goals.json
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "traffic_goals.json"

VALID_GOAL_TYPES = [
    "traffic",          # Maximize page visits
    "signups",          # Email/account signups
    "leads",            # Lead form completions
    "purchases",        # E-commerce conversions
    "engaged_sessions", # Quality sessions (>2 min)
    "followers",        # Social follower growth
    "profile_visits",   # Social profile visits
]

VALID_CHANNELS = ["x", "instagram", "tiktok", "meta_ads", "google_ads", "organic_search", "all"]


def _load() -> dict:
    if not STORE_PATH.exists():
        return {"goals": [], "outcomes": []}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"goals": [], "outcomes": []}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def upsert_traffic_goal(
    user_id: str,
    goal_type: str,
    destination_url: str,
    target_monthly: int,
    channel: str = "all",
    destination_description: Optional[str] = None,
    utm_source: Optional[str] = None,
) -> dict:
    """Create or update a traffic/acquisition goal."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()

    # Check for existing goal of same type+channel
    for i, goal in enumerate(data["goals"]):
        if goal["user_id"] == user_id and goal["goal_type"] == goal_type and goal["channel"] == channel:
            data["goals"][i].update({
                "destination_url": destination_url,
                "target_monthly": target_monthly,
                "destination_description": destination_description,
                "utm_source": utm_source,
                "updated_at": now,
            })
            _save(data)
            return data["goals"][i]

    goal = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "goal_type": goal_type,
        "destination_url": destination_url,
        "target_monthly": target_monthly,
        "channel": channel,
        "destination_description": destination_description or "",
        "utm_source": utm_source or "",
        "current_monthly": 0,
        "all_time_total": 0,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    data["goals"].append(goal)
    _save(data)
    return goal


def get_traffic_goals(user_id: str, active_only: bool = True) -> list[dict]:
    """Return traffic goals for a user."""
    data = _load()
    goals = [g for g in data["goals"] if g["user_id"] == user_id]
    if active_only:
        goals = [g for g in goals if g.get("active", True)]
    return sorted(goals, key=lambda g: g.get("created_at", ""), reverse=True)


def record_acquisition_outcome(
    user_id: str,
    goal_id: str,
    channel: str,
    count: int,
    source_post_id: Optional[str] = None,
    source_campaign_id: Optional[str] = None,
    session_quality: Optional[float] = None,
) -> dict:
    """Record an acquisition outcome (visit, signup, conversion, etc.)."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()

    outcome = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "goal_id": goal_id,
        "channel": channel,
        "count": count,
        "source_post_id": source_post_id,
        "source_campaign_id": source_campaign_id,
        "session_quality": session_quality,
        "recorded_at": now,
    }
    data["outcomes"].append(outcome)

    # Update goal current_monthly and all_time
    for goal in data["goals"]:
        if goal["id"] == goal_id and goal["user_id"] == user_id:
            goal["current_monthly"] = goal.get("current_monthly", 0) + count
            goal["all_time_total"] = goal.get("all_time_total", 0) + count
            break

    _save(data)
    return outcome


def get_acquisition_summary(user_id: str) -> dict:
    """Return acquisition performance summary."""
    data = _load()
    goals = [g for g in data["goals"] if g["user_id"] == user_id and g.get("active")]
    outcomes = [o for o in data["outcomes"] if o["user_id"] == user_id]

    total_all_time = sum(o["count"] for o in outcomes)
    by_channel: dict[str, int] = {}
    by_goal_type: dict[str, int] = {}
    for o in outcomes:
        by_channel[o["channel"]] = by_channel.get(o["channel"], 0) + o["count"]

    for goal in goals:
        by_goal_type[goal["goal_type"]] = by_goal_type.get(goal["goal_type"], 0) + goal.get("current_monthly", 0)

    progress = []
    for goal in goals:
        pct = round(goal.get("current_monthly", 0) / max(goal["target_monthly"], 1) * 100, 1)
        progress.append({
            "goal_type": goal["goal_type"],
            "destination_url": goal["destination_url"],
            "channel": goal["channel"],
            "current": goal.get("current_monthly", 0),
            "target": goal["target_monthly"],
            "progress_pct": pct,
            "on_track": pct >= 66,  # rough 2/3 of target
        })

    return {
        "total_all_time": total_all_time,
        "by_channel": by_channel,
        "by_goal_type": by_goal_type,
        "goal_progress": progress,
        "active_goals": len(goals),
    }
