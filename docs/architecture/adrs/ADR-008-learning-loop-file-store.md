# ADR-008: Learning Loop — File-Based Store with MLflow Migration Path

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The platform needs a closed-loop growth intelligence system: recommend strategies, track outcomes, suppress failures, amplify successes. This is the core value-add over a static rules engine.

Production-grade experiment tracking typically uses MLflow or Feast. However:
- MLflow adds Docker service dependencies and infrastructure complexity
- Feast requires a feature store backend (Redis or BigQuery)
- Neither is appropriate for a zero-dependency self-hosted v0.1

The learning system must work on day-one without any external infrastructure, while having a clear migration path for production deployments.

## Decision

Use a JSON file store (`storage/learning_store.json`) for v0.1 with the following schema:

```
{
  "strategy_records":      [],  // Recommendations + measured outcomes
  "hypothesis_records":    [],  // A/B tests and experiment results
  "learning_runs":         [],  // Periodic learning sweep metadata
  "suppressed_strategies": [],  // Patterns with >60% failure rate
  "promoted_strategies":   []   // Patterns with >70% success rate
}
```

**Pattern suppression logic:** After any outcome is recorded, check the last 10 instances of the same `{niche}:{strategy_type}` pattern. If failure rate ≥ 0.6, add to suppressed list. If success rate ≥ 0.7, add to promoted list. Minimum 3 samples required before any suppression/promotion.

**API surface:**
- `GET  /api/v1/learning/summary` — dashboard metrics
- `GET/POST /api/v1/learning/strategies` — strategy records
- `POST /api/v1/learning/strategies/{id}/outcome` — outcome recording
- `GET/POST /api/v1/learning/hypotheses` — hypothesis tracking
- `POST /api/v1/learning/hypotheses/{id}/result` — experiment results
- `GET /api/v1/learning/suppressed` — suppressed patterns
- `GET /api/v1/learning/promoted` — promoted patterns

## Migration Path

When ready for production:
1. Replace `learning_store.py` with `learning_store_pg.py` using PostgreSQL tables
2. Optionally add MLflow as experiment tracking backend for hypothesis records
3. No API surface changes required — store is behind a clean function interface

## Consequences

**Positive:**
- Zero additional infrastructure in v0.1
- Full learning loop works from day one
- Pattern suppression and promotion are computable from day 3 of use
- Clean interface makes backend swap straightforward

**Negative:**
- JSON file is not concurrent-write safe (single writer at a time)
- No time-series querying — only last-N pattern analysis
- File must be backed up manually (not in a DB transaction)

## Related

- `app/core/store/learning_store.py` — implementation
- `app/api/endpoints/learning.py` — API layer
- `apps/web/app/dashboard/experiments/page.tsx` — frontend (planned)
