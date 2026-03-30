"""
File-based learning loop store.

Persists strategy outcomes, hypothesis records, and learning runs.
This is the foundation of the closed-loop growth system.

In production: migrate to Feast (feature store) + MLflow (experiment tracking).
Currently: file-based JSON for self-hosted zero-dependency operation.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "learning_store.json"

_DEFAULT: dict = {
    "strategy_records": [],     # Every recommendation + what happened
    "hypothesis_records": [],   # Tested hypotheses with outcomes
    "learning_runs": [],        # Periodic learning sweep records
    "suppressed_strategies": [], # Failed strategies to avoid repeating
    "promoted_strategies": [],  # High-performing patterns to amplify
}


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        data = dict(_DEFAULT)
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
        return dict(_DEFAULT)


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Strategy Records ──────────────────────────────────────────────────────────

def record_strategy(
    user_id: str,
    strategy_type: str,            # channel_recommendation | content_brief | media_plan | audience_hypothesis
    strategy_title: str,
    niche: str,
    channel: Optional[str],
    recommendation_data: dict,
    source: str = "niche_engine",  # niche_engine | user_defined | llm_generated
    strategy_version: str = "v1",
    expected_outcome: Optional[dict] = None,  # { metric: value } predictions
) -> dict:
    """Record a strategy recommendation for future outcome tracking."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "strategy_type": strategy_type,
        "strategy_title": strategy_title,
        "niche": niche,
        "channel": channel,
        "source": source,
        "strategy_version": strategy_version,
        "recommendation_data": recommendation_data,
        "expected_outcome": expected_outcome or {},
        "status": "recommended",   # recommended | approved | rejected | executed | measured
        "outcome": None,           # None | success | failure | partial
        "outcome_data": {},        # Actual metrics when available
        "confidence_before": 0.7,  # Starting confidence
        "confidence_after": None,  # Updated after measurement
        "confidence_delta": None,  # Computed: confidence_after - confidence_before
        "approved_at": None,
        "executed_at": None,
        "measured_at": None,
        "created_at": _now(),
    }
    data = _load()
    data["strategy_records"].append(record)
    _save(data)
    return record


def update_strategy_outcome(
    record_id: str,
    outcome: str,          # success | failure | partial
    outcome_data: dict,    # { impressions, clicks, conversions, roas, cac, ... }
    confidence_after: Optional[float] = None,
) -> Optional[dict]:
    """Record the measured outcome for a strategy and update confidence delta."""
    data = _load()
    for r in data["strategy_records"]:
        if r["id"] == record_id:
            r["outcome"] = outcome
            r["outcome_data"] = outcome_data
            r["status"] = "measured"
            r["measured_at"] = _now()
            # Auto-compute confidence_after from outcome if not provided
            if confidence_after is not None:
                r["confidence_after"] = confidence_after
            elif outcome == "success":
                r["confidence_after"] = min(1.0, r["confidence_before"] + 0.1)
            elif outcome == "failure":
                r["confidence_after"] = max(0.0, r["confidence_before"] - 0.15)
            else:  # partial
                r["confidence_after"] = r["confidence_before"]
            # Confidence delta
            if r["confidence_after"] is not None:
                r["confidence_delta"] = round(r["confidence_after"] - r["confidence_before"], 3)
            _save(data)
            # Trigger suppression or promotion
            _evaluate_strategy_pattern(data, r)
            return r
    return None


def get_strategy_records(
    user_id: str,
    niche: Optional[str] = None,
    strategy_type: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    records = [r for r in _load()["strategy_records"] if r["user_id"] == user_id]
    if niche:
        records = [r for r in records if r["niche"] == niche]
    if strategy_type:
        records = [r for r in records if r["strategy_type"] == strategy_type]
    if outcome:
        records = [r for r in records if r["outcome"] == outcome]
    return sorted(records, key=lambda x: x["created_at"], reverse=True)[:limit]


# ── Hypothesis Records ────────────────────────────────────────────────────────

def record_hypothesis(
    user_id: str,
    hypothesis: str,
    rationale: str,
    channel: Optional[str],
    niche: str,
    test_type: str,           # ab_test | before_after | holdout | multivariate
    metric_to_track: str,     # ctr | cpa | roas | engagement_rate | follower_growth
    expected_lift_pct: float,
    test_duration_days: int,
) -> dict:
    """Create a testable hypothesis record."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "hypothesis": hypothesis,
        "rationale": rationale,
        "channel": channel,
        "niche": niche,
        "test_type": test_type,
        "metric_to_track": metric_to_track,
        "expected_lift_pct": expected_lift_pct,
        "test_duration_days": test_duration_days,
        "status": "proposed",   # proposed | running | completed | abandoned
        "result": None,         # None | confirmed | rejected | inconclusive
        "actual_lift_pct": None,
        "result_data": {},
        "confidence_level": None,
        "notes": "",
        "started_at": None,
        "completed_at": None,
        "created_at": _now(),
    }
    data = _load()
    data["hypothesis_records"].append(record)
    _save(data)
    return record


def update_hypothesis_result(
    hypothesis_id: str,
    result: str,              # confirmed | rejected | inconclusive
    actual_lift_pct: float,
    confidence_level: float,  # 0.0 – 1.0
    result_data: dict,
    notes: str = "",
) -> Optional[dict]:
    """Record the outcome of a hypothesis test."""
    data = _load()
    for h in data["hypothesis_records"]:
        if h["id"] == hypothesis_id:
            h["result"] = result
            h["actual_lift_pct"] = actual_lift_pct
            h["confidence_level"] = confidence_level
            h["result_data"] = result_data
            h["status"] = "completed"
            h["completed_at"] = _now()
            h["notes"] = notes
            _save(data)
            return h
    return None


def get_hypotheses(
    user_id: str,
    niche: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    records = [h for h in _load()["hypothesis_records"] if h["user_id"] == user_id]
    if niche:
        records = [h for h in records if h["niche"] == niche]
    if result:
        records = [h for h in records if h["result"] == result]
    return sorted(records, key=lambda x: x["created_at"], reverse=True)[:limit]


# ── Pattern Suppression / Promotion ──────────────────────────────────────────

def _evaluate_strategy_pattern(data: dict, record: dict) -> None:
    """
    After recording a strategy outcome, check if the pattern should be
    suppressed (repeated failure) or promoted (consistent success).
    """
    niche = record["niche"]
    strategy_type = record["strategy_type"]
    outcome = record["outcome"]

    # Count recent outcomes for this pattern
    matching = [
        r for r in data["strategy_records"]
        if r["niche"] == niche
        and r["strategy_type"] == strategy_type
        and r["outcome"] is not None
    ][-10:]  # Last 10 instances

    if len(matching) < 3:
        return  # Not enough data

    failures = [r for r in matching if r["outcome"] == "failure"]
    successes = [r for r in matching if r["outcome"] == "success"]
    failure_rate = len(failures) / len(matching)
    success_rate = len(successes) / len(matching)

    pattern_key = f"{niche}:{strategy_type}"

    # Suppress if >60% failure rate
    if failure_rate >= 0.6:
        existing = [s for s in data["suppressed_strategies"] if s["pattern_key"] == pattern_key]
        if not existing:
            data["suppressed_strategies"].append({
                "id": str(uuid.uuid4()),
                "pattern_key": pattern_key,
                "niche": niche,
                "strategy_type": strategy_type,
                "failure_rate": failure_rate,
                "sample_size": len(matching),
                "suppressed_at": _now(),
                "note": f"Suppressed after {len(failures)}/{len(matching)} failures",
            })

    # Promote if >70% success rate
    if success_rate >= 0.7:
        existing = [p for p in data["promoted_strategies"] if p["pattern_key"] == pattern_key]
        if not existing:
            data["promoted_strategies"].append({
                "id": str(uuid.uuid4()),
                "pattern_key": pattern_key,
                "niche": niche,
                "strategy_type": strategy_type,
                "success_rate": success_rate,
                "sample_size": len(matching),
                "promoted_at": _now(),
                "note": f"Promoted after {len(successes)}/{len(matching)} successes",
            })

    _save(data)


def get_suppressed_strategies(niche: Optional[str] = None) -> list[dict]:
    data = _load()
    items = data["suppressed_strategies"]
    if niche:
        items = [s for s in items if s["niche"] == niche]
    return items


def get_promoted_strategies(niche: Optional[str] = None) -> list[dict]:
    data = _load()
    items = data["promoted_strategies"]
    if niche:
        items = [p for p in items if p["niche"] == niche]
    return items


# ── Learning Summary ──────────────────────────────────────────────────────────

def get_learning_summary(user_id: str, niche: Optional[str] = None) -> dict:
    """Return a high-level learning summary for the dashboard."""
    records = get_strategy_records(user_id, niche=niche)
    hypotheses = get_hypotheses(user_id, niche=niche)
    suppressed = get_suppressed_strategies(niche=niche)
    promoted = get_promoted_strategies(niche=niche)

    measured = [r for r in records if r["outcome"] is not None]
    successes = [r for r in measured if r["outcome"] == "success"]
    failures = [r for r in measured if r["outcome"] == "failure"]

    confirmed_hypotheses = [h for h in hypotheses if h["result"] == "confirmed"]
    rejected_hypotheses = [h for h in hypotheses if h["result"] == "rejected"]

    return {
        "total_strategies_recorded": len(records),
        "total_measured": len(measured),
        "total_successes": len(successes),
        "total_failures": len(failures),
        "success_rate": round(len(successes) / len(measured), 2) if measured else None,
        "total_hypotheses": len(hypotheses),
        "confirmed_hypotheses": len(confirmed_hypotheses),
        "rejected_hypotheses": len(rejected_hypotheses),
        "suppressed_patterns": len(suppressed),
        "promoted_patterns": len(promoted),
        "suppressed": suppressed[:5],
        "promoted": promoted[:5],
        "recent_successes": [
            {"title": r["strategy_title"], "channel": r["channel"], "niche": r["niche"]}
            for r in successes[-3:]
        ],
        "recent_failures": [
            {"title": r["strategy_title"], "channel": r["channel"], "niche": r["niche"]}
            for r in failures[-3:]
        ],
    }
