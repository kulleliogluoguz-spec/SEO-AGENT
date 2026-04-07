"""
Growth Experiment Store — persistent storage for X/Twitter account growth tests.

A GrowthExperiment tracks:
  - The connected X account (user_id, x_username)
  - The niche, growth goal, autonomy mode
  - Generated content drafts assigned to this experiment
  - Performance snapshot: followers_at_start, current_followers, posts_published

Structure: storage/growth_experiments.json (JSON list)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

STORE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "storage" / "growth_experiments.json"
)

VALID_GOALS = [
    "followers",
    "profile_visits",
    "website_clicks",
    "signups",
    "leads",
    "traffic",
]

VALID_POSTING_MODES = ["review", "auto_schedule", "auto_publish"]
VALID_AD_MODES = ["off", "boost_best", "full_auto"]
VALID_STAGES = ["setup", "active", "paused", "completed"]


def _load() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(experiments: list[dict]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(experiments, f, indent=2)


def create_experiment(
    user_id: str,
    niche: str,
    goal: str,
    posting_mode: str,
    ad_mode: str = "off",
    x_username: str | None = None,
    brand_voice: str | None = None,
    target_audience: str | None = None,
    content_themes: list[str] | None = None,
    daily_post_target: int = 3,
    followers_at_start: int = 0,
    website_url: str | None = None,
) -> dict:
    """Create a new X account growth experiment."""
    experiments = _load()

    experiment = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": "x",
        "niche": niche,
        "goal": goal,
        "posting_mode": posting_mode,
        "ad_mode": ad_mode,
        "x_username": x_username,
        "brand_voice": brand_voice or "professional and engaging",
        "target_audience": target_audience or "",
        "content_themes": content_themes or [],
        "daily_post_target": daily_post_target,
        "followers_at_start": followers_at_start,
        "current_followers": followers_at_start,
        "posts_published": 0,
        "posts_drafted": 0,
        "website_url": website_url,
        "stage": "active",
        "growth_strategy": None,  # populated by strategy generation
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "last_post_at": None,
        "performance_snapshots": [],  # [{date, followers, posts_published}]
    }

    experiments.append(experiment)
    _save(experiments)
    return experiment


def get_experiment(experiment_id: str, user_id: str) -> dict | None:
    """Return a specific experiment by ID."""
    for exp in _load():
        if exp["id"] == experiment_id and exp["user_id"] == user_id:
            return exp
    return None


def get_user_experiments(user_id: str, channel: str = "x") -> list[dict]:
    """Return all experiments for a user on a given channel."""
    return [exp for exp in _load() if exp["user_id"] == user_id and exp.get("channel") == channel]


def get_active_experiment(user_id: str) -> dict | None:
    """Return the most recent active X experiment for a user."""
    experiments = [
        exp for exp in _load() if exp["user_id"] == user_id and exp.get("stage") == "active"
    ]
    if not experiments:
        return None
    return sorted(experiments, key=lambda e: e.get("created_at", ""), reverse=True)[0]


def update_experiment(experiment_id: str, user_id: str, updates: dict) -> dict | None:
    """Update fields on an experiment."""
    experiments = _load()
    for i, exp in enumerate(experiments):
        if exp["id"] == experiment_id and exp["user_id"] == user_id:
            experiments[i].update(updates)
            experiments[i]["updated_at"] = datetime.now(UTC).isoformat()
            _save(experiments)
            return experiments[i]
    return None


def record_performance_snapshot(
    experiment_id: str,
    user_id: str,
    current_followers: int,
    posts_published: int,
) -> dict | None:
    """Append a performance snapshot and update current stats."""
    experiments = _load()
    for i, exp in enumerate(experiments):
        if exp["id"] == experiment_id and exp["user_id"] == user_id:
            snapshot = {
                "date": datetime.now(UTC).isoformat(),
                "followers": current_followers,
                "posts_published": posts_published,
                "follower_delta": current_followers - exp.get("followers_at_start", 0),
            }
            experiments[i]["performance_snapshots"].append(snapshot)
            experiments[i]["current_followers"] = current_followers
            experiments[i]["posts_published"] = posts_published
            experiments[i]["updated_at"] = datetime.now(UTC).isoformat()
            _save(experiments)
            return experiments[i]
    return None


def set_experiment_stage(
    experiment_id: str,
    user_id: str,
    stage: str,
) -> dict | None:
    """Transition experiment to a new stage (active/paused/completed)."""
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid stage: {stage}")
    return update_experiment(experiment_id, user_id, {"stage": stage})
