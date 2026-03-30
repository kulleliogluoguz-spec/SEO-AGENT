# Architecture — AI CMO OS

## Overview

AI CMO OS is a multi-layer, multi-agent growth intelligence platform built on FastAPI, LangGraph, and Temporal. It is designed to be modular, observable, and safe by default.

## System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (port 3000)                   │
│  Login · Dashboard · Sites · SEO · GEO · Content · Approvals     │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST / JSON (Bearer JWT)
┌──────────────────────────▼───────────────────────────────────────┐
│                FastAPI Backend (port 8000)                         │
│  /api/v1/auth · /sites · /crawls · /recommendations              │
│  /content · /approvals · /reports · /connectors                   │
├──────────────────────────┬───────────────────────────────────────┤
│         LangGraph         │         Temporal Workers               │
│   Agent Reasoning Graphs  │   Durable Workflow Execution          │
│   12 Layers / 138 Agents  │   Scheduling · Retries · Resumes      │
└──────────┬───────────────┴──────────────────┬────────────────────┘
           │                                  │
┌──────────▼──────────────────────────────────▼────────────────────┐
│              PostgreSQL 16 + pgvector + Redis                      │
│        Site data · Recommendations · Content · Reports             │
└───────────────────────────────────────────────────────────────────┘
```

## Layers

### Backend Service Layer

| Layer | Responsibility |
|-------|---------------|
| `app/api/endpoints/` | FastAPI routers — HTTP interface |
| `app/api/dependencies/` | Shared FastAPI dependencies (auth, pagination) |
| `app/services/` | Business logic, orchestration |
| `app/repositories/` | Database query logic (future) |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response schemas |
| `app/agents/` | 138 agents across 13 layers |
| `app/workflows/` | LangGraph state graphs |
| `app/tools/` | Typed tool implementations |
| `app/connectors/` | External system adapters |
| `app/prompts/` | Prompt registry and templates |

### Agent Architecture

Agents are organized into 13 functional layers:

| Layer | Name | Purpose |
|-------|------|---------|
| 0 | Platform Control | Supervision, routing, policy gating, compliance |
| 1 | Onboarding & Intelligence | Crawling, metadata, content extraction |
| 2 | Product Understanding | Product summary, ICP, personas, positioning |
| 3 | Competitor Intel | Discovery, clustering, battlecards |
| 4 | SEO | Technical SEO, on-page, content gaps |
| 5 | GEO/AEO | AI visibility, citation readiness (experimental) |
| 6 | Analytics | GA4, GSC ingestion, KPIs, trends |
| 7 | Content Strategy | Briefs, editorial calendar, audience mapping |
| 8 | Content Production | Writing, editing, scoring, compliance |
| 9 | Distribution | Planning, channel fit, approval routing |
| 10 | Experimentation | Hypothesis, variants, metrics |
| 11 | Reporting | Daily/weekly/monthly summaries |
| 12 | Quality/Evaluation | Prompt eval, QA, hallucination risk |

### Orchestration Split: LangGraph vs Temporal

**LangGraph** handles:
- Agent reasoning graphs
- Conditional routing between agents
- Stateful subgraph execution
- Structured handoffs and outputs

**Temporal** handles:
- Durable long-running workflows (e.g., full site onboarding)
- Scheduled periodic jobs (weekly reports)
- Retry and resume on failure
- Waiting on human approval signals
- Cross-service coordination

This split keeps reasoning logic cleanly separated from workflow durability concerns.

## Data Flow: Site Onboarding

```
User submits URL
    → API creates Site + Crawl records
    → SiteService.trigger_onboarding_workflow()
        → Temporal: SiteOnboardingWorkflow
            → Activity: validate_domain
            → Activity: run_crawl (WebCrawlerTool)
            → Activity: run_seo_audit (TechnicalSEOAuditAgent)
            → Activity: run_product_understanding (ProductUnderstandingAgent)
            → Activity: generate_recommendations
            → Activity: generate_initial_report
            → Activity: notify_team (SlackConnector)
        → DB: Site.status = ACTIVE
        → DB: Recommendations created
        → DB: Report created
```

## Data Flow: Content Generation

```
User creates brief
    → ContentBriefAgent → ContentAsset (status=DRAFT)
    → User requests generation
    → LongFormWriterAgent → ContentAsset (status=REVIEW)
    → Compliance scan → compliance_flags populated
    → ApprovalGateAgent → Approval record created
    → Human approves in UI
    → ContentAsset (status=APPROVED)
    → (Optional) CMSPublishPreparationAgent → publishing queue
```

## Autonomy Policy

Every consequential action is gated by the workspace autonomy level:

| Level | Behavior | Use Case |
|-------|----------|----------|
| 0 | Analysis only | Read-only intelligence |
| 1 | Draft only (default) | All output for human review |
| 2 | Approval-required | Queued actions need explicit approval |
| 3 | Low-risk auto | Minor changes auto-execute |
| 4 | Advanced auto | Disabled by default |

## Security Model

See [SECURITY.md](SECURITY.md) and [THREAT_MODEL.md](THREAT_MODEL.md).

Key points:
- JWT auth with RBAC
- SSRF protection on all crawl requests
- Domain blocklist for crawls
- Prompt injection mitigations (untrusted content isolation)
- Approval gates before all publishing actions
- Audit logs for all consequential actions

## Multi-Tenancy

- Every resource belongs to a `workspace`
- Workspaces belong to `organizations`
- Users have `memberships` with RBAC roles
- All queries filter by workspace_id
- Separate Temporal namespaces per environment
