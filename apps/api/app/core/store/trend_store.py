"""
Trend signal store — file-backed with per-niche TTL.

Structure:
  storage/trend_store.json → { "niche_signals": { "<niche>": { signals, fetched_at, expires_at } } }

Signals are refreshed by the background trend_refresh_job every 6 hours.
Falls back to seeded niche_data.py values when cache is cold or external fetch fails.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "trend_store.json"
CACHE_TTL_HOURS = 6

_DEFAULT: dict = {"niche_signals": {}}


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


def is_cache_fresh(niche: str) -> bool:
    data = _load()
    entry = data.get("niche_signals", {}).get(niche)
    if not entry:
        return False
    expires_at = entry.get("expires_at")
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expiry
    except (ValueError, TypeError):
        return False


def get_signals(niche: str) -> list[dict]:
    """Return cached signals for a niche, or empty list if cache is stale/missing."""
    data = _load()
    entry = data.get("niche_signals", {}).get(niche)
    if not entry:
        return []
    return entry.get("signals", [])


def store_signals(niche: str, signals: list[dict]) -> None:
    """Persist signals for a niche with TTL."""
    data = _load()
    now = datetime.now(timezone.utc)
    data.setdefault("niche_signals", {})[niche] = {
        "signals": signals,
        "fetched_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=CACHE_TTL_HOURS)).isoformat(),
        "count": len(signals),
    }
    _save(data)


def get_last_refresh(niche: str) -> Optional[str]:
    data = _load()
    entry = data.get("niche_signals", {}).get(niche)
    return entry.get("fetched_at") if entry else None


def get_all_niches_status() -> dict:
    """Return cache status for all stored niches."""
    data = _load()
    result = {}
    for niche, entry in data.get("niche_signals", {}).items():
        result[niche] = {
            "count": entry.get("count", 0),
            "fetched_at": entry.get("fetched_at"),
            "expires_at": entry.get("expires_at"),
            "fresh": is_cache_fresh(niche),
        }
    return result
