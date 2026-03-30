# Official Ads API Strategy

## Supported Platforms

| Platform | API | Review Required | Timeline |
|----------|-----|-----------------|----------|
| Meta (Facebook + Instagram) | Marketing API v20+ | Yes (ads_management scope) | 1–5 business days |
| Google Ads | Google Ads API v17+ | Yes (developer token) | Basic: immediate; Standard: 1–2 weeks |
| TikTok for Business | Marketing API v1.3+ | Yes | 3–7 business days |
| LinkedIn | Marketing Solutions API v202404+ | Yes (MDP access) | 1–4 weeks |
| Pinterest | Ads API v5+ | No (ads:read/write available) | Immediate |
| Snap | Marketing API v1+ | Yes | 2–5 business days |

## Connection Flow

### Step 1: Server Configuration
Set environment variables:
```
META_CLIENT_ID=xxx
META_CLIENT_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_DEVELOPER_TOKEN=xxx
TIKTOK_CLIENT_ID=xxx
TIKTOK_CLIENT_SECRET=xxx
LINKEDIN_CLIENT_ID=xxx
LINKEDIN_CLIENT_SECRET=xxx
PINTEREST_CLIENT_ID=xxx
PINTEREST_CLIENT_SECRET=xxx
SNAP_CLIENT_ID=xxx
SNAP_CLIENT_SECRET=xxx
ENCRYPTION_KEY=32_byte_hex_string
```

### Step 2: OAuth Flow
```
POST /api/v1/ads-connectors/{platform}/auth-url
  → Returns auth_url for browser redirect

POST /api/v1/ads-connectors/{platform}/connect
  → Exchanges code → stores token → stage: auth_verified

POST /api/v1/ads-connectors/{platform}/connect-token  (alternative)
  → Accepts long-lived token directly
```

### Step 3: Account Linking
```
GET  /api/v1/ads-connectors/{platform}/accounts
  → Lists accessible ad accounts

POST /api/v1/ads-connectors/{platform}/link-account
  → Links chosen account → stage: account_linked
```

### Step 4: Campaign Draft Creation
```
POST /api/v1/campaigns/drafts
  → Creates PAUSED draft (never auto-published)

POST /api/v1/campaigns/drafts/{id}/submit
  → Moves to pending_approval

POST /api/v1/approvals/{id}/action (approve)
  → Grants publish permission

POST /api/v1/campaigns/drafts/{id}/publish
  → Publishes to platform (requires approval_id)
```

## Platform-Specific Notes

### Meta Marketing API

Required scopes: `ads_management`, `ads_read`, `business_management`, `pages_show_list`

Campaign structure:
- Campaign → Ad Set (audience, budget) → Ad (creative)
- Create campaign with `status=PAUSED`
- Budget set at Ad Set level (daily or lifetime)
- Objective: `AWARENESS`, `TRAFFIC`, `ENGAGEMENT`, `LEADS`, `SALES`, `APP_PROMOTION`

Rate limits: ~200 calls/hour per access token.

### Google Ads API

Required: developer token (Basic access for testing, Standard for production).

Campaign types implemented: Search RSA, Performance Max, Display, Video.
Budget: Campaign-level daily budget in micros (e.g., $10 = 10_000_000 micros).

Rate limits: Quota-based, varies by account spend.

### TikTok for Business

Required scopes: `ad.create`, `campaign.create`, `ad_account.readonly`

Campaign structure mirrors Meta: Campaign → Ad Group → Ad.
Minimum daily budget: $20/day at Ad Group level.

### LinkedIn Marketing Solutions

Required: `rw_ads`, `r_ads_reporting`, `r_organization_social`

Campaign structure: Campaign Group → Campaign → Creative.
B2B targeting: job title, seniority, company size, industry.
Minimum daily budget: $10/day.

### Pinterest Ads API

No extended review required. `ads:read` and `ads:write` scopes.

Campaign structure: Campaign → Ad Group → Ad (Promoted Pin).
Best for: fashion, beauty, food, home, travel.

### Snap Marketing API

Required: `snapchat-marketing-api` access from kit.snapchat.com.

Campaign structure: Campaign → Ad Squad → Ad.
Best for: Gen Z audiences, fashion, beauty, creator content.

## Adapter Implementation Status

| Platform | Auth URL | Token Exchange | List Accounts | Create Draft | Publish |
|----------|----------|----------------|---------------|--------------|---------|
| Meta | ✅ | Stub | Stub | Stub | Stub |
| Google | ✅ | Stub | Stub | Stub | Stub |
| TikTok | ✅ | Stub | Stub | Stub | Stub |
| LinkedIn | ✅ | Stub | Stub | Stub | Stub |
| Pinterest | ✅ | Stub | Stub | Stub | Stub |
| Snap | ✅ | Stub | Stub | Stub | Stub |

Stubs raise `NotImplementedError` — the platform connection flow handles this gracefully with a `501` response that explains what's needed.

## Security Requirements for Production

1. `ENCRYPTION_KEY` must be set (32-byte hex) — credentials stored encrypted
2. Credentials file (`storage/credentials.json`) must be in `.gitignore`
3. HTTPS required for OAuth redirect URIs
4. Token refresh must run on a schedule (Dagster/Temporal job)
5. Access token expiry must be tracked (`expires_at` field in credential store)
