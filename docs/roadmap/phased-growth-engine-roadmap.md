# Phased Growth Engine Roadmap

**Last updated:** 2026-03-29
**Current stage:** Stage 2 (Analytics scaffolded) — Stage 3–10 planned

---

## Stage 1 — Intelligence Foundation ✅ Complete

- ✅ Instagram-first brand profile with 4-step onboarding
- ✅ Niche inference from category (9 niches)
- ✅ Trend feed with momentum/relevance scoring
- ✅ Audience segment intelligence (4 segments per niche)
- ✅ Growth recommendations (6 per niche, priority scored)
- ✅ Content brief creator with AI suggestions
- ✅ GEO/SEO intelligence for websites
- ✅ Approval workflow (draft-only, Level 1 autonomy)
- ✅ Data provenance on all brand intelligence endpoints (`_meta` block)
- ✅ Real test mode vs. demo mode (based on instagram_handle / website_url)
- ✅ File-based stores — full functionality without PostgreSQL
- ✅ Demo mode — full platform without external services
- ✅ Export MD fixed — fetches full ReportDetail with content_md

---

## Stage 2 — Measurement + Analytics ✅ Scaffolded

- ✅ PostHog typed event library (`apps/web/lib/analytics.ts`)
  - 30+ event types: campaigns, connectors, hypotheses, bandit actions, onboarding, reports
  - No-op when `NEXT_PUBLIC_POSTHOG_KEY` unset
  - `identifyUser`, `setSuperProperties`, `trackPageView`
- ✅ Learning loop: confidence tracking, pattern suppression/promotion
- ✅ Experiments UI: Overview, Strategies, Hypotheses, Patterns tabs
- ⬜ Connect PostHog Cloud/self-hosted (set NEXT_PUBLIC_POSTHOG_KEY)
- ⬜ Google Analytics 4 connector (OAuth, pull organic sessions + conversions)
- ⬜ Google Search Console connector (pull top queries, CTR)

---

## Stage 3 — Semantic Memory (Qdrant) ⬜ Planned

**Goal:** Make recommendations smarter through vector similarity.

- ⬜ `brand_profiles` collection — embed brand descriptions
- ⬜ `trends` collection — embed keywords for brand-to-trend matching
- ⬜ `audience_segments` collection — content-to-audience matching
- ⬜ `content_briefs` collection — deduplication + variation suggestions
- ⬜ Embedding model: `nomic-embed-text` via Ollama
- ⬜ Qdrant MCP integration for AI assistant memory

---

## Stage 4 — Data Pipeline (Airbyte) ⬜ Planned

**Goal:** Structured ingestion from external sources.

- ⬜ Airbyte source connectors: GA4, Search Console, Instagram Insights
- ⬜ Incremental sync for campaign performance data
- ⬜ CSV upload connectors (Instagram export, competitor data)
- ⬜ Dagster jobs for scheduled syncs

---

## Stage 5 — Ads Execution Layer ✅ Framework + ⬜ Adapters

- ✅ OAuth framework for all 6 platforms (Meta, Google, TikTok, LinkedIn, Pinterest, Snap)
- ✅ Auth URL generation live for all platforms
- ✅ Credential store (encrypted, file-based)
- ✅ Campaign draft lifecycle: draft → pending_approval → approved → published
- ✅ Budget reallocation with 50% cap + approval gate
- ✅ Immutable audit log
- ⬜ Meta Marketing API adapter: token exchange, account listing, campaign create
- ⬜ Google Ads API adapter
- ⬜ TikTok for Business adapter
- ⬜ LinkedIn Marketing Solutions adapter
- ⬜ Pinterest Ads API adapter (no extended review required)
- ⬜ Snap Marketing API adapter

---

## Stage 6 — Activation Layer (Mautic) ⬜ Planned

**Goal:** Approval-gated marketing execution and lifecycle management.

- ⬜ Mautic REST API integration (self-hosted)
- ⬜ Contact lifecycle stage tracking (awareness → consideration → conversion)
- ⬜ Audience segment export to ad platform audiences
- ⬜ Webhook-based publishing triggers

### Autonomy Levels
| Level | Behavior |
|---|---|
| 0 | Analysis only |
| 1 | Draft only — all outputs need approval (default) |
| 2 | Low-risk auto-queue |
| 3 | Pre-approved action types execute |
| 4 | Supervised full execution |

---

## Stage 7 — Local AI Enhancement (Ollama) ⬜ Partially Ready

**Goal:** Replace seeded data with locally-generated intelligence.

- ✅ Ollama configured in settings (`OLLAMA_BASE_URL`, `OLLAMA_MODEL=qwen3:8b`)
- ✅ Anthropic disabled by default (local-first)
- ⬜ Real trend detection from RSS/Reddit feeds
- ⬜ Content generation: brief → draft → review queue
- ⬜ GEO audit: website crawl → AI discoverability scoring
- ⬜ `llava` for Instagram image analysis

---

## Stage 8 — Feature Store + Experiment Tracking ⬜ Planned

**Goal:** Close the loop between bandit decisions and outcome data.

- ⬜ Feast: online feature store for bandit context
  - `user_success_rate_{niche}`, `channel_cpl_{platform}`, `creative_ctr_{format}`
- ⬜ MLflow: learning run tracking, policy registry, model versioning
- ⬜ GrowthBook / Unleash: production A/B testing + feature flags
- ⬜ Evidently: reward signal drift monitoring

### Bandit Upgrade Path
| Stage | Trigger | Algorithm |
|---|---|---|
| Stage 1 (current) | any | Epsilon-greedy + UCB1 |
| Stage 2 | >100 labeled outcomes per arm | Vowpal Wabbit CB + DR estimator |
| Stage 3 | >1000 outcomes total | Offline RL (CQL / IQL) |
| Stage 4 | OPE validated + compliance approved | Live RL |

---

## Stage 9 — PostgreSQL + pgvector Migration ⬜ Planned

**Goal:** Replace all file stores with proper database.

- ⬜ Migrate brand_store → `brands` table
- ⬜ Migrate learning_store → `strategy_records`, `hypothesis_records` tables
- ⬜ Migrate campaign_store → `campaign_drafts`, `audit_log` tables
- ⬜ Migrate bandit_store → `bandit_arms`, `selection_log` tables
- ⬜ Enable pgvector extension for semantic search
- ⬜ Temporal / Dagster for scheduled jobs (token refresh, learning sweeps)

---

## Stage 10 — Live Reinforcement Learning ⬜ Future

**Prerequisites:**
1. >1000 labeled strategy outcomes in learning_store
2. Stable reward model with <15% estimation error
3. Bandit system running for >90 days
4. Off-Policy Evaluation (DR estimate >10% above bandit baseline)
5. Compliance and legal review of autonomous budget management

**Guardrails when deployed:**
- Hard budget floor: $5/day minimum
- Hard budget ceiling: workspace monthly cap
- Max daily budget change: 20%
- Kill switch: admin can disable at any time
- Approval gate: any change >$50/day requires human approval
- Rollback: every optimization action has documented rollback plan

---

## Open-Source Integration Status

| System | Stage | Status | Role |
|---|---|---|---|
| PostHog | 2 | ✅ Library ready | Product analytics, session replay |
| Qdrant | 3 | ⬜ Config ready | Semantic brand memory |
| Airbyte | 4 | ⬜ Planned | Data ingestion framework |
| Mautic | 6 | ⬜ Planned | Marketing activation, lifecycle |
| Ollama | 7 | ✅ Config ready | Local LLM, no external API |
| Feast | 8 | ⬜ Planned | Online feature store for bandit |
| MLflow | 8 | ⬜ Planned | Experiment tracking, model registry |
| GrowthBook | 8 | ⬜ Planned | Production A/B testing |
| Unleash | 8 | ⬜ Planned | Feature flags |
| Evidently | 8 | ⬜ Planned | Reward drift monitoring |
| Vowpal Wabbit | 8 | ⬜ Planned | Bandit Stage 2 CB |
| Coba | 8 | ⬜ Planned | Bandit benchmarking |
| learn_to_pick | 8 | ⬜ Planned | Fast CB prototyping |
| RLlib | 10 | ⬜ Planned | Offline RL research |
| Stable-Baselines3 | 10 | ⬜ Planned | Offline RL simpler baseline |
| RecBole | 10 | ⬜ Planned | Recommendation ranking research |
| Microsoft Recommenders | 10 | ⬜ Planned | Production ranking patterns |
| Temporal | 9 | ⬜ Planned | Workflow orchestration |
| Dagster | 9 | ⬜ Planned | Scheduled data pipelines |
