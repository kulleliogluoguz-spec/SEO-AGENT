# ADR-010: Official Ads Connectors — Staged Capability with Full Audit Trail

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The platform must support live ad campaign creation via official APIs for Meta, Google, TikTok, LinkedIn, Pinterest, and Snap. The naive approach (direct API integration without safety layers) would allow the system to spend real money without explicit human oversight.

The platform must also handle:
- OAuth2 token acquisition, storage, and refresh
- Secure credential persistence (no tokens in env vars at runtime)
- Account linking (one user can have multiple ad accounts per platform)
- Staged capability unlock (Planning → Account Linked → Draft → Published)
- Full audit trail of every action taken

## Decision

### Credential Architecture

All OAuth tokens are stored in `storage/credentials.json` (file-based, base64-encoded for v0.1). Production migration: encrypted Postgres column or HashiCorp Vault.

The `credential_store.py` module provides:
- `store_credential(user_id, platform, access_token, ...)` — base64-encoded storage
- `get_credential(user_id, platform)` — decoded retrieval (never logged)
- `delete_credential(user_id, platform)` — irreversible disconnect
- `link_account(user_id, platform, account_id, ...)` — links a specific ad account
- `get_platform_stage(user_id, platform)` — returns current capability stage

### Connection Flow

```
POST /{platform}/auth-url      → Generate OAuth URL (requires CLIENT_ID in env)
  ↓ User authorizes in browser
POST /{platform}/connect       → Exchange code → store encrypted token → stage: auth_verified
GET  /{platform}/accounts      → List accessible accounts from platform API
POST /{platform}/link-account  → Link chosen account → stage: account_linked
POST /campaigns/drafts         → Create campaign draft (requires account_linked)
POST /campaigns/drafts/{id}/submit → Submit for approval
POST /campaigns/drafts/{id}/publish → Publish (requires approval_id)
```

### Audit Trail

Every action is logged to `campaign_store.py` audit_log with:
- action type, entity_id, user_id, timestamp, details

This log is immutable and append-only (no delete endpoint).

### Adapter Interface

All 6 platform adapters implement `BaseAdsAdapter`:
- `get_auth_url(redirect_uri, state)` — platform-specific OAuth URL
- `exchange_code(code, redirect_uri)` — token exchange (async)
- `list_accounts()` — accessible accounts (async, READ_REPORT stage)
- `create_campaign(draft)` — create PAUSED campaign (async, DRAFT_CREATE stage)
- `publish_campaign(platform_campaign_id)` — activate (APPROVAL_GATE stage)
- `get_metrics(campaign_id, date_range)` — reporting pull (READ_REPORT+)

## New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ads-connectors/{platform}/connect-token` | Store long-lived token directly |
| DELETE | `/api/v1/ads-connectors/{platform}/disconnect` | Remove credentials |
| POST | `/api/v1/ads-connectors/{platform}/link-account` | Link ad account |
| DELETE | `/api/v1/ads-connectors/{platform}/accounts/{id}` | Unlink account |
| POST | `/api/v1/campaigns/drafts` | Create campaign draft |
| GET | `/api/v1/campaigns/drafts` | List drafts |
| PATCH | `/api/v1/campaigns/drafts/{id}` | Update draft |
| POST | `/api/v1/campaigns/drafts/{id}/submit` | Submit for approval |
| POST | `/api/v1/campaigns/drafts/{id}/publish` | Publish (post-approval) |
| POST | `/api/v1/campaigns/reallocation` | Propose budget reallocation |
| GET | `/api/v1/campaigns/audit-log` | Full audit trail |

## Safety Invariants

1. No campaign is ever published without `approval_id` from the Approvals workflow
2. Maximum single budget reallocation: 50% of current budget
3. All credential operations are logged
4. Tokens are never returned in API responses (only `has_access_token: true/false`)
5. `LIVE_OPTIMIZE` stage requires explicit workspace admin opt-in

## Consequences

**Positive:** Full credential lifecycle management. Real account linking. Approval-gated publishing. Audit trail for compliance.

**Negative:** Requires platform app review before production use (1–4 weeks per platform). Credential storage needs encryption upgrade before production.

## Related

- `app/adapters/base.py` — adapter interface
- `app/adapters/{meta,google,tiktok,linkedin,pinterest,snap}.py` — platform adapters
- `app/core/store/credential_store.py` — credential persistence
- `app/core/store/campaign_store.py` — campaign + audit persistence
- `app/api/endpoints/ads_connectors.py` — connector endpoints
- `app/api/endpoints/campaigns.py` — campaign draft endpoints
