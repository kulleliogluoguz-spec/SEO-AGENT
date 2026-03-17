# AI Growth OS — Marketing Execution Engine

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                   Next.js Frontend (port 3000)                        │
│  Dashboard · Campaigns · Calendar · Approvals · Generate · Ads · Perf │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST/JSON — Bearer JWT
┌────────────────────────────▼─────────────────────────────────────────┐
│                   FastAPI Backend (port 8000)                          │
│  /marketing/campaigns · /generate · /approvals · /calendar            │
│  /content · /schedule · /publish · /ads · /performance · /connectors  │
├────────────────────────────┬─────────────────────────────────────────┤
│  13 Marketing Agents       │   5 Marketing Workflows (Temporal)       │
│  (LangGraph orchestrated)  │   Content Pipeline · Publish · Campaign  │
│                            │   Repurpose · Performance Tracking       │
├────────────────────────────┴─────────────────────────────────────────┤
│              Social Channel Connectors (Adapter Pattern)              │
│   Instagram · TikTok · Twitter/X · LinkedIn · Meta Ads                │
│   Mock + Real implementations · Auth · Rate Limiting · Retry          │
├──────────────────────────────────────────────────────────────────────┤
│              Compliance & Safety Service                               │
│   Spam detection · Risk scoring · Policy checks · Platform rules      │
├──────────────────────────────────────────────────────────────────────┤
│         PostgreSQL 16 + pgvector · Redis · Temporal                    │
│   7 new tables: campaigns, content_items, content_approvals,          │
│   content_performance, channel_connectors, ad_campaigns,              │
│   repurpose_logs                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Safety Architecture

**Default Autonomy: Level 1 — Draft Only**

| Level | Behavior | Auto-Publish |
|-------|----------|-------------|
| 0 | Analysis only — read-only | Never |
| 1 | **Draft only (default)** — all output requires review | Never |
| 2 | Approval-required — queued actions need explicit approval | Never |
| 3 | Low-risk auto — only compliant, low-risk content executes | Low-risk only |

### Compliance Checks (every content item)
- No spam patterns
- No fake engagement tactics
- No deceptive claims
- Platform-specific content limits (char count, hashtags, thread length)
- Excessive caps / emoji detection
- Risk scoring (0.0–1.0 scale)
- Policy warnings

---

## Marketing Agent Registry (13 Agents)

| # | Agent | Purpose | Permissions |
|---|-------|---------|------------|
| 1 | CampaignPlannerAgent | Creates structured campaign plans | manage_campaigns, llm_generate |
| 2 | ContentCalendarAgent | Generates time-slotted content calendars | write_content, llm_generate |
| 3 | ChannelStrategyAgent | Recommends optimal channel mix | read_analytics, llm_generate |
| 4 | SocialPostGeneratorAgent | Generates channel-specific posts | write_content, llm_generate |
| 5 | AdCampaignGeneratorAgent | Creates Meta Ads structures | manage_ads, llm_generate |
| 6 | HookOptimizationAgent | Generates attention hooks | llm_generate |
| 7 | HashtagStrategyAgent | Optimized hashtag sets by niche | read_analytics, llm_generate |
| 8 | AudienceTargetingAgent | Builds audience personas | read_analytics, llm_generate |
| 9 | PostTimingAgent | Optimal posting times | read_analytics |
| 10 | EngagementOptimizationAgent | Analyzes + suggests optimization | read_analytics, llm_generate |
| 11 | ABVariantGeneratorAgent | Creates A/B test variants | write_content, llm_generate |
| 12 | ContentRepurposingAgent | 1 post → multi-channel content | write_content, llm_generate |
| 13 | PerformanceFeedbackAgent | AI-generated performance insights | read_analytics, llm_generate |

---

## Channel Connectors

Each connector implements:
- `authenticate()` → Verify credentials
- `refresh_auth()` → Token refresh
- `publish(content)` → Publish to channel
- `schedule(content, time)` → Schedule post
- `delete(id)` → Remove post
- `get_metrics(id)` → Post-level metrics
- `get_account_metrics()` → Account metrics

### Platform Limits (enforced)

| Channel | Max Length | Hashtags | Rate Limit |
|---------|-----------|----------|-----------|
| Instagram | 2,200 chars | 30 max | 200/hr |
| TikTok | 2,200 chars | 100 max | 1000/day |
| Twitter/X | 280 chars (thread: 25 tweets) | — | 300/15min |
| LinkedIn | 3,000 chars | — | 1000/day |
| Meta Ads | 125 primary / 40 headline | — | 200/hr |

---

## Content Lifecycle

```
Topic/Brief → Generate (Agent) → Compliance Check → Draft
    ↓
Draft → Send to Approval → Approval Queue
    ↓
Approved → Schedule (time-zone aware)
    ↓
Scheduled → Publish (via Connector)
    ↓
Published → Track Metrics → Performance Feedback
    ↓
Feedback → Optimize → Next Content Cycle
```

---

## API Reference

### Campaigns
- `POST /marketing/campaigns` — Create campaign
- `GET /marketing/campaigns` — List campaigns

### Content Generation
- `POST /marketing/generate` — Generate multi-channel content
- `POST /marketing/repurpose` — Repurpose long-form → social

### Content Items
- `POST /marketing/content` — Create content item
- `GET /marketing/content` — List content items

### Approvals
- `GET /marketing/approvals` — List pending approvals
- `POST /marketing/approvals/{id}` — Approve/reject

### Calendar & Scheduling
- `GET /marketing/calendar` — Get content calendar
- `POST /marketing/schedule/{id}` — Schedule content
- `POST /marketing/schedule/batch` — Batch schedule

### Publishing
- `POST /marketing/publish/{id}` — Publish approved content

### Performance
- `GET /marketing/performance` — Performance summary
- `GET /marketing/performance/feedback` — AI insights

### Ads
- `POST /marketing/ads` — Create ad campaign
- `GET /marketing/ads` — List ad campaigns

### Tools
- `GET /marketing/hooks?topic=X` — Generate hooks
- `GET /marketing/hashtags?topic=X` — Hashtag strategy
- `GET /marketing/timing?channel=X` — Optimal posting times
- `GET /marketing/strategy` — Channel strategy

### Connectors
- `GET /marketing/connectors` — List connector status
- `POST /marketing/connectors` — Connect channel

---

## Temporal Workflows

| Workflow | Trigger | Steps |
|----------|---------|-------|
| ContentGenerationPipeline | Generate request | Generate → Compliance → Auto/Manual Approval → Queue |
| ScheduledPublish | Scheduled time | Wait → Re-check compliance → Publish → Track |
| CampaignExecution | Campaign start | Plan → Calendar → Generate content → Queue approvals |
| RepurposeWorkflow | Repurpose request | Extract key points → Generate per channel → Compliance |
| PerformanceTracking | Periodic | Fetch metrics → Store → AI feedback |

---

## Database Schema (7 new tables)

- `campaigns` — Campaign definitions + metadata
- `content_items` — Individual content pieces with channel-specific data
- `content_approvals` — Approval queue with compliance checks
- `content_performance` — Per-item metrics tracking
- `channel_connectors` — OAuth tokens + rate limit state
- `ad_campaigns` — Meta Ads campaign structures
- `repurpose_logs` — Source → output mapping

---

## File Structure

```
apps/api/app/
├── agents/marketing/
│   └── agents.py              # 13 marketing agents
├── api/endpoints/marketing/
│   └── routes.py              # FastAPI routes (30+ endpoints)
├── connectors/social/
│   ├── base.py                # Base interface + registry
│   ├── channels.py            # 5 channel implementations
│   └── __init__.py
├── models/
│   └── marketing.py           # 7 SQLAlchemy models
├── schemas/marketing/
│   └── schemas.py             # Pydantic request/response
├── services/marketing/
│   ├── service.py             # Orchestration service
│   └── compliance.py          # Safety + compliance
├── workers/marketing/
│   └── workflows.py           # 5 Temporal workflows
├── prompts/marketing/
│   └── prompts.py             # Versioned prompt templates
└── alembic/versions/
    └── mktg_001_...py         # Database migration

apps/web/src/
├── types/marketing.ts         # TypeScript types
├── lib/api/marketing.ts       # API client
└── (dashboard components)
```

---

## Quick Start (adding to existing repo)

```bash
# 1. Copy new files into your existing repo structure
cp -r apps/api/app/agents/marketing    your-repo/apps/api/app/agents/
cp -r apps/api/app/connectors/social   your-repo/apps/api/app/connectors/
cp -r apps/api/app/services/marketing  your-repo/apps/api/app/services/
# ... etc

# 2. Run migration
make migrate

# 3. Register routes in your main.py
from app.api.endpoints.marketing.routes import router as marketing_router
app.include_router(marketing_router)

# 4. Start services
make up
```
