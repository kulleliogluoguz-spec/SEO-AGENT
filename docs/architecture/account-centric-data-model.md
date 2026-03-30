# Account-Centric Data Model

The platform is organized around a **BrandProfile** as the central entity, anchored by an Instagram account.

---

## Core Entity Hierarchy

```
User
└── BrandProfile (one per user in demo mode)
    ├── instagram_handle       string, normalized (no @)
    ├── brand_name             string
    ├── website_url            string | null
    ├── description            string | null
    ├── category               string (e.g. "Health & Fitness")
    ├── target_audience        string | null
    ├── geography              string | null
    └── business_goal          string | null
    
    Derived (from niche_data.py intelligence engine):
    ├── inferred_niche         string (e.g. "fitness")
    ├── TrendSignal[]          8 niche-relevant trends
    ├── AudienceSegment[]      4 audience profiles
    ├── Recommendation[]       6 growth recommendations
    ├── ContentOpportunity[]   3 content themes
    └── GeoAudit               signals based on website_url

WebsiteProfile (optional enrichment)
└── belongs to BrandProfile via website_url
    ├── domain                 string
    ├── status                 pending | active | error
    ├── Crawl[]                async crawl jobs
    └── Recommendation[]       site-level SEO recommendations
```

---

## Intelligence Engine (niche_data.py)

Niche inference from `category` field:
- 9 niches: fitness, beauty, food, fashion, travel, tech, home, education, finance
- Fallback: `general`

Per-niche seeded data:
- 8 `TrendSignal` objects with momentum_score, relevance_score, volume_current, evidence
- 4 `AudienceSegment` objects with fit_score, intent_score, platforms, content_angle
- 6 `Recommendation` objects with priority_score, impact_score, effort_score, action
- 3 `ContentOpportunity` themes with hook_ideas, CTA, format_suggestion
- `GeoAudit` with weighted overall_score, signal breakdown

All intelligence is personalized with `brand_name` and `instagram_handle` at generation time.

---

## Storage Strategy

| Entity | Store | Persistence |
|---|---|---|
| BrandProfile | `brand_store.json` | File-based, survives restarts |
| Site / Crawl | `demo_store.json` (fallback) or PostgreSQL | File in demo mode |
| ContentAsset | `demo_store.json` (fallback) or PostgreSQL | File in demo mode |
| Report | `demo_store.json` (fallback) or PostgreSQL | File in demo mode |
| Approval | `demo_store.json` (fallback) or PostgreSQL | File in demo mode |
| Intelligence | Generated on-demand from `niche_data.py` | Stateless, no DB needed |

---

## Dashboard Query Scoping

Every dashboard module queries through BrandProfile:

1. Auth → `user_id`
2. `GET /api/v1/brand/profile` → load `BrandProfile` for this user
3. Derive `niche` from `category`
4. All intelligence endpoints return data scoped to this profile
5. Website/SEO endpoints use `website_url` from the profile

No page may use hardcoded UUIDs for brand-scoped data.
The `DEMO_WS` and `DEMO_SITE` constants are only used as fallback workspace/site IDs for legacy endpoints that predate the brand-centric model.

---

## Future: Social Account Model

```
SocialAccount
├── platform          "instagram" | "tiktok" | "youtube" | "twitter"
├── handle            string
├── profile_url       string
├── follower_count    int | null      (user-provided or API)
├── engagement_rate   float | null    (user-provided or calculated)
└── bio               string | null   (user-provided)
    └── belongs to BrandProfile
```

This will replace the `instagram_handle` field on BrandProfile when multi-platform support is added.

