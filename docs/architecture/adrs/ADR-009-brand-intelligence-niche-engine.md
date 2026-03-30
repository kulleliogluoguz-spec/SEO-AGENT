# ADR-009: Brand Intelligence — Niche Engine Over Generic LLM Prompts

**Status:** Accepted
**Date:** 2026-03-29
**Deciders:** Principal Architect

---

## Context

The platform needs to produce brand-specific intelligence: channel recommendations, content opportunities, audience profiles, geo scores, competitive positioning. The naive approach is to send all this to an LLM with a big prompt. This has several problems:

1. **Latency:** Cold LLM calls take 5–30 seconds for structured output
2. **Non-determinism:** Same brand, different run → different channel rankings
3. **No learning:** LLM output cannot be weighted by past strategy outcomes
4. **Token cost:** Even with local Ollama, large context windows strain 8B models

## Decision

Implement a rule-based **Niche Engine** (`app/core/niche_data.py`) as the primary intelligence layer. The engine maps niches to pre-calibrated channel scores, audience archetypes, content formats, and seasonal patterns.

**Architecture:**
```
Brand Profile (niche, stage, channels)
    → NicheEngine.get_recommendations(niche, context)
    → PromotedStrategies weighting (from learning_store)
    → SuppressedStrategies filtering
    → Ranked recommendations
```

LLM is used **only** for:
- Free-text brand profile extraction from crawl data
- Content brief generation (structured prompt → structured output)
- Hypothesis rationale generation

All numerical scoring, channel ranking, and audience sizing comes from the niche engine.

**Supported niches:** ecommerce, saas, fashion, beauty, fitness, food, travel, finance, education, creator, b2b, tech, healthcare, real_estate, gaming, general

Each niche defines:
- `top_channels` — ordered list with confidence scores
- `audience_archetypes` — demographic + psychographic profiles
- `content_formats` — ranked by engagement for the niche
- `seasonal_peaks` — months with highest conversion probability
- `avg_cac_usd`, `avg_roas` — industry benchmarks
- `geo_priority` — tier-1 cities/regions for the niche

## Learning Integration

The niche engine output is post-processed through the learning loop:
- Promoted patterns for this niche get +0.1 confidence boost
- Suppressed patterns get filtered out of recommendations
- This means the engine gets smarter as users record outcomes

## Consequences

**Positive:**
- Sub-100ms response times for all intelligence endpoints
- Deterministic, auditable scoring (no LLM hallucination in numerical output)
- Learning loop directly improves recommendation quality
- Works with zero LLM calls for basic intelligence

**Negative:**
- Niche data requires manual maintenance as market conditions change
- New niches must be manually added to `niche_data.py`
- Channel scores are calibrated on industry averages, not account-specific data (until Stage B ads connector)

## Related

- `app/core/niche_data.py` — niche engine implementation
- `app/api/endpoints/brand.py` — brand intelligence API
- `app/core/store/learning_store.py` — learning loop integration
- `storage/brand_store.json` — brand profiles
