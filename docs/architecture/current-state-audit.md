# Current State Audit

**Date:** 2026-03-29
**Status:** Architecture v2 — Full closed-loop growth + advertising OS scaffolded

---

## Frontend Routes (all verified 200)

| Route | Status | Data Source |
|---|---|---|
| `/auth` | ✅ | Demo bypass JWT |
| `/onboarding` | ✅ | `POST /api/v1/brand/profile` |
| `/dashboard` | ✅ | `GET /api/v1/brand/overview` |
| `/dashboard/trends` | ✅ | `GET /api/v1/brand/trends` |
| `/dashboard/audience` | ✅ | `GET /api/v1/brand/audience` |
| `/dashboard/geo` | ✅ | `GET /api/v1/brand/geo` |
| `/dashboard/seo` | ✅ | `GET /api/v1/recommendations` (demo store) |
| `/dashboard/sites` | ✅ | `GET /api/v1/sites` (demo store) |
| `/dashboard/sites/onboard` | ✅ | `POST /api/v1/sites` (demo store) |
| `/dashboard/sites/[id]` | ✅ | `GET /api/v1/sites/{id}` (demo store) |
| `/dashboard/content` | ✅ | `GET /api/v1/content` (demo store) |
| `/dashboard/content/new` | ✅ | `GET /api/v1/brand/content-opportunities` + `POST /api/v1/content/briefs` |
| `/dashboard/approvals` | ✅ | `GET /api/v1/approvals` (demo store) |
| `/dashboard/reports` | ✅ | Export MD fixed — fetches full ReportDetail with `content_md` |
| `/dashboard/connectors` | ✅ | Real stage from credential_store, OAuth auth URL live |
| `/dashboard/activity` | ✅ | Static UI |
| `/dashboard/admin` | ✅ | `GET /health` |
| `/dashboard/experiments` | ✅ | Full UI — Overview/Strategies/Hypotheses/Patterns tabs |

---

## Backend Endpoint Map

### Brand Intelligence (no-DB, always works)
- `POST/GET /api/v1/brand/profile` → `storage/brand_store.json`
- `GET /api/v1/brand/overview|trends|audience|recommendations|content-opportunities|geo` → `niche_data.py` + `_meta` provenance block

### Ads Connectors (new)
- `GET /api/v1/ads-connectors` — list all platforms with real stage from credential_store
- `POST /api/v1/ads-connectors/{platform}/auth-url` — OAuth URL generation ✅ live
- `POST /api/v1/ads-connectors/{platform}/connect` — OAuth code exchange (stubs raise 501)
- `POST /api/v1/ads-connectors/{platform}/connect-token` — direct token input
- `DELETE /api/v1/ads-connectors/{platform}/disconnect` — credential removal
- `GET /api/v1/ads-connectors/{platform}/accounts` — list accessible ad accounts
- `POST /api/v1/ads-connectors/{platform}/link-account` — link chosen account
- `DELETE /api/v1/ads-connectors/{platform}/accounts/{account_id}` — unlink account

### Campaigns (new)
- `POST /api/v1/campaigns/drafts` — create draft (always PAUSED, never auto-published)
- `GET /api/v1/campaigns/drafts` — list with filters
- `GET /api/v1/campaigns/drafts/{id}` — get single draft
- `PATCH /api/v1/campaigns/drafts/{id}` — update (only if status=draft)
- `POST /api/v1/campaigns/drafts/{id}/submit` — → pending_approval
- `POST /api/v1/campaigns/drafts/{id}/publish` — requires approval_id
- `POST /api/v1/campaigns/reallocation` — budget move (50% cap enforced)
- `GET /api/v1/campaigns/reallocation` — list decisions
- `GET /api/v1/campaigns/audit-log` — immutable audit trail

### Learning Loop (existing, enhanced)
- `GET/POST /api/v1/learning/strategies` — strategy records with confidence_delta
- `PATCH /api/v1/learning/strategies/{id}/outcome` — auto-computes confidence_after + delta
- `GET/POST /api/v1/learning/hypotheses` — A/B hypothesis tracking
- `GET /api/v1/learning/patterns` — suppressed/promoted patterns
- `POST /api/v1/learning/run` — trigger learning sweep

### Optimization / Bandit (new)
- `POST /api/v1/optimization/select` — epsilon-greedy + UCB action selection
- `POST /api/v1/optimization/reward` — record outcome (reward presets)
- `GET /api/v1/optimization/arms` — arm statistics per action type
- `GET /api/v1/optimization/log` — selection audit log with propensity scores
- `GET /api/v1/optimization/status` — readiness, upgrade path, safety rules

### DB-primary with demo fallback
- All entity endpoints catch DB connection errors and fall back to `storage/demo_store.json`

---

## New Storage Files

| File | Contents |
|---|---|
| `storage/brand_store.json` | Brand profiles keyed by user_id |
| `storage/demo_store.json` | Sites, content assets, reports, approvals, recommendations |
| `storage/learning_store.json` | Strategy records, hypotheses, learning runs, suppressed/promoted patterns |
| `storage/bandit_store.json` | Arm stats per (niche, action_type, action_value), selection log |
| `storage/campaign_store.json` | Campaign drafts, creative/audience drafts, reallocation decisions, audit log |
| `storage/credentials.json` | Encrypted platform credentials — MUST be in .gitignore |

---

## Authentication

- Demo login: `demo@aicmo.os` / `Demo1234!` — bypasses DB entirely
- JWT issued for `DEMO_USER_ID = "00000000-0000-0000-0001-000000000001"`
- `_DemoUser` plain Python class used server-side (not SQLAlchemy model)

---

## Data Provenance

All brand intelligence endpoints now return `_meta` block:
```json
{
  "_meta": {
    "data_mode": "real_test | demo",
    "source": "niche_engine",
    "provenance": { "field": "user_provided | inferred | estimated | observed | demo" },
    "confidence": 0.7,
    "note": "..."
  }
}
```

---

## Architecture Maturity

| Layer | State |
|---|---|
| Brand intelligence | ✅ Production-ready (no-DB, niche engine) |
| Provenance tracking | ✅ All 7 brand endpoints |
| Export MD | ✅ Fixed — fetches ReportDetail before export |
| Experiments UI | ✅ Full page wired to learning loop API |
| Ads connector framework | ✅ Auth URL live; token exchange stubbed (501) |
| Credential store | ✅ Encrypted, file-based |
| Campaign lifecycle | ✅ Draft→approval→publish, immutable audit log |
| Learning loop | ✅ Confidence tracking, pattern suppression/promotion |
| Contextual bandit | ✅ Epsilon-greedy + UCB, propensity logging |
| PostHog analytics | ✅ Typed event library, no-op without key |
| PostgreSQL | ❌ Not connected — file stores used |
| Qdrant | ❌ Config ready, not integrated |
| Airbyte | ❌ Pattern documented, not implemented |
| Feast | ❌ Planned for bandit Stage 2 |
| MLflow | ❌ Planned for learning run tracking |
| Evidently | ❌ Planned for reward drift monitoring |
| Temporal / Dagster | ❌ Planned for scheduled jobs |
| Mautic | ❌ Planned for activation layer |
| Platform adapter implementations | ❌ All stubbed — raise 501 |
| Live RL | ❌ Research mode only |
