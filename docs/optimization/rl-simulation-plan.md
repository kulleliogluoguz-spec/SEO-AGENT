# RL Simulation Plan — Offline Policy Research

## Summary

Full reinforcement learning is the final stage of the optimization engine. This document defines the simulation architecture, evaluation methodology, and safety gates required before any live RL deployment.

## Why Simulation First

Live ad systems are:
- Expensive to experiment with (real money, real audiences)
- Non-stationary (platform dynamics shift over time)
- Delayed-reward (attribution windows prevent fast feedback)

RL agents must be validated in simulation before touching live campaigns.

## Simulated Environment Architecture

### State Space

```
s = {
  niche: str,
  budget_tier: float,
  platform_maturity: float,  # 0.0 (new) to 1.0 (established)
  audience_saturation: float,
  creative_fatigue: float,
  day_of_week: int,
  month: int,
  recent_cpl: float,
  recent_ctr: float,
  recent_roas: float,
  competitor_intensity: float,
}
```

### Action Space

```
a = {
  channel: str,
  audience_segment: str,
  creative_format: str,
  daily_budget_usd: float,
  bid_strategy: str,
}
```

### Reward Function

```
R = w_roas × ROAS_normalized
  + w_cac  × (1 / CAC_normalized)
  + w_reach × reach_efficiency
  - w_risk  × risk_penalty
```

Risk penalty: Applied when budget utilization > 95% or CPL spikes >40% vs. baseline.

### Data Sources for Simulation

1. Historical strategy outcome records (learning_store.py)
2. Bandit selection log with propensity scores
3. Industry benchmark data (niche_data.py)
4. Platform CPM/CPC range distributions

## Offline RL Algorithms to Evaluate

| Algorithm | Library | Notes |
|-----------|---------|-------|
| CQL (Conservative Q-Learning) | RLlib | Pessimistic, safe for offline data |
| IQL (Implicit Q-Learning) | RLlib | Stable offline training |
| TD3+BC | Stable-Baselines3 | Behavior-constrained, close to data distribution |
| BCQ (Batch Constrained Q-learning) | Custom | Classic offline RL baseline |

## Off-Policy Evaluation (OPE)

Before any live deployment, offline RL policy must beat bandit baseline in OPE:

| Method | Description |
|--------|-------------|
| Direct Method (DM) | Fit reward model, predict on policy actions |
| Inverse Propensity Scoring (IPS) | Reweight bandit log by policy probabilities |
| Doubly Robust (DR) | Combine DM + IPS for variance reduction |

Threshold: DR estimate must exceed bandit baseline by >10% over 30-day simulation.

## Guardrails for Live Deployment

1. Hard budget floor: Cannot reduce daily budget below $5 or platform minimum
2. Hard budget ceiling: Cannot exceed workspace monthly cap
3. Maximum daily budget change: 20% per day (gradual ramping)
4. Kill switch: Workspace admin can disable live RL at any time
5. Approval gate: All budget changes >$50/day require human approval
6. Rollback: Every optimization action has a documented rollback plan
7. Monitoring: Evidently drift detection on reward signal distribution

## Integration with Open-Source Stack

| Tool | Integration Point |
|------|-----------------|
| RLlib | Primary RL research and offline training |
| Stable-Baselines3 | Simpler baseline comparisons |
| Feast | Online feature store for state observations |
| MLflow | Experiment tracking, model versioning, policy registry |
| Evidently | Drift monitoring on reward distributions |
| Dagster | Scheduled offline training pipelines |

## Timeline

This plan is currently in **research mode** — no live RL is deployed.

Live RL requires:
1. >1000 labeled strategy outcomes in learning_store
2. Stable reward model with <15% estimation error
3. Bandit system running for >90 days
4. OPE validation passing on held-out data
5. Compliance and legal review of autonomous budget management
