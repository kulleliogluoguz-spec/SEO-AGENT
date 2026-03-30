# Instagram + Website Onboarding

## Overview

The onboarding flow is the entry point to all platform intelligence. The quality of inputs directly determines the quality of recommendations — connecting a real Instagram handle or website URL shifts the platform from `demo` mode to `real_test` mode.

## 4-Step Onboarding Flow

### Step 1: Brand Basics
Fields:
- `brand_name` (required) — must be non-generic (not "Acme", "Demo", "Example") to trigger real_test mode
- `tagline` (optional)
- `description` (optional)

### Step 2: Instagram Handle
Fields:
- `instagram_handle` — @handle without the @
- `instagram_url` — full profile URL

**Effect on data mode:** Providing instagram_handle immediately sets `data_mode = "real_test"`.
All brand intelligence responses will include personalized provenance labels.

**Future:** When Instagram Graph API is connected, this handle triggers:
- Follower count, engagement rate, recent post performance pull
- Audience demographics (if Business/Creator account)
- Content format performance history

### Step 3: Business Details
Fields:
- `category` — selects from 9 supported niches
- `target_audience` — free-text description
- `primary_goal` — `growth | engagement | conversion | awareness`

**Niche inference:** Category keywords map to one of 9 niches:
`fitness | beauty | food | fashion | travel | tech | home | education | finance`

### Step 4: Website
Fields:
- `website_url` — full URL with https://

**Effect on data mode:** Providing website_url also triggers `real_test` mode.

**What it enables:**
- GEO/SEO audit with website-specific recommendations
- Organic traffic intelligence once GA4/GSC is connected
- AI discoverability scoring: structured data, entity clarity, citation density, content depth

---

## Data Mode Logic

```python
def _data_mode(profile):
    has_instagram = bool(profile.get("instagram_handle"))
    has_website = bool(profile.get("website_url"))
    has_real_name = bool(
        profile.get("brand_name") and
        profile["brand_name"].lower() not in ("acme", "demo", "example")
    )
    return "real_test" if (has_instagram or has_website or has_real_name) else "demo"
```

---

## Provenance Labels

After onboarding, every insight card shows a provenance chip:

| Label | Color | Meaning |
|---|---|---|
| `user_provided` | Blue | Entered directly in onboarding |
| `observed` | Green | Pulled from a live connected API |
| `inferred` | Teal | Derived by niche engine from your inputs |
| `estimated` | Amber | Industry benchmark / statistical estimate |
| `demo` | Gray | Seeded placeholder — connect account for real data |

---

## Frontend Flow

Route: `/onboarding`

Component: `apps/web/app/onboarding/page.tsx`

On completion:
- Calls `POST /api/v1/brand/profile`
- Saves profile to `storage/brand_store.json` keyed by `user_id`
- Redirects to `/dashboard`

Brand profile is then read by all 7 brand intelligence endpoints:
- `/overview`, `/trends`, `/audience`, `/recommendations`, `/content-opportunities`, `/geo`, `/media-plan`

---

## What Connecting Instagram Changes

### Before (demo mode)
- All insights are seeded niche data
- Gray "demo" chips on every card
- Persistent banner: "Connect your Instagram or website for personalized intelligence"
- Confidence: 0.5

### After (real_test mode)
- Insights are personalized to your brand name, handle, niche
- Provenance chips show `inferred` and `estimated` (not `demo`)
- Confidence: 0.7
- Note: "Intelligence derived from your brand inputs + niche engine. Connect analytics (GA4, GSC) for observed data."

### After Analytics Connected (future: `observed` mode)
- Real follower counts, engagement rates, post performance
- Provenance chips upgrade from `estimated` to `observed`
- Confidence: 0.85+
- Trend recommendations keyed to your actual content performance

---

## Upgrade Path

```
demo (no inputs)
  ↓ brand_name provided
real_test (inferred + estimated)
  ↓ instagram handle connected via Graph API
observed: social metrics
  ↓ GA4 + GSC connected
observed: traffic + search
  ↓ ads platform connected
observed: campaign performance
  ↓ learning loop has >100 outcomes
bandit-optimized recommendations
```

---

## Security Notes

- Instagram handles are stored in `brand_store.json` only — never logged or sent to external services
- No scraping is performed — Instagram data is only pulled via official Graph API (future)
- Website URLs are used only for GEO/SEO audit generation (no crawling in current version)
