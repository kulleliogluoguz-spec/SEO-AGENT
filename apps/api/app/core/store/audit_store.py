"""
Audit Event Store — immutable append-only log of all autonomous system actions.

Every publish, launch, reallocation, and policy enforcement writes here.
The audit log is the trust foundation for the autonomy system:
  - operators can inspect every action taken on their behalf
  - the kill switch immediately halts all future writes
  - frontend reads the log to show "what the system did"

Structure: storage/audit_log.jsonl (newline-delimited JSON for append efficiency)

Migration path: PostgreSQL audit_events table with partitioning by month.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOG_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "audit_log.jsonl"


def write_audit_event(
    user_id: str,
    action: str,
    channel: Optional[str] = None,
    success: bool = True,
    post_id: Optional[str] = None,
    content_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    error: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Write an audit event for an autonomous system action.

    action examples:
      publish.x.text_post
      publish.instagram.image_post
      campaign.launch.meta
      reallocation.approved
      kill_switch.activated
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "channel": channel,
        "success": success,
        "post_id": post_id,
        "content_id": content_id,
        "campaign_id": campaign_id,
        "error": error,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")

    return event


def get_recent_events(
    user_id: str,
    limit: int = 50,
    action_prefix: Optional[str] = None,
    channel: Optional[str] = None,
) -> list[dict]:
    """Return most recent audit events for a user, newest first."""
    if not LOG_PATH.exists():
        return []

    events = []
    try:
        with open(LOG_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("user_id") != user_id:
                        continue
                    if action_prefix and not event.get("action", "").startswith(action_prefix):
                        continue
                    if channel and event.get("channel") != channel:
                        continue
                    events.append(event)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []

    # Reverse for newest first
    events.reverse()
    return events[:limit]


def get_publish_summary(user_id: str) -> dict:
    """Return a compact publish summary for the user."""
    events = get_recent_events(user_id, limit=500, action_prefix="publish.")
    successful = [e for e in events if e.get("success")]
    failed = [e for e in events if not e.get("success")]

    by_channel: dict[str, dict] = {}
    for e in events:
        ch = e.get("channel") or "unknown"
        if ch not in by_channel:
            by_channel[ch] = {"published": 0, "failed": 0, "last_at": None}
        if e.get("success"):
            by_channel[ch]["published"] += 1
        else:
            by_channel[ch]["failed"] += 1
        ts = e.get("timestamp")
        if ts and (by_channel[ch]["last_at"] is None or ts > by_channel[ch]["last_at"]):
            by_channel[ch]["last_at"] = ts

    return {
        "total_published": len(successful),
        "total_failed": len(failed),
        "by_channel": by_channel,
        "last_action_at": events[0].get("timestamp") if events else None,
    }
