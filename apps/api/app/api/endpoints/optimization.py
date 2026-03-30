"""
Optimization API — contextual bandit action selection and reward recording.

This is Layer 10 of the Growth OS: the online optimization engine.

Current implementation: epsilon-greedy + UCB bandit (safe, interpretable).
Migration path: Vowpal Wabbit CB → constrained RL.

Endpoints:
  POST /api/v1/optimization/select      — select best action from candidates
  POST /api/v1/optimization/reward      — record reward for a previous selection
  GET  /api/v1/optimization/arms        — get arm statistics for action type
  GET  /api/v1/optimization/log         — selection audit log
  GET  /api/v1/optimization/status      — optimizer status and readiness
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.core.bandit.action_selector import (
    select_action, record_reward, get_arm_summary, get_selection_log,
)

router = APIRouter()

VALID_ACTION_TYPES = {
    "channel_selection",
    "audience_segment",
    "creative_format",
    "budget_allocation",
    "content_angle",
    "cta_variant",
    "landing_variant",
}

REWARD_PRESETS = {
    "success": 1.0,
    "partial": 0.3,
    "neutral": 0.0,
    "failure": -1.0,
}


class ActionSelectRequest(BaseModel):
    action_type: str = Field(..., description=f"One of: {sorted(VALID_ACTION_TYPES)}")
    candidates: list[str] = Field(..., min_length=2, description="List of candidate actions (e.g. ['meta', 'tiktok', 'google'])")
    context_niche: str = Field(..., description="Niche context for the decision (e.g. 'fitness', 'ecommerce')")
    context_extra: dict = Field(default_factory=dict, description="Additional context (brand_stage, budget_tier, etc.)")
    model_version: str = "epsilon_greedy_v1"


class RewardRequest(BaseModel):
    selection_id: str = Field(..., description="ID returned from /select")
    reward: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Reward value (-1.0 to 1.0)")
    reward_preset: Optional[str] = Field(None, description="success | partial | neutral | failure")
    reward_type: str = Field("binary", description="binary | continuous | roas | cac_proxy")


@router.post("/select")
async def select_best_action(
    payload: ActionSelectRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Select the best action from candidates using the contextual bandit.

    Returns the selected action, confidence, policy (explore/exploit),
    and per-arm statistics for transparency.

    Log the selection_id and call POST /reward when you observe the outcome.
    """
    if payload.action_type not in VALID_ACTION_TYPES:
        raise HTTPException(400, f"action_type must be one of: {sorted(VALID_ACTION_TYPES)}")
    if len(set(payload.candidates)) < 2:
        raise HTTPException(400, "Provide at least 2 distinct candidates.")

    result = select_action(
        action_type=payload.action_type,
        candidates=list(set(payload.candidates)),
        context_niche=payload.context_niche,
        context_extra={**payload.context_extra, "user_id": str(current_user.id)},
        model_version=payload.model_version,
    )
    return {
        **result,
        "note": f"Record the outcome via POST /api/v1/optimization/reward with selection_id='{result['selection_id']}'",
    }


@router.post("/reward")
async def record_action_reward(
    payload: RewardRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Record the reward for a previous action selection.

    Use reward_preset for simple outcomes:
      success → +1.0 | partial → +0.3 | neutral → 0.0 | failure → -1.0

    Or provide a raw reward value between -1.0 and 1.0.

    This updates arm statistics and improves future action selection.
    """
    if payload.reward is None and payload.reward_preset is None:
        raise HTTPException(400, "Provide either reward (float) or reward_preset (success|partial|neutral|failure).")

    reward_value = payload.reward
    if payload.reward_preset:
        if payload.reward_preset not in REWARD_PRESETS:
            raise HTTPException(400, f"reward_preset must be one of: {list(REWARD_PRESETS.keys())}")
        reward_value = REWARD_PRESETS[payload.reward_preset]

    entry = record_reward(
        selection_id=payload.selection_id,
        reward=reward_value,
        reward_type=payload.reward_type,
    )
    if not entry:
        raise HTTPException(404, f"Selection '{payload.selection_id}' not found.")

    return {
        "selection_id": payload.selection_id,
        "reward": reward_value,
        "reward_type": payload.reward_type,
        "message": "Reward recorded. Arm statistics updated.",
        "action": entry["selected_action"],
        "action_type": entry["action_type"],
    }


@router.get("/arms")
async def get_arms(
    action_type: str = Query(..., description="Action type to inspect"),
    context_niche: str = Query(..., description="Niche context"),
    current_user=Depends(get_current_user),
) -> dict:
    """
    Get current arm statistics for an action type in a niche context.

    Shows observation counts, mean rewards, UCB scores, and exploitation readiness.
    """
    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(400, f"action_type must be one of: {sorted(VALID_ACTION_TYPES)}")

    return get_arm_summary(action_type=action_type, context_niche=context_niche)


@router.get("/log")
async def selection_log(
    action_type: Optional[str] = Query(None),
    context_niche: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict:
    """Audit log of all action selections and their rewards."""
    entries = get_selection_log(
        action_type=action_type,
        context_niche=context_niche,
        limit=limit,
    )
    rewarded = [e for e in entries if e.get("reward_recorded")]
    return {
        "entries": entries,
        "total": len(entries),
        "rewarded": len(rewarded),
        "pending_reward": len(entries) - len(rewarded),
    }


@router.get("/status")
async def optimizer_status(current_user=Depends(get_current_user)) -> dict:
    """Return optimizer status and readiness for each action type."""
    return {
        "optimizer": "epsilon_greedy_v1",
        "epsilon": 0.2,
        "min_observations_for_exploitation": 3,
        "action_types": list(VALID_ACTION_TYPES),
        "reward_presets": REWARD_PRESETS,
        "stage": "bandit",
        "upgrade_path": [
            {"stage": "bandit", "description": "Epsilon-greedy + UCB (current)", "status": "active"},
            {"stage": "vowpal_wabbit", "description": "Vowpal Wabbit contextual bandit", "status": "planned", "requires": ">100 observations per arm"},
            {"stage": "offline_rl", "description": "Offline RL policy via RLlib/SB3", "status": "planned", "requires": ">1000 labeled outcomes"},
            {"stage": "live_rl", "description": "Constrained live RL with safety rails", "status": "future", "requires": "Proven offline policy + compliance sign-off"},
        ],
        "safety_rules": [
            "Minimum 3 observations before exploitation",
            "20% exploration floor (epsilon=0.2)",
            "Maximum confidence cap: 0.9",
            "All selections logged with propensity for causal analysis",
            "No live budget changes without approval gate",
        ],
        "note": "This optimizer selects growth actions (channel, audience, creative, budget). "
                "It does NOT directly modify live campaigns — all reallocations require approval.",
    }
