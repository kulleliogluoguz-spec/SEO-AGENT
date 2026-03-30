"""
Autonomy Policy API endpoints.

These endpoints persist per-channel automation policies for a user.
Policies are enforced at publish and campaign-launch time.

Routes:
  GET  /api/v1/autonomy/policies                 — list all channel policies
  POST /api/v1/autonomy/policies/{channel}        — upsert channel policy
  GET  /api/v1/autonomy/policies/{channel}        — get channel policy
  POST /api/v1/autonomy/policies/{channel}/kill   — toggle kill switch
  GET  /api/v1/autonomy/summary                   — compact summary for UI
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.core.store.autonomy_store import (
    get_all_policies,
    get_policy,
    set_kill_switch,
    upsert_policy,
    CHANNELS,
)

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PolicyUpsert(BaseModel):
    autonomy_mode: Optional[str] = Field(
        None,
        description="manual | assisted | semi_auto | autonomous"
    )
    content_auto_publish: Optional[bool] = None
    ads_auto_launch: Optional[bool] = None
    max_daily_posts: Optional[int] = Field(None, ge=0, le=50)
    max_daily_spend_usd: Optional[float] = Field(None, ge=0.0, le=10000.0)
    reallocation_cap_pct: Optional[int] = Field(None, ge=0, le=50)
    approval_threshold_usd: Optional[float] = Field(None, ge=0.0, le=10000.0)
    quiet_hours_start: Optional[str] = Field(None, description="HH:MM in user local time")
    quiet_hours_end: Optional[str] = Field(None, description="HH:MM in user local time")
    kill_switch: Optional[bool] = None


class KillSwitchRequest(BaseModel):
    enabled: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/policies")
async def list_policies(current_user=Depends(get_current_user)) -> dict:
    """Return all channel policies for the current user."""
    policies = get_all_policies(str(current_user.id))
    return {
        "policies": policies,
        "channels": CHANNELS,
        "total": len(policies),
    }


@router.get("/policies/{channel}")
async def get_channel_policy(
    channel: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Return the automation policy for a specific channel."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel '{channel}'. Valid: {CHANNELS}")
    policy = get_policy(str(current_user.id), channel)
    return policy


@router.post("/policies/{channel}")
async def upsert_channel_policy(
    channel: str,
    payload: PolicyUpsert,
    current_user=Depends(get_current_user),
) -> dict:
    """Create or update automation policy for a channel."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel '{channel}'. Valid: {CHANNELS}")

    valid_modes = {"manual", "assisted", "semi_auto", "autonomous"}
    if payload.autonomy_mode and payload.autonomy_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid autonomy_mode. Must be one of: {valid_modes}")

    updates = payload.model_dump(exclude_none=True)
    policy = upsert_policy(str(current_user.id), channel, updates)
    return {"policy": policy, "message": f"Policy updated for {channel}"}


@router.post("/policies/{channel}/kill")
async def toggle_kill_switch(
    channel: str,
    payload: KillSwitchRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """Enable or disable emergency kill switch for a channel."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel '{channel}'")
    policy = set_kill_switch(str(current_user.id), channel, payload.enabled)
    action = "enabled" if payload.enabled else "disabled"
    return {
        "policy": policy,
        "message": f"Kill switch {action} for {channel}. All auto-actions are {'STOPPED' if payload.enabled else 'restored'}.",
    }


@router.post("/kill-all")
async def kill_all_channels(current_user=Depends(get_current_user)) -> dict:
    """Emergency: disable all auto-actions across all channels."""
    results = {}
    for channel in CHANNELS:
        policy = set_kill_switch(str(current_user.id), channel, True)
        results[channel] = policy.get("kill_switch")
    return {
        "message": "Kill switch activated on all channels. No autonomous actions will occur.",
        "channels": results,
    }


@router.get("/summary")
async def get_autonomy_summary(current_user=Depends(get_current_user)) -> dict:
    """
    Compact summary of the user's autonomy configuration.
    Used by the command center and Growth Engine page.
    """
    policies = get_all_policies(str(current_user.id))

    any_auto_content = any(p.get("content_auto_publish") for p in policies)
    any_auto_ads = any(p.get("ads_auto_launch") for p in policies)
    any_kill_switch = any(p.get("kill_switch") for p in policies)

    modes = {p["channel"]: p.get("autonomy_mode", "manual") for p in policies}
    highest_mode = "manual"
    mode_rank = {"manual": 0, "assisted": 1, "semi_auto": 2, "autonomous": 3}
    for m in modes.values():
        if mode_rank.get(m, 0) > mode_rank.get(highest_mode, 0):
            highest_mode = m

    return {
        "highest_mode": highest_mode,
        "any_auto_content": any_auto_content,
        "any_auto_ads": any_auto_ads,
        "any_kill_switch_active": any_kill_switch,
        "channel_modes": modes,
        "policy_count": len(policies),
    }
