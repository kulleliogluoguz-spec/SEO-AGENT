# ADR-013: Constrained Auto-Reallocation — Safety-First Budget Optimization

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

Budget reallocation is one of the highest-value and highest-risk operations in the platform. Reallocating budget from underperforming channels to overperforming ones can significantly improve ROAS. But unrestricted reallocation can:

- Exhaust budget on a single platform (concentration risk)
- Reallocate on statistically insignificant data (noise-chasing)
- Move budget mid-flight and invalidate A/B tests
- Violate platform-specific minimum budget requirements
- Trigger approval violations if done without human sign-off

## Decision

All budget reallocation is subject to hard safety constraints enforced by the `campaign_store.py` and the campaigns API.

### Constraints

| Constraint | Value | Rationale |
|---|---|---|
| Max single reallocation | 50% of current budget | Prevents catastrophic misallocation |
| Min impressions before reallocation | 1,000 | Ensures statistical significance |
| Min observation window | 7 days | Avoids recency bias |
| Approval requirement | Always for >$50/day change | Maintains human oversight |
| Floor protection | Platform minimum budget | Prevents campaigns from going dark |
| Ceiling protection | Workspace budget cap | Prevents overspend |

### Decision Record Schema

Every reallocation decision includes:
```json
{
  "old_allocation": { "platform": "meta", "budget_usd": 100 },
  "new_allocation": { "platform": "meta", "budget_usd": 140 },
  "delta_usd": 40,
  "delta_pct": 40.0,
  "reason": "Meta CPL dropped 23% vs. previous 14-day average",
  "supporting_metrics": { "impressions": 12400, "cpl": 18.4, "cpl_baseline": 23.9 },
  "confidence": 0.74,
  "requires_approval": true,
  "rollback_plan": "Revert to $100/day if CPL rises above $25 within 7 days",
  "status": "pending_approval"
}
```

### Automation Policy

| Condition | Action |
|---|---|
| Change ≤ $20/day AND confidence ≥ 0.80 | Auto-apply (no approval required) |
| Change $20–$50/day OR confidence < 0.80 | Requires human approval |
| Change > $50/day | Always requires approval + written justification |
| Change > 50% of current budget | Blocked — must split into multiple smaller moves |

### Rollback

Every applied reallocation has a rollback record. The system can:
1. Detect outcome degradation (CPL increase, ROAS drop) within the measurement window
2. Surface a rollback recommendation via the Approvals queue
3. Apply rollback on approval

### Integration with Bandit

The bandit (ADR-011) selects the optimal channel/audience/creative action. The reallocation engine:
1. Receives the bandit's selected action
2. Maps it to a concrete budget delta
3. Runs constraint validation
4. If approved, fires the platform API to update the campaign budget

## Consequences

**Positive:** Reallocation is safe, auditable, and explainable. Every decision has a rollback plan. Human oversight maintained for significant changes.

**Negative:** Approval friction slows optimization cycle for large changes. 50% cap prevents aggressive optimization in clear winner scenarios. Statistical thresholds mean the system waits before acting on early signals.

## Related

- `app/core/store/campaign_store.py` — reallocation decision storage
- `app/api/endpoints/campaigns.py` — reallocation API
- ADR-011 — bandit selects actions that feed reallocation
- ADR-010 — adapter layer executes approved reallocations
