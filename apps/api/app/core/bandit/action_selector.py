"""
Contextual Bandit Action Selector — Layer 10 of the Growth OS.

This module implements the first stage of the optimization engine:
a simple epsilon-greedy contextual bandit that selects growth actions
based on historical reward signals from the learning store.

Architecture:
  Stage 1 (current): Epsilon-greedy bandit with UCB fallback
  Stage 2 (next):    Vowpal Wabbit CB for proper contextual decisions
  Stage 3 (later):   Offline RL policy via RLlib / Stable-Baselines3

Action types supported:
  - channel_selection     (which ad platform to prioritize)
  - audience_segment      (which segment to target first)
  - creative_format       (Reels vs. static vs. carousel etc.)
  - budget_allocation     (how to split budget across channels)
  - content_angle         (hook/narrative approach)
  - cta_variant           (call to action wording/type)
  - landing_variant       (which landing page to route to)

Reward signals (from strategy outcome records):
  - success  → +1.0
  - partial  → +0.3
  - failure  → -1.0
  - no data  → 0.0 (explore)

Safety rules:
  - Minimum 3 observations before exploitation
  - Epsilon floor: 0.15 (always 15% exploration)
  - Maximum confidence cap: 0.9 (never 100% sure)
  - All selections logged for propensity scoring
"""
from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "bandit_store.json"

EPSILON = 0.2          # Exploration rate (20% random, 80% greedy)
MIN_OBSERVATIONS = 3   # Minimum before exploitation
UCB_ALPHA = 1.0        # UCB confidence width


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        return {"arm_stats": {}, "selection_log": []}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"arm_stats": {}, "selection_log": []}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Arm statistics ─────────────────────────────────────────────────────────────

def _arm_key(action_type: str, action_value: str, context_niche: str) -> str:
    return f"{context_niche}:{action_type}:{action_value}"


def _get_arm(data: dict, key: str) -> dict:
    return data["arm_stats"].get(key, {"n": 0, "total_reward": 0.0, "mean_reward": 0.0, "ucb": float("inf")})


def _update_arm(data: dict, key: str, reward: float) -> None:
    arm = _get_arm(data, key)
    arm["n"] += 1
    arm["total_reward"] += reward
    arm["mean_reward"] = arm["total_reward"] / arm["n"]
    # UCB1 score (used for tie-breaking and initial exploration)
    total_n = sum(a["n"] for a in data["arm_stats"].values()) + 1
    if arm["n"] >= MIN_OBSERVATIONS:
        arm["ucb"] = arm["mean_reward"] + UCB_ALPHA * math.sqrt(math.log(total_n) / arm["n"])
    else:
        arm["ucb"] = float("inf")  # Always explore under-observed arms
    data["arm_stats"][key] = arm


# ── Action selection ──────────────────────────────────────────────────────────

def select_action(
    action_type: str,
    candidates: list[str],
    context_niche: str,
    context_extra: Optional[dict] = None,
    model_version: str = "epsilon_greedy_v1",
) -> dict:
    """
    Select an action from candidates using epsilon-greedy + UCB.

    Returns:
      {
        "selected_action": str,
        "action_type": str,
        "context_niche": str,
        "selection_id": str,       # Log this to record rewards later
        "policy": str,             # "explore" | "exploit"
        "confidence": float,
        "arm_stats": dict,
        "model_version": str,
      }
    """
    if not candidates:
        raise ValueError("candidates list cannot be empty")

    data = _load()
    selection_id = str(uuid.uuid4())
    policy = "explore"
    selected = random.choice(candidates)

    # Epsilon: explore randomly
    if random.random() < EPSILON:
        policy = "explore"
        selected = random.choice(candidates)
    else:
        # Exploit: pick arm with highest UCB score
        scores = []
        for c in candidates:
            key = _arm_key(action_type, c, context_niche)
            arm = _get_arm(data, key)
            scores.append((c, arm["ucb"]))
        best = max(scores, key=lambda x: x[1])
        selected = best[0]
        policy = "explore" if best[1] == float("inf") else "exploit"

    # Compute confidence for selected arm
    sel_key = _arm_key(action_type, selected, context_niche)
    sel_arm = _get_arm(data, sel_key)
    confidence = min(0.9, max(0.1, sel_arm["mean_reward"] * 0.9 + 0.1)) if sel_arm["n"] >= MIN_OBSERVATIONS else 0.1

    # Log selection
    log_entry = {
        "id": selection_id,
        "action_type": action_type,
        "selected_action": selected,
        "candidates": candidates,
        "context_niche": context_niche,
        "context_extra": context_extra or {},
        "policy": policy,
        "confidence": confidence,
        "model_version": model_version,
        "reward_recorded": False,
        "reward": None,
        "timestamp": _now(),
    }
    data["selection_log"].append(log_entry)
    _save(data)

    # Return arm stats for all candidates (for transparency)
    arm_stats_out = {}
    for c in candidates:
        key = _arm_key(action_type, c, context_niche)
        arm = _get_arm(data, key)
        arm_stats_out[c] = {
            "n": arm["n"],
            "mean_reward": round(arm["mean_reward"], 3),
            "ucb": round(arm["ucb"], 3) if arm["ucb"] != float("inf") else None,
        }

    return {
        "selected_action": selected,
        "action_type": action_type,
        "context_niche": context_niche,
        "selection_id": selection_id,
        "policy": policy,
        "confidence": round(confidence, 3),
        "arm_stats": arm_stats_out,
        "model_version": model_version,
    }


def record_reward(
    selection_id: str,
    reward: float,
    reward_type: str = "binary",  # binary | continuous | roas | cac_proxy
) -> Optional[dict]:
    """
    Record the reward for a previous action selection.

    reward:
      +1.0 = success / positive outcome
      +0.3 = partial success
       0.0 = neutral / no data
      -1.0 = failure

    This updates the arm statistics and improves future selections.
    """
    data = _load()
    for entry in data["selection_log"]:
        if entry["id"] == selection_id:
            if entry["reward_recorded"]:
                return entry  # Already recorded
            entry["reward"] = reward
            entry["reward_type"] = reward_type
            entry["reward_recorded"] = True
            entry["reward_timestamp"] = _now()

            # Update arm stats
            key = _arm_key(entry["action_type"], entry["selected_action"], entry["context_niche"])
            _update_arm(data, key, reward)
            _save(data)
            return entry
    return None


def get_arm_summary(action_type: str, context_niche: str) -> dict:
    """Get the current arm statistics for an action type in a niche context."""
    data = _load()
    arms = {
        k.split(":")[-1]: v
        for k, v in data["arm_stats"].items()
        if k.startswith(f"{context_niche}:{action_type}:")
    }
    total_n = sum(a["n"] for a in arms.values())
    return {
        "action_type": action_type,
        "context_niche": context_niche,
        "arms": arms,
        "total_observations": total_n,
        "exploitation_ready": total_n >= MIN_OBSERVATIONS * len(arms) if arms else False,
        "epsilon": EPSILON,
        "model_version": "epsilon_greedy_v1",
        "next_upgrade": "Vowpal Wabbit CB when >100 observations per arm.",
    }


def get_selection_log(
    action_type: Optional[str] = None,
    context_niche: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Return recent action selections for audit/debugging."""
    data = _load()
    entries = data["selection_log"]
    if action_type:
        entries = [e for e in entries if e["action_type"] == action_type]
    if context_niche:
        entries = [e for e in entries if e["context_niche"] == context_niche]
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]
