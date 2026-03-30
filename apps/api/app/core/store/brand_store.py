"""
Simple JSON file-based store for brand profiles and intelligence cache.
Works without PostgreSQL — designed for local dev / demo mode.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "brand_store.json"

_DEFAULT = {"brand_profiles": [], "intelligence_runs": []}


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        _save(_DEFAULT)
        return _DEFAULT
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _DEFAULT


def _save(data: dict):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_brand_profile(user_id: str) -> Optional[dict]:
    data = _load()
    for p in data.get("brand_profiles", []):
        if p.get("user_id") == user_id:
            return p
    return None


def get_brand_profile_by_id(profile_id: str) -> Optional[dict]:
    data = _load()
    for p in data.get("brand_profiles", []):
        if p.get("id") == profile_id:
            return p
    return None


def create_brand_profile(user_id: str, profile: dict) -> dict:
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        **{k: v for k, v in profile.items() if k not in ("id", "user_id", "created_at", "updated_at")},
    }
    # Remove existing profile for this user first (single-profile model)
    data["brand_profiles"] = [p for p in data.get("brand_profiles", []) if p.get("user_id") != user_id]
    data["brand_profiles"].append(record)
    _save(data)
    return record


def update_brand_profile(profile_id: str, updates: dict) -> Optional[dict]:
    data = _load()
    for p in data.get("brand_profiles", []):
        if p.get("id") == profile_id:
            for k, v in updates.items():
                if v is not None and k not in ("id", "user_id", "created_at"):
                    p[k] = v
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save(data)
            return p
    return None


def upsert_brand_profile(user_id: str, profile: dict) -> dict:
    existing = get_brand_profile(user_id)
    if existing:
        return update_brand_profile(existing["id"], profile) or existing
    return create_brand_profile(user_id, profile)
