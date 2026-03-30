# ADR-011: Contextual Bandits Before RL — Safe Online Optimization Path

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The platform must optimize growth actions (channel selection, audience targeting, creative format, budget allocation) based on observed outcomes. The temptation is to jump directly to Reinforcement Learning. This is wrong for three reasons:

1. **Delayed rewards:** Ad campaigns have 7–30 day attribution windows. RL agents cannot learn from fast feedback loops in this environment.
2. **Non-stationarity:** Platform algorithms, CPM prices, and audience behavior change weekly. An RL policy trained last month may be wrong today.
3. **Production risk:** RL agents optimize for reward signals. If the reward signal is improperly specified (e.g., CTR instead of actual revenue), the agent will exploit it — spending real money on vanity metrics.

Contextual bandits are the correct intermediate step because:
- They can handle exploration/exploitation with sparse data
- They are interpretable (each arm has a mean reward and confidence interval)
- They degrade gracefully (epsilon floor prevents full exploitation on small samples)
- They can be upgraded to full RL when sufficient labeled data exists

## Decision

### Stage 1 (current): Epsilon-Greedy + UCB Bandit

Implementation: `app/core/bandit/action_selector.py`

Algorithm:
- Epsilon = 0.20 (20% random exploration, 80% greedy)
- UCB1 score = mean_reward + α × √(ln(total_pulls) / arm_pulls)
- Minimum 3 observations before exploitation
- Confidence capped at 0.90 (never fully certain)

Action types supported:
- `channel_selection` — which platform to spend on
- `audience_segment` — which audience to target
- `creative_format` — ad format choice
- `budget_allocation` — budget split
- `content_angle` — hook/narrative
- `cta_variant` — call to action
- `landing_variant` — landing page route

Reward schema:
- +1.0 = success
- +0.3 = partial success
- 0.0 = neutral / no data
- -1.0 = failure

### Stage 2 (planned): Vowpal Wabbit CB

Trigger: >100 labeled observations per arm per niche.

VW provides proper contextual bandit learning with feature vectors, importance-weighted updates, and off-policy evaluation support. This is where the learning becomes genuinely personalized per brand context.

Configuration:
```bash
vw --cb_explore_adf --epsilon 0.1 --cb_type dr -f model.vw
```

Features per context:
- niche, geography, business_stage, budget_tier
- day_of_week, month, platform_maturity
- previous_arm_rewards, brand_engagement_history

### Stage 3 (planned): Offline RL via RLlib / Stable-Baselines3

Trigger: >1000 labeled outcomes, stable reward model, offline policy evaluation passing.

Use offline RL (Conservative Q-Learning, IQL, or TD3+BC) trained on historical bandit logs. Evaluate with Off-Policy Evaluation (OPE) methods (DR, DM, IPS) before any live deployment.

### Stage 4 (future): Constrained Live RL

Only deploy if:
- Offline RL consistently beats bandit baseline in OPE
- Hard budget guardrails are implemented in the environment
- Workspace admin explicitly enables
- Full audit trail and rollback mechanism in place

## Consequences

**Positive:** Safe incremental path from heuristics → bandits → RL. Each stage is interpretable and auditable. Epsilon floor ensures exploration never stops. Selection log provides propensity scores for causal analysis.

**Negative:** Epsilon-greedy is not truly contextual (features not used in Stage 1). VW requires additional infrastructure. Full RL requires significant labeled data corpus.

## Related

- `app/core/bandit/action_selector.py` — Stage 1 implementation
- `app/api/endpoints/optimization.py` — bandit API
- ADR-013 — constrained auto-reallocation (bandit output feeds reallocation)
- ADR-008 — learning loop (outcome signals feed bandit rewards)
