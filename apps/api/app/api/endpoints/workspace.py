"""
Workspace Settings — Dashboard-driven configuration.

Replaces per-customer manual .env editing. Credentials are encrypted
before storage and never returned to the frontend in plaintext — only
boolean flags showing whether each credential is set.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.security.encryption import encrypt

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"

CREDENTIAL_FIELDS = {
    "meta_app_id": "meta_app_id_enc",
    "meta_app_secret": "meta_app_secret_enc",
    "google_developer_token": "google_developer_token_enc",
    "google_client_id": "google_client_id_enc",
    "google_client_secret": "google_client_secret_enc",
    "twilio_account_sid": "twilio_account_sid_enc",
    "twilio_auth_token": "twilio_auth_token_enc",
}

PLAIN_FIELDS = [
    "company_name",
    "industry",
    "default_currency",
    "monthly_ad_budget",
    "break_even_roas",
    "avg_order_value",
    "cogs_per_unit",
    "shipping_cost",
    "return_rate",
    "twilio_phone_number",
    "slack_webhook_url",
    "notification_email",
    "setup_completed",
    "setup_step",
]


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out: dict = {}
    for k, v in row._mapping.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@router.get("/settings")
async def get_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return workspace settings — credentials shown as bool flags only."""
    wid = _wid(current_user)
    r = await db.execute(
        text("SELECT * FROM workspace_settings WHERE workspace_id = :wid"),
        {"wid": wid},
    )
    row = r.fetchone()
    if not row:
        return {"settings": {"setup_completed": False, "setup_step": 1}}

    settings = _row_to_dict(row)
    # Replace each *_enc field with a bool flag, never expose ciphertext.
    for plain_key, enc_key in CREDENTIAL_FIELDS.items():
        settings[plain_key] = bool(settings.get(enc_key))
        settings.pop(enc_key, None)
    return {"settings": settings}


@router.put("/settings")
async def update_settings(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upsert workspace settings. Credentials are encrypted before storage
    and only updated when a non-empty value is provided (so partial
    updates don't accidentally clear other secrets).
    """
    wid = _wid(current_user)

    updates: dict = {}
    for plain in PLAIN_FIELDS:
        if plain in data:
            updates[plain] = data[plain]
    for cred_key, enc_key in CREDENTIAL_FIELDS.items():
        if cred_key in data and data[cred_key]:
            updates[enc_key] = encrypt(data[cred_key])

    if not updates:
        return {"success": True, "updated_fields": 0}

    columns = list(updates.keys())
    set_clause = ", ".join(f"{k} = EXCLUDED.{k}" for k in columns)
    insert_cols = ", ".join(["workspace_id", *columns])
    insert_vals = ", ".join([":wid", *(f":{k}" for k in columns)])

    params = {"wid": wid, **updates}
    await db.execute(
        text(
            f"""
            INSERT INTO workspace_settings ({insert_cols})
            VALUES ({insert_vals})
            ON CONFLICT (workspace_id) DO UPDATE SET
                {set_clause}, updated_at = NOW()
            """
        ),
        params,
    )
    await db.commit()
    return {"success": True, "updated_fields": len(updates)}


@router.get("/setup-status")
async def get_setup_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the onboarding wizard's current step + connection counts."""
    wid = _wid(current_user)
    r = await db.execute(
        text(
            "SELECT setup_step, setup_completed FROM workspace_settings "
            "WHERE workspace_id = :wid"
        ),
        {"wid": wid},
    )
    row = r.fetchone()
    setup_step = 1
    setup_completed = False
    if row:
        d = _row_to_dict(row)
        setup_step = d.get("setup_step") or 1
        setup_completed = bool(d.get("setup_completed"))

    conn_r = await db.execute(
        text(
            """
            SELECT platform, COUNT(*) AS cnt
            FROM ad_account_connections
            WHERE workspace_id = :wid AND is_active = true
            GROUP BY platform
            """
        ),
        {"wid": wid},
    )
    connections = {row.platform: row.cnt for row in conn_r.fetchall()}

    return {
        "setup_step": setup_step,
        "setup_completed": setup_completed,
        "meta_connected": (connections.get("meta", 0) or 0) > 0,
        "google_connected": (connections.get("google", 0) or 0) > 0,
    }
