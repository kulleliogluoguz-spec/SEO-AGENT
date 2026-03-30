# ADR-007: Ads Connector Capability Stages — Safety-First Progressive Access

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

Ad platform APIs (Meta, Google, TikTok, LinkedIn, Pinterest, Snap) can create, modify, and spend real money on campaigns if given the correct OAuth scopes. A system that automatically publishes campaigns without explicit human approval would be unacceptable for the target user base (growth teams, solo operators, agencies).

Additionally, all six platforms require either developer account applications or app review processes (ranging from same-day to 4 weeks). This means full API integration cannot be developed and tested in one pass — it must be staged.

## Decision

Implement a five-stage capability model for all ad platform connectors:

| Stage | Label | What's Possible |
|---|---|---|
| A — `planning` | Planning only | Channel recommendations, media plans, budget estimates. Zero API calls. |
| B — `read_report` | Read & Report | Pull account structure, campaign metrics, audience lists. Read-only. |
| C — `draft_create` | Draft Campaigns | Create campaigns/ads in `PAUSED` state. Never published automatically. |
| D — `approval_gate` | Approval Gated | Campaigns go live only after explicit human approval in the Approvals queue. |
| E — `live_optimize` | Live Optimization | Automated budget and bid adjustments on already-running campaigns. |

All connectors ship at Stage A (planning only). Stage advancement requires:
1. Server-side credential storage (encrypted)
2. Platform app review completion
3. Explicit workspace-level opt-in by a workspace admin

## Adapter Base Pattern

All adapters extend `BaseAdsAdapter` from `app/adapters/base.py`:
- `capability_summary()` — returns stage, can_read, can_create_drafts, can_publish flags
- `get_auth_url()` — generates platform OAuth URL (requires `client_id` in env)
- `exchange_code()` — exchanges OAuth code for token (requires encrypted credential store)
- `list_accounts()` — returns accessible ad accounts (Stage B+)

The `ADAPTER_REGISTRY` in `app/adapters/__init__.py` maps platform keys to adapter classes.

## Consequences

**Positive:**
- Teams cannot accidentally spend money via the AI system
- Clear upgrade path for users ready to advance stages
- App review requirements are surfaced explicitly in the UI
- All ad platform endpoints documented with `POST /{platform}/auth-url` → `/connect` flow

**Negative:**
- Stages C–E require credential storage infrastructure (ENCRYPTION_KEY + secrets manager) not yet implemented
- `/connect` and `/accounts` endpoints return 501/403 until credential storage is in place

## Related

- `app/adapters/` — adapter implementations
- `app/api/endpoints/ads_connectors.py` — API endpoints
- `apps/web/app/dashboard/connectors/page.tsx` — frontend UI
- ADR-005: Connector SDK (data connectors, separate system)
