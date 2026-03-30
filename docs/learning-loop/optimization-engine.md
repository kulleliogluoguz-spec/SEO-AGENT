# Learning Loop + Optimization Engine

## Overview

The learning loop is the core of the platform's intelligence. It transforms every strategy execution into a feedback signal that improves future recommendations.

## Architecture (6 Layers)

```
[1] Recommend → Niche Engine generates ranked recommendations
[2] Execute   → User approves + executes (campaign, content, audience test)
[3] Measure   → PostHog + platform API pulls outcome metrics
[4] Record    → Learning store records outcome + confidence delta
[5] Adapt     → Suppression/promotion updates pattern weights
[6] Optimize  → Bandit selects better actions for next cycle
```

## Data Stores

### learning_store.json

```json
{
  "strategy_records": [],      // Every recommendation + outcome
  "hypothesis_records": [],    // A/B tests with results
  "learning_runs": [],         // Periodic sweep metadata
  "suppressed_strategies": [], // Patterns with >60% failure rate
  "promoted_strategies": []    // Patterns with >70% success rate
}
```

Key fields per strategy record:
- `confidence_before` — starting confidence (0.7 default)
- `confidence_after` — updated after outcome
- `confidence_delta` — computed: after - before
- `strategy_version` — enables tracking across model/engine updates
- `expected_outcome` — predictions made at recommendation time

### Pattern Suppression Logic

After any outcome is recorded, the engine scans the last 10 instances of the same `{niche}:{strategy_type}` pattern:
- If failure_rate ≥ 0.60 → add to suppressed_strategies
- If success_rate ≥ 0.70 → add to promoted_strategies
- Minimum 3 samples required

### campaign_store.json

```json
{
  "campaign_drafts": [],          // All drafts with full lifecycle
  "creative_drafts": [],
  "audience_drafts": [],
  "reallocation_decisions": [],   // Every budget change proposed
  "audit_log": []                 // Immutable action log
}
```

### bandit_store.json

```json
{
  "arm_stats": {},        // Per (niche, action_type, action_value) stats
  "selection_log": []     // Every selection with propensity score
}
```

## Confidence Tracking

Confidence represents how strongly the system believes in a pattern:

| Outcome | Confidence Change |
|---------|-----------------|
| success | +0.10 (capped at 1.0) |
| partial | 0.00 (neutral) |
| failure | -0.15 (floored at 0.0) |

After suppression/promotion thresholds are crossed, the confidence of the pattern type is adjusted in future recommendations.

## MLflow Integration (Planned)

All learning runs will be tracked as MLflow experiments:
```python
with mlflow.start_run(experiment_id=exp_id, run_name=f"learning_sweep_{niche}"):
    mlflow.log_metrics({
        "success_rate": success_rate,
        "suppressed_count": len(suppressed),
        "promoted_count": len(promoted),
        "confidence_mean": mean_confidence,
    })
    mlflow.log_artifact("learning_store.json")
```

## Feast Integration (Planned)

Online features served to the bandit at decision time:
- `user_success_rate_{niche}` — recent win rate per niche
- `channel_cpl_{platform}` — recent CPL per platform
- `creative_ctr_{format}` — recent CTR per format
- `audience_conversion_rate_{segment}` — recent conversion per segment

## Evidently Integration (Planned)

Monitor for:
- Distribution drift in reward signals
- Stale patterns (promoted strategies that have stopped working)
- Data freshness (when did we last receive outcome signals?)

## Current State vs. Target

| Component | Current | Target |
|-----------|---------|--------|
| Strategy records | ✅ File-based | PostgreSQL |
| Hypothesis records | ✅ File-based | PostgreSQL |
| Pattern suppression | ✅ Rule-based | Feat. store weighted |
| Bandit | ✅ Epsilon-greedy | Vowpal Wabbit |
| Experiment tracking | ❌ | MLflow |
| Feature store | ❌ | Feast |
| Drift monitoring | ❌ | Evidently |
