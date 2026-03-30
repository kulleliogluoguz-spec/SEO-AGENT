"""
Autonomy Policy Store — file-backed, per-user per-channel.

An AutomationPolicy defines how much the system can act autonomously on behalf of
a user for a given channel (instagram, tiktok, meta_ads, google_ads, etc.).

Enforcement contract:
  - autonomy_mode: manual | assisted | semi_auto | autonomous
  - content_auto_publish: bool — may the system publish content without approval?
  - ads_auto_launch: bool — may the system launch paid campaigns without approval?
  - max_daily_posts: int — hard cap on auto-published posts per day per channel
  - max_daily_spend_usd: float — hard cap on auto-spend per day
  - reallocation_cap_pct: int — max % budget shift in one reallocation
  - approval_threshold_usd: float — require approval for budget changes above this
  - kill_switch: bool — emergency stop; overrides all auto-behaviors

These policies are enforced at the API layer (campaigns, content publish endpoints).
The frontend reads them to render the correct UI state.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "autonomy_store.json"

_DEFAULT: dict = {"policies": []}

CHANNELS = [
    "instagram", "tiktok", "x", "youtube",
    "meta_ads", "google_ads", "tiktok_ads",
    "linkedin_ads", "pinterest_ads",
]


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        return _DEFAULT
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _DEFAULT


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _default_policy(user_id: str, channel: str) -> dict:
    """Return a safe default policy (full manual, no auto-actions)."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": channel,
        "autonomy_mode": "manual",
        "content_auto_publish": False,
        "ads_auto_launch": False,
        "max_daily_posts": 3,
        "max_daily_spend_usd": 0.0,
        "reallocation_cap_pct": 0,
        "approval_threshold_usd": 50.0,
        "quiet_hours_start": None,   # "22:00" local time
        "quiet_hours_end": None,     # "07:00" local time
        "kill_switch": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_policy(user_id: str, channel: str) -> dict:
    """Return policy for a channel, creating default if not set."""
    data = _load()
    for p in data.get("policies", []):
        if p.get("user_id") == user_id and p.get("channel") == channel:
            return p
    return _default_policy(user_id, channel)


def get_all_policies(user_id: str) -> list[dict]:
    """Return all policies for a user, filling defaults for missing channels."""
    data = _load()
    stored = {p["channel"]: p for p in data.get("policies", []) if p.get("user_id") == user_id}
    result = []
    for channel in CHANNELS:
        result.append(stored.get(channel) or _default_policy(user_id, channel))
    return result


def upsert_policy(user_id: str, channel: str, updates: dict) -> dict:
    """Create or update an automation policy for a channel."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()

    # Find existing
    existing_idx = None
    for i, p in enumerate(data.get("policies", [])):
        if p.get("user_id") == user_id and p.get("channel") == channel:
            existing_idx = i
            break

    if existing_idx is not None:
        policy = data["policies"][existing_idx]
        allowed_keys = {
            "autonomy_mode", "content_auto_publish", "ads_auto_launch",
            "max_daily_posts", "max_daily_spend_usd", "reallocation_cap_pct",
            "approval_threshold_usd", "quiet_hours_start", "quiet_hours_end", "kill_switch",
        }
        for k, v in updates.items():
            if k in allowed_keys:
                policy[k] = v
        policy["updated_at"] = now
        data["policies"][existing_idx] = policy
    else:
        policy = _default_policy(user_id, channel)
        allowed_keys = {
            "autonomy_mode", "content_auto_publish", "ads_auto_launch",
            "max_daily_posts", "max_daily_spend_usd", "reallocation_cap_pct",
            "approval_threshold_usd", "quiet_hours_start", "quiet_hours_end", "kill_switch",
        }
        for k, v in updates.items():
            if k in allowed_keys:
                policy[k] = v
        policy["updated_at"] = now
        data.setdefault("policies", []).append(policy)

    _save(data)
    return policy


def set_kill_switch(user_id: str, channel: str, enabled: bool) -> dict:
    """Set emergency kill switch for a channel (stops all auto-actions)."""
    return upsert_policy(user_id, channel, {"kill_switch": enabled})


def is_quiet_hours(policy: dict) -> bool:
    """Return True if the current UTC time falls within quiet hours."""
    start = policy.get("quiet_hours_start")
    end = policy.get("quiet_hours_end")
    if not start or not end:
        return False
    try:
        now_t = datetime.now(timezone.utc).strftime("%H:%M")
        # Handles overnight windows (e.g. 22:00 → 07:00)
        if start <= end:
            return start <= now_t < end
        else:
            return now_t >= start or now_t < end
    except Exception:
        return False


def get_daily_post_count(user_id: str, channel: str) -> int:
    """Count auto-published posts for this user/channel in the current UTC day."""
    try:
        from app.core.store.audit_store import get_recent_events
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        events = get_recent_events(user_id, limit=200, action_prefix="publish.", channel=channel)
        return sum(
            1 for e in events
            if e.get("success") is True
            and e.get("timestamp", "").startswith(today)
        )
    except Exception:
        return 0


def is_auto_publish_allowed(user_id: str, channel: str) -> bool:
    """Check if auto-publish is enabled AND kill switch is off."""
    policy = get_policy(user_id, channel)
    if policy.get("kill_switch"):
        return False
    return bool(policy.get("content_auto_publish", False))


def check_publish_allowed(user_id: str, channel: str) -> tuple[bool, str]:
    """
    Full publish gate: checks kill switch, auto-publish flag, quiet hours, and daily limit.
    Returns (allowed: bool, reason: str).
    """
    policy = get_policy(user_id, channel)
    if policy.get("kill_switch"):
        return False, "Kill switch is active. Re-enable auto-publish in Autonomy Settings."
    if not policy.get("content_auto_publish", False):
        return False, f"Auto-publish is off for '{channel}'. Enable it in Autonomy Settings."
    if is_quiet_hours(policy):
        return False, f"Quiet hours active ({policy.get('quiet_hours_start')}–{policy.get('quiet_hours_end')}). Post will retry after quiet window."
    max_daily = int(policy.get("max_daily_posts") or 0)
    if max_daily > 0:
        published_today = get_daily_post_count(user_id, channel)
        if published_today >= max_daily:
            return False, f"Daily post limit reached ({published_today}/{max_daily} for '{channel}'). Resets at midnight UTC."
    return True, ""


def is_auto_launch_allowed(user_id: str, channel: str) -> bool:
    """Check if auto ad launch is enabled AND kill switch is off."""
    policy = get_policy(user_id, channel)
    if policy.get("kill_switch"):
        return False
    return bool(policy.get("ads_auto_launch", False))


def requires_approval_for_spend(user_id: str, channel: str, amount_usd: float) -> bool:
    """Return True if the spend amount requires human approval."""
    policy = get_policy(user_id, channel)
    threshold = policy.get("approval_threshold_usd", 50.0)
    return amount_usd >= threshold
