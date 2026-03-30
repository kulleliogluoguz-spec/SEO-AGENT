# ADR-012: Measurement and Attribution Stack — PostHog + posthog-js

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The optimization and learning loop layers require accurate measurement. Without measurement, the system cannot distinguish successful strategies from failures. The platform needs:

1. Product event tracking (what users do inside the platform)
2. Campaign performance measurement (what happens after ads run)
3. Funnel tracking (session → engagement → conversion)
4. Experiment assignment tracking (which strategy variant did a user see?)
5. Attribution (which campaign/channel drove a conversion?)

## Decision

Use **PostHog** as the unified analytics and measurement layer.

Rationale:
- Open-source, self-hostable (consistent with platform's local-first philosophy)
- Supports product analytics + web analytics + funnels + session replay + feature flags
- posthog-js for browser-side instrumentation
- Python SDK for server-side event capture
- Feature flags integration supports GrowthBook-style experiment rollout

### Browser-Side (posthog-js)

File: `apps/web/lib/analytics.ts`

Events tracked:
- Campaign lifecycle (draft created, submitted, approved, published)
- Report exports
- Onboarding steps and completion
- Recommendation actions (accept/reject/defer)
- Approval decisions
- Bandit action selections and rewards
- Page views (manual, SPA-aware)

Configuration:
```
NEXT_PUBLIC_POSTHOG_KEY=phc_your_key
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com  # or self-hosted
```

Without `POSTHOG_KEY` the module is a no-op — safe to deploy without PostHog configured.

### Server-Side Event Capture (future)

Add `posthog-python` to requirements.txt and fire server-side events for:
- Campaign published to platform
- Strategy outcome recorded
- Reallocation decision applied
- Bandit reward recorded

### Attribution Model

Platform-level attribution (UTM tagging):
- All campaign URLs tagged with `?utm_source={platform}&utm_medium=paid&utm_campaign={campaign_id}`
- PostHog captures source/medium/campaign on session start
- Campaign IDs are linked to platform campaign IDs via the campaign_store

Conversion tracking:
- Install posthog-js on landing pages (or inject via GTM/Segment)
- Capture `conversion` events with campaign context
- Feed conversion events back to learning store as strategy outcomes

### Feast Integration (future)

PostHog event data → materialized into Feast feature store via Dagster pipeline:
- `audience_conversion_rate_{niche}` — per audience segment
- `channel_cac_{platform}` — per platform
- `creative_ctr_{format}` — per creative format
- `landing_quality_score` — session quality proxy

These features feed the Vowpal Wabbit bandit context.

### Evidently Integration (future)

Monitor for:
- Recommendation quality drift (are recommendations still relevant?)
- Reward distribution drift (is the reward signal still valid?)
- Data freshness (when did we last receive outcome signals?)

## Consequences

**Positive:** Single analytics platform for product + campaign measurement. Self-hostable. Open-source. No data leaves infrastructure. Propensity scores for causal analysis.

**Negative:** Requires PostHog self-hosted or cloud account. posthog-js adds ~50KB bundle size. Attribution is last-touch by default (multi-touch requires custom implementation).

## Related

- `apps/web/lib/analytics.ts` — browser-side implementation
- ADR-011 — bandit rewards sourced from attribution events
- ADR-013 — reallocation decisions informed by attribution data
