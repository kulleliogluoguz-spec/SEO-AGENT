# Platform Capabilities

**AI Growth OS** is a local-first, account-centric, closed-loop growth and advertising operating system.

---

## Capability Layers

### Layer 1: Brand Onboarding + Niche Intelligence
- Accept Instagram handle, website URL, brand name, and category
- Infer niche from category (9 niches: fitness, beauty, food, fashion, travel, tech, home, education, finance)
- Classify data mode: `real_test` (real inputs provided) vs. `demo` (placeholder)
- Return provenance labels per insight: `user_provided | observed | inferred | estimated | demo`

### Layer 2: Trend + Audience + Content Intelligence
- 8 niche-relevant trending topics weekly with momentum, relevance, and volume scores
- 4 audience segment profiles per niche with fit and intent scores, pain points, platform habits
- 3 content opportunity themes with hooks, CTAs, and format recommendations (Reels, carousel, story)
- GEO/SEO audit: structured data, entity clarity, citation density, content depth
- All responses include `_meta` block: data_mode, provenance, confidence, note

### Layer 3: Growth Recommendations + Approval Workflow
- 6 prioritized recommendations specific to brand niche and stage
- Scored by: priority, impact, effort
- Default autonomy level: 1 (Draft Only) — nothing executes without human approval
- Approve, reject, or defer any action via `/dashboard/approvals`
- Approval gate required for campaign publish and budget changes >$50/day

### Layer 4: Ads Connector Layer
- OAuth connection for: Meta, Google, TikTok, LinkedIn, Pinterest, Snap
- Capability stages: `planning → auth_verified → account_linked`
- Platform adapters: auth URL generation live (✅), token exchange and account listing stubbed (501 with explanation)
- Credential store: encrypted at rest, never returned in API responses
- Credential file (`storage/credentials.json`) must be gitignored

### Layer 5: Campaign Draft Lifecycle
- Campaign drafts always created with `status=draft`, never auto-published
- Draft → `pending_approval` (submit) → `approved` (approval action) → `published` (publish with approval_id)
- Budget reallocation: 50% max single move, requires approval for >$50/day change
- Full immutable audit log on every campaign action
- Endpoints: `POST /campaigns/drafts`, `POST /drafts/{id}/submit`, `POST /drafts/{id}/publish`

### Layer 6: PostHog Analytics
- Typed event tracking library at `apps/web/lib/analytics.ts`
- 30+ event types: campaign created/submitted/published, ads connected, account linked, hypothesis created, strategy outcome recorded, reallocation proposed, report exported, onboarding steps, recommendations acted on, bandit actions/rewards
- No-op gracefully when `NEXT_PUBLIC_POSTHOG_KEY` is not set
- `identifyUser()`, `resetIdentity()`, `setSuperProperties()`, `trackPageView()`

### Layer 7: Learning Loop
- Every recommendation execution recorded as a strategy outcome
- Confidence tracking: +0.10 success, 0.00 partial, -0.15 failure
- Pattern suppression: failure_rate ≥ 0.60 → suppressed, min 3 samples
- Pattern promotion: success_rate ≥ 0.70 → promoted
- A/B hypothesis tracking with winner/loser outcomes
- Experiments UI at `/dashboard/experiments`: Overview, Strategies, Hypotheses, Patterns tabs
- Storage: `storage/learning_store.json` → target: PostgreSQL

### Layer 8: Contextual Bandit (Online Optimization)
- Epsilon-greedy (ε=0.20) + UCB1 action selection
- 7 action types: channel_selection, audience_segment, creative_format, budget_allocation, content_angle, cta_variant, landing_variant
- Reward presets: success=1.0, partial=0.3, neutral=0.0, failure=-1.0
- Propensity logging for all selections (required for causal analysis / OPE)
- Safety rules: min 3 observations before exploitation, max confidence 0.90, epsilon floor 0.20
- Upgrade path: Stage 2 = Vowpal Wabbit CB (>100 labeled outcomes), Stage 3 = Offline RL (>1000)
- Storage: `storage/bandit_store.json`

### Layer 9: Constrained Auto-Reallocation
- Propose budget moves based on bandit arm performance
- Hard constraints: 50% max single reallocation, never below $5/day floor, never above workspace monthly cap
- Requires human approval for any move >$50/day
- All decisions logged in campaign_store audit log
- Kill switch: workspace admin can disable at any time

### Layer 10: RL / Simulation (Planned)
- Offline RL research mode — no live RL deployed
- Algorithms planned: CQL, IQL, TD3+BC, BCQ (via RLlib / Stable-Baselines3)
- Off-Policy Evaluation required before any live deployment: DM, IPS, Doubly Robust
- DR estimate must beat bandit baseline by >10% over 30-day simulation
- Live RL requires: >1000 labeled outcomes, stable reward model, 90+ days bandit data, compliance review

---

## What is Real vs. Inferred vs. Estimated vs. Demo

| Data | Mode | Notes |
|---|---|---|
| Brand name, handle, category | `user_provided` | Saved to brand_store.json |
| Website URL | `user_provided` | Enables SEO/GEO analysis |
| Niche inference | `inferred` | 9-niche classifier from category keywords |
| Trend intelligence | `estimated` | Niche-specific curated data |
| Audience segments | `estimated` | Niche-specific profiles, brand-personalized |
| Growth recommendations | `inferred` | Scored and ranked per niche |
| Content opportunities | `estimated` | Niche-specific themes with hooks |
| GEO signals | `estimated` | Structural audit, adapted for website presence |
| SEO recommendations | `estimated` | Site-level best practices |
| Campaign performance | `observed` | (future) from connected platform APIs |
| Analytics events | `observed` | (future) from PostHog + GA4 + GSC |

---

## What Remains Before Full Autonomous Optimization

1. Platform API adapters: complete token exchange, account listing, campaign creation for Meta/Google/TikTok/LinkedIn/Pinterest/Snap
2. Data pipeline: Airbyte connectors for GA4, GSC, platform performance pull
3. Feature store: Feast for bandit context features (user_success_rate, channel_cpl, creative_ctr)
4. Experiment tracking: MLflow for learning runs and model versioning
5. Drift monitoring: Evidently on reward signal distributions
6. Live RL: offline RL validated in simulation with OPE, compliance review, admin kill switch
7. Mautic: email/CRM automation for nurture sequences triggered by learning loop
8. GrowthBook/Unleash: production A/B testing and feature flags for live experiments
9. Temporal/Dagster: scheduled jobs for token refresh, learning sweeps, bandit retraining
10. PostgreSQL + pgvector: migrate all file stores; enable semantic similarity search on brand content
