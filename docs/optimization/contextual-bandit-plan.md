# Contextual Bandit Plan — Online Action Optimization

## Summary

The contextual bandit is the first stage of the platform's online optimization engine. It selects growth actions (which channel, audience, creative, or budget allocation) based on historical reward signals from the learning store.

## Why Bandits Before RL

Ad campaign environments have:
- **Delayed rewards** (7–30 day attribution windows)
- **Non-stationary dynamics** (platform CPMs change weekly)
- **Small data volumes** (early-stage brands have <100 measured outcomes)

Full RL requires stable reward signals and large datasets. Bandits work with 10–100 observations and degrade gracefully with less data.

## Stage 1: Epsilon-Greedy + UCB (Current)

**File:** `app/core/bandit/action_selector.py`

**Algorithm:**
```
P(random) = 0.20 (explore)
P(greedy) = 0.80 (exploit best-known arm)
UCB(arm) = mean_reward(arm) + α × √(ln(N) / n_arm)
```

**Action types:**
- `channel_selection` — meta | google | tiktok | linkedin | pinterest | snap
- `audience_segment` — which audience segment to prioritize
- `creative_format` — reels | static | carousel | video | story
- `budget_allocation` — which channel split to run
- `content_angle` — transformation | education | entertainment | social_proof
- `cta_variant` — shop_now | learn_more | get_started | book_now
- `landing_variant` — which landing page to route to

**API:**
```
POST /api/v1/optimization/select   # Select action
POST /api/v1/optimization/reward   # Record outcome
GET  /api/v1/optimization/arms     # Inspect arm stats
GET  /api/v1/optimization/log      # Audit log
GET  /api/v1/optimization/status   # Readiness status
```

## Stage 2: Vowpal Wabbit CB (Planned)

Trigger: >100 labeled observations per arm per niche.

VW CB with Doubly Robust (DR) estimator:
```bash
vw --cb_explore_adf --cb_type dr --epsilon 0.1 -f model.vw
```

Context features:
- niche, geography, business_stage, budget_tier
- day_of_week, month
- platform_maturity (account age, spend history)
- brand_engagement_history (recent organic performance)

Off-policy evaluation: Inverse Propensity Scoring (IPS) and Direct Method (DM).

## Stage 3: Offline RL (Planned, >1000 outcomes)

Use logged bandit data (with propensity scores) to train:
- Conservative Q-Learning (CQL) — safe pessimistic offline RL
- Implicit Q-Learning (IQL) — stable offline RL
- TD3+BC — behavior-constrained offline RL

Evaluate with Off-Policy Evaluation (OPE) before any live deployment.

## Stage 4: Live RL (Future)

Only deploy if:
1. Offline RL beats bandit baseline consistently in OPE
2. Hard budget guardrails implemented in environment
3. Workspace admin explicitly enables autonomous optimization
4. Full audit trail and rollback implemented

## Reward Signal Design

| Signal | Weight | Notes |
|--------|--------|-------|
| ROAS proxy | High | Requires conversion tracking |
| CPL (cost per lead) | High | B2B and lead-gen focus |
| Engagement rate | Medium | Content/organic optimization |
| CTR | Low | Vanity metric without conversion data |
| Session quality | Medium | PostHog session depth score |
| Follower growth | Low | Organic only, slow signal |

## Safety Rules

1. Epsilon floor 0.20 — always explore
2. Min 3 observations before exploitation
3. Max confidence 0.90 — never fully certain
4. All selections logged with propensity for causal analysis
5. No live campaign changes without human approval gate
6. Bandit selects actions; adapter layer executes; approval gate controls publishing

## Open-Source Tools Used

| Tool | Role |
|------|------|
| Current custom UCB | Stage 1 epsilon-greedy |
| Vowpal Wabbit | Stage 2 proper CB with feature context |
| Coba | Benchmarking and simulation |
| learn_to_pick | Fast prototyping of CB policies |
| RLlib | Stage 3 offline RL research |
| Stable-Baselines3 | Stage 3 offline RL simpler baseline |
| RecBole | Recommendation research and ranking baselines |
| Microsoft Recommenders | Production-minded ranking patterns |
