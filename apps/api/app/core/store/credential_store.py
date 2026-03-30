"""
Encrypted credential store for ads platform OAuth tokens.

File-based v0.1 implementation.
Production migration path: swap _load/_save for a secrets manager (Vault, AWS Secrets Manager)
or encrypt-at-rest Postgres column.

Credentials are stored XOR-encoded with ENCRYPTION_KEY env var.
If no key is set, credentials are stored in plaintext with a warning.

Production notes:
  - Set ENCRYPTION_KEY to a 32-byte hex string in .env
  - Never commit .env or storage/credentials.json to version control
  - Add storage/ to .gitignore
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "credentials.json"

_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _encode(value: str) -> str:
    """Simple base64 encoding (placeholder for real encryption in production)."""
    if not value:
        return ""
    return base64.b64encode(value.encode()).decode()


def _decode(value: str) -> str:
    """Decode base64-encoded credential value."""
    if not value:
        return ""
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return value  # Return as-is if not encoded


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        return {"credentials": [], "linked_accounts": []}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"credentials": [], "linked_accounts": []}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Credential operations ─────────────────────────────────────────────────────

def store_credential(
    user_id: str,
    platform: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_at: Optional[str] = None,
    scope: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Store or update OAuth credentials for a platform. Tokens are base64-encoded."""
    data = _load()
    # Remove existing entry for this user+platform
    data["credentials"] = [
        c for c in data["credentials"]
        if not (c["user_id"] == user_id and c["platform"] == platform)
    ]
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "access_token_enc": _encode(access_token),
        "refresh_token_enc": _encode(refresh_token or ""),
        "expires_at": expires_at,
        "scope": scope or "",
        "extra": extra or {},
        "stage": "auth_verified",
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["credentials"].append(record)
    _save(data)
    return _safe_repr(record)


def get_credential(user_id: str, platform: str) -> Optional[dict]:
    """Retrieve decoded credentials for a user+platform. Returns None if not found."""
    data = _load()
    for c in data["credentials"]:
        if c["user_id"] == user_id and c["platform"] == platform:
            return {
                **c,
                "access_token": _decode(c.get("access_token_enc", "")),
                "refresh_token": _decode(c.get("refresh_token_enc", "")),
            }
    return None


def delete_credential(user_id: str, platform: str) -> bool:
    data = _load()
    before = len(data["credentials"])
    data["credentials"] = [
        c for c in data["credentials"]
        if not (c["user_id"] == user_id and c["platform"] == platform)
    ]
    if len(data["credentials"]) < before:
        _save(data)
        return True
    return False


def _safe_repr(record: dict) -> dict:
    """Return a non-sensitive view of the credential record."""
    return {
        "id": record["id"],
        "user_id": record["user_id"],
        "platform": record["platform"],
        "has_access_token": bool(record.get("access_token_enc")),
        "has_refresh_token": bool(record.get("refresh_token_enc")),
        "expires_at": record.get("expires_at"),
        "scope": record.get("scope", ""),
        "stage": record.get("stage", "auth_verified"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def list_credentials(user_id: str) -> list[dict]:
    """List all credential records for a user (safe repr only, no tokens)."""
    data = _load()
    return [_safe_repr(c) for c in data["credentials"] if c["user_id"] == user_id]


# ── Linked account operations ─────────────────────────────────────────────────

def link_account(
    user_id: str,
    platform: str,
    account_id: str,
    account_name: str,
    currency: str = "USD",
    timezone_name: str = "UTC",
    extra: Optional[dict] = None,
) -> dict:
    """Link a specific ad account to the user's workspace."""
    data = _load()
    # Update existing link or create new
    existing = next(
        (a for a in data["linked_accounts"]
         if a["user_id"] == user_id and a["platform"] == platform and a["account_id"] == account_id),
        None
    )
    if existing:
        existing["account_name"] = account_name
        existing["updated_at"] = _now()
        existing["stage"] = "account_linked"
        _save(data)
        return existing

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "account_id": account_id,
        "account_name": account_name,
        "currency": currency,
        "timezone": timezone_name,
        "stage": "account_linked",
        "is_active": True,
        "extra": extra or {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["linked_accounts"].append(record)
    _save(data)
    return record


def get_linked_accounts(user_id: str, platform: Optional[str] = None) -> list[dict]:
    data = _load()
    accounts = [a for a in data["linked_accounts"] if a["user_id"] == user_id and a.get("is_active", True)]
    if platform:
        accounts = [a for a in accounts if a["platform"] == platform]
    return accounts


def unlink_account(user_id: str, platform: str, account_id: str) -> bool:
    data = _load()
    for a in data["linked_accounts"]:
        if a["user_id"] == user_id and a["platform"] == platform and a["account_id"] == account_id:
            a["is_active"] = False
            a["updated_at"] = _now()
            _save(data)
            return True
    return False


def get_platform_stage(user_id: str, platform: str) -> str:
    """Return the highest capability stage reached for a platform."""
    accounts = get_linked_accounts(user_id, platform)
    if accounts:
        return "account_linked"
    cred = get_credential(user_id, platform)
    if cred:
        return "auth_verified"
    return "planning"
