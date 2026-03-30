# ADR-014: Real Test Mode Over Demo — Data Provenance and Trust

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The platform was initially built with heavy demo assumptions (hardcoded "Acme Growth" workspace, seeded JSON data, no real account signals). This is acceptable for initial development but becomes a trust problem:

- Users cannot tell which insights are real vs. fabricated
- Demo data can create false confidence in recommendations
- Onboarding with a real Instagram account should immediately change the intelligence quality

## Decision

All API responses from brand intelligence endpoints include a `_meta` block:

```json
{
  "_meta": {
    "data_mode": "real_test",
    "source": "niche_engine",
    "provenance": {
      "brand_inputs": "user_provided",
      "niche_intelligence": "inferred",
      "audience_estimates": "estimated",
      "benchmark_metrics": "estimated",
      "recommendations": "inferred"
    },
    "confidence": 0.7,
    "note": "Intelligence derived from your brand inputs + niche engine. Connect analytics (GA4, GSC) for observed data."
  }
}
```

### Data Mode Logic

`real_test`:
- User has provided instagram_handle OR website_url OR a non-generic brand name
- All recommendations are personalized to their actual inputs
- Provenance labels distinguish user_provided / inferred / estimated

`demo`:
- No real account connected
- All data is seeded/placeholder
- Every insight is labeled `demo`

### Provenance Labels

| Label | Meaning |
|---|---|
| `user_provided` | Entered directly by the user during onboarding |
| `observed` | Pulled from a live connected account (GA4, GSC, platform API) |
| `inferred` | Derived by the niche intelligence engine from user inputs |
| `estimated` | Industry benchmark / statistical estimate, not account-specific |
| `demo` | Seeded placeholder; no real account connected |

### Frontend Rules

- Demo mode: show a persistent banner: "Connect your Instagram or website for personalized intelligence"
- Real test mode: show data provenance chips on every insight card
- Observed data: show as highest-confidence (green)
- Estimated data: show with amber indicator
- Demo data: show with gray indicator and explicit disclaimer

## Consequences

**Positive:** Users always know what to trust. Real account data immediately improves intelligence. No false confidence from demo data.

**Negative:** Provenance tracking adds complexity to every endpoint response. Frontend must render provenance chips without cluttering the UI.

## Related

- `app/api/endpoints/brand.py` — `_meta()` and `_data_mode()` helpers
- All brand intelligence endpoints (`/overview`, `/trends`, `/audience`, `/recommendations`, `/media-plan`, `/geo`)
