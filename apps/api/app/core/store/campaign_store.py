"""
File-based campaign draft store.

Stores all campaign drafts, creative drafts, and audience drafts before
they are submitted to ad platform APIs.

All drafts are in PAUSED/DRAFT state until explicitly published via an
approval-gated workflow. No live campaign is created without human approval.

Production migration path: PostgreSQL + Redis for status polling.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "campaign_store.json"

_DEFAULT: dict = {
    "campaign_drafts": [],
    "creative_drafts": [],
    "audience_drafts": [],
    "reallocation_decisions": [],
    "audit_log": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        return dict(_DEFAULT)
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
        for k, v in _DEFAULT.items():
            if k not in data:
                data[k] = list(v) if isinstance(v, list) else v
        return data
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Campaign Draft CRUD ───────────────────────────────────────────────────────

def create_campaign_draft(
    user_id: str,
    platform: str,
    account_id: str,
    name: str,
    objective: str,
    daily_budget_usd: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_audiences: Optional[list] = None,
    creatives: Optional[list] = None,
    notes: str = "",
    strategy_version: str = "v1",
) -> dict:
    """Create a campaign draft. Draft is always PAUSED — never auto-published."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "account_id": account_id,
        "name": name,
        "objective": objective,
        "daily_budget_usd": daily_budget_usd,
        "start_date": start_date,
        "end_date": end_date,
        "target_audiences": target_audiences or [],
        "creatives": creatives or [],
        "notes": notes,
        "strategy_version": strategy_version,
        # Lifecycle
        "status": "draft",        # draft | pending_approval | approved | published | paused | archived
        "platform_campaign_id": None,  # Set after publishing to platform
        "approval_id": None,
        "published_at": None,
        "created_at": _now(),
        "updated_at": _now(),
        # Outcome tracking
        "expected_impressions": None,
        "expected_clicks": None,
        "expected_ctr": None,
        "expected_cpc": None,
        "confidence": 0.6,
    }
    data = _load()
    data["campaign_drafts"].append(record)
    _audit(data, user_id, "campaign_draft_created", record["id"], {"name": name, "platform": platform})
    _save(data)
    return record


def get_campaign_drafts(
    user_id: str,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    data = _load()
    items = [d for d in data["campaign_drafts"] if d["user_id"] == user_id]
    if platform:
        items = [d for d in items if d["platform"] == platform]
    if status:
        items = [d for d in items if d["status"] == status]
    return sorted(items, key=lambda x: x["created_at"], reverse=True)[:limit]


def get_campaign_draft(draft_id: str) -> Optional[dict]:
    data = _load()
    return next((d for d in data["campaign_drafts"] if d["id"] == draft_id), None)


def update_campaign_draft(draft_id: str, updates: dict) -> Optional[dict]:
    data = _load()
    for d in data["campaign_drafts"]:
        if d["id"] == draft_id:
            allowed = {"name", "objective", "daily_budget_usd", "start_date", "end_date",
                       "target_audiences", "creatives", "notes", "status", "approval_id",
                       "platform_campaign_id", "published_at"}
            for k, v in updates.items():
                if k in allowed:
                    d[k] = v
            d["updated_at"] = _now()
            _save(data)
            return d
    return None


def submit_for_approval(draft_id: str, user_id: str) -> Optional[dict]:
    """Transition draft to pending_approval state."""
    data = _load()
    for d in data["campaign_drafts"]:
        if d["id"] == draft_id and d["user_id"] == user_id:
            d["status"] = "pending_approval"
            d["updated_at"] = _now()
            _audit(data, user_id, "campaign_submitted_for_approval", draft_id, {})
            _save(data)
            return d
    return None


def mark_published(draft_id: str, user_id: str, platform_campaign_id: str) -> Optional[dict]:
    """Mark draft as published after successful API call."""
    data = _load()
    for d in data["campaign_drafts"]:
        if d["id"] == draft_id and d["user_id"] == user_id:
            d["status"] = "published"
            d["platform_campaign_id"] = platform_campaign_id
            d["published_at"] = _now()
            d["updated_at"] = _now()
            _audit(data, user_id, "campaign_published", draft_id, {"platform_campaign_id": platform_campaign_id})
            _save(data)
            return d
    return None


# ── Reallocation Decisions ────────────────────────────────────────────────────

def create_reallocation_decision(
    user_id: str,
    platform: str,
    account_id: str,
    campaign_id: str,
    old_budget_usd: float,
    new_budget_usd: float,
    reason: str,
    supporting_metrics: dict,
    confidence: float,
    requires_approval: bool = True,
    rollback_plan: str = "Revert to previous budget if ROAS drops below threshold.",
) -> dict:
    """Record a reallocation decision. Always logged; requires approval if above threshold."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "account_id": account_id,
        "campaign_id": campaign_id,
        "old_budget_usd": old_budget_usd,
        "new_budget_usd": new_budget_usd,
        "delta_usd": round(new_budget_usd - old_budget_usd, 2),
        "delta_pct": round(((new_budget_usd - old_budget_usd) / old_budget_usd) * 100, 1) if old_budget_usd > 0 else 0,
        "reason": reason,
        "supporting_metrics": supporting_metrics,
        "confidence": confidence,
        "requires_approval": requires_approval,
        "rollback_plan": rollback_plan,
        "status": "pending_approval" if requires_approval else "applied",
        "applied_at": None,
        "created_at": _now(),
    }
    data = _load()
    data["reallocation_decisions"].append(record)
    _audit(data, user_id, "reallocation_decision_created", record["id"],
           {"old_budget": old_budget_usd, "new_budget": new_budget_usd, "reason": reason})
    _save(data)
    return record


def get_reallocation_decisions(user_id: str, platform: Optional[str] = None) -> list[dict]:
    data = _load()
    items = [r for r in data["reallocation_decisions"] if r["user_id"] == user_id]
    if platform:
        items = [r for r in items if r["platform"] == platform]
    return sorted(items, key=lambda x: x["created_at"], reverse=True)


# ── Audit log ─────────────────────────────────────────────────────────────────

def _audit(data: dict, user_id: str, action: str, entity_id: str, details: dict) -> None:
    data["audit_log"].append({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "entity_id": entity_id,
        "details": details,
        "timestamp": _now(),
    })


def get_audit_log(user_id: str, limit: int = 100) -> list[dict]:
    data = _load()
    entries = [e for e in data["audit_log"] if e["user_id"] == user_id]
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]
