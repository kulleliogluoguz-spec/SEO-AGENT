"""
Content Queue Store — file-backed content lifecycle state machine.

Content lifecycle:
  generated → needs_review → approved → scheduled → publishing → published
                                                                     ↓
                                                                  (failed → retry → scheduled)

This store manages ContentDraft and ScheduledPost entities.
The publish_sweep_job (runs every 5 minutes) picks up scheduled posts past their scheduled_at
and attempts to publish them via the appropriate channel abstraction.

Migration path: Replace with PostgreSQL content_drafts + scheduled_posts tables.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "content_queue_store.json"

VALID_STATUSES = {
    "generated", "needs_review", "approved",
    "scheduled", "publishing", "published",
    "failed", "archived",
}

VALID_CHANNELS = {"instagram", "x", "tiktok", "linkedin", "youtube", "website"}

_DEFAULT: dict = {
    "content_drafts": [],
    "scheduled_posts": [],
    "publish_log": [],
}


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


# ── ContentDraft CRUD ─────────────────────────────────────────────────────────

def create_draft(
    user_id: str,
    title: str,
    content_type: str,
    topic: str,
    generated_text: str,
    niche: Optional[str] = None,
    trend_keyword: Optional[str] = None,
    objective: Optional[str] = None,
    channels: Optional[list[str]] = None,
) -> dict:
    """Create a new content draft from generation output."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    draft = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "content_type": content_type,
        "topic": topic,
        "generated_text": generated_text,
        "status": "generated",
        "niche": niche,
        "trend_keyword": trend_keyword,
        "objective": objective,
        "channels": channels or [],
        "scheduled_posts": [],
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "approved_by": None,
        "rejection_reason": None,
    }
    data.setdefault("content_drafts", []).append(draft)
    _save(data)
    return draft


def get_draft(draft_id: str) -> Optional[dict]:
    data = _load()
    for d in data.get("content_drafts", []):
        if d.get("id") == draft_id:
            return d
    return None


def list_drafts(
    user_id: str,
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    data = _load()
    drafts = [d for d in data.get("content_drafts", []) if d.get("user_id") == user_id]
    if status:
        drafts = [d for d in drafts if d.get("status") == status]
    if content_type:
        drafts = [d for d in drafts if d.get("content_type") == content_type]
    return sorted(drafts, key=lambda d: d.get("created_at", ""), reverse=True)[:limit]


def transition_status(draft_id: str, new_status: str, actor: Optional[str] = None, reason: Optional[str] = None) -> Optional[dict]:
    """Move a draft to a new lifecycle status."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Valid: {VALID_STATUSES}")

    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for draft in data.get("content_drafts", []):
        if draft.get("id") == draft_id:
            old_status = draft.get("status")
            draft["status"] = new_status
            draft["updated_at"] = now
            if new_status == "approved":
                draft["approved_at"] = now
                draft["approved_by"] = actor
            if new_status == "needs_review" and reason:
                draft["rejection_reason"] = reason
            if new_status == "failed" and reason:
                draft["last_error"] = reason
                draft["retry_count"] = draft.get("retry_count", 0) + 1
            # Append to lifecycle log
            draft.setdefault("lifecycle_log", []).append({
                "from": old_status, "to": new_status,
                "actor": actor, "reason": reason, "at": now,
            })
            _save(data)
            return draft
    return None


def update_draft_text(draft_id: str, generated_text: str) -> Optional[dict]:
    """Update the generated text (e.g. after re-generation)."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for draft in data.get("content_drafts", []):
        if draft.get("id") == draft_id:
            draft["generated_text"] = generated_text
            draft["updated_at"] = now
            _save(data)
            return draft
    return None


# ── ScheduledPost CRUD ────────────────────────────────────────────────────────

def schedule_post(
    draft_id: str,
    user_id: str,
    channel: str,
    scheduled_at: str,
    caption_override: Optional[str] = None,
) -> dict:
    """Schedule a draft for posting on a channel at a specific time."""
    if channel not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel '{channel}'. Valid: {VALID_CHANNELS}")

    data = _load()
    now = datetime.now(timezone.utc).isoformat()

    post = {
        "id": str(uuid.uuid4()),
        "draft_id": draft_id,
        "user_id": user_id,
        "channel": channel,
        "scheduled_at": scheduled_at,
        "caption_override": caption_override,
        "status": "scheduled",
        "publish_attempt_count": 0,
        "last_attempt_at": None,
        "published_at": None,
        "platform_post_id": None,
        "error": None,
        "created_at": now,
    }
    data.setdefault("scheduled_posts", []).append(post)

    # Also transition draft to scheduled
    for d in data.get("content_drafts", []):
        if d.get("id") == draft_id:
            d["status"] = "scheduled"
            d["updated_at"] = now
            d.setdefault("scheduled_posts", []).append(post["id"])

    _save(data)
    return post


def get_due_scheduled_posts() -> list[dict]:
    """Return scheduled posts whose scheduled_at is in the past and status is 'scheduled'."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    return [
        p for p in data.get("scheduled_posts", [])
        if p.get("status") == "scheduled" and p.get("scheduled_at", "9999") <= now
    ]


def mark_post_published(post_id: str, platform_post_id: Optional[str] = None) -> Optional[dict]:
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for post in data.get("scheduled_posts", []):
        if post.get("id") == post_id:
            post["status"] = "published"
            post["published_at"] = now
            post["platform_post_id"] = platform_post_id
            # Also update parent draft
            for d in data.get("content_drafts", []):
                if d.get("id") == post.get("draft_id"):
                    d["status"] = "published"
                    d["updated_at"] = now
            data.setdefault("publish_log", []).append({
                "post_id": post_id, "action": "published", "at": now,
            })
            _save(data)
            return post
    return None


def mark_post_failed(post_id: str, error: str) -> Optional[dict]:
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for post in data.get("scheduled_posts", []):
        if post.get("id") == post_id:
            post["status"] = "failed"
            post["error"] = error
            post["last_attempt_at"] = now
            post["publish_attempt_count"] = post.get("publish_attempt_count", 0) + 1
            # Back to scheduled for retry if < 3 attempts
            if post["publish_attempt_count"] < 3:
                post["status"] = "scheduled"
                post["scheduled_at"] = (
                    datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
                )  # retry immediately next sweep
            else:
                # Give up — mark draft as failed
                for d in data.get("content_drafts", []):
                    if d.get("id") == post.get("draft_id"):
                        d["status"] = "failed"
                        d["last_error"] = error
                        d["updated_at"] = now
            data.setdefault("publish_log", []).append({
                "post_id": post_id, "action": "failed", "error": error, "at": now,
            })
            _save(data)
            return post
    return None


def list_scheduled_posts(user_id: str, status: Optional[str] = None) -> list[dict]:
    data = _load()
    posts = [p for p in data.get("scheduled_posts", []) if p.get("user_id") == user_id]
    if status:
        posts = [p for p in posts if p.get("status") == status]
    return sorted(posts, key=lambda p: p.get("scheduled_at", ""), reverse=False)


def get_published_posts_for_metrics(user_id: str, days: int = 7) -> list[dict]:
    """
    Return published scheduled posts (with platform_post_id) for the last N days.
    Used by the metrics ingestion background job to poll for engagement data.
    Also enriches each post with its parent draft metadata (topic, content_type).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = _load()

    # Build a draft lookup for enrichment
    draft_lookup = {d["id"]: d for d in data.get("content_drafts", [])}

    posts = []
    for p in data.get("scheduled_posts", []):
        if (
            p.get("user_id") == user_id
            and p.get("status") == "published"
            and p.get("platform_post_id")
            and p.get("published_at", "") >= cutoff
        ):
            # Enrich with draft fields
            draft = draft_lookup.get(p.get("draft_id", ""), {})
            enriched = {**p}
            enriched.setdefault("topic", draft.get("topic", ""))
            enriched.setdefault("content_type", draft.get("content_type", "text_post"))
            enriched.setdefault("generated_text", draft.get("generated_text", ""))
            enriched.setdefault("title", draft.get("title", ""))
            enriched.setdefault("objective", draft.get("objective", ""))
            posts.append(enriched)

    return posts
