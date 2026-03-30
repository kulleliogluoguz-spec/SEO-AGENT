# Implementation Roadmap — AI Growth OS

**Version:** 1.0
**Date:** 2026-03-28

---

## Overview

The platform is built in 9 phases. Each phase produces a vertical slice of working functionality. Phases build on each other but are designed so that partial completions remain useful.

---

## PHASE 0 — Repo Audit and Gap Analysis ✅ COMPLETE

**Deliverables:**
- [x] `/docs/architecture/current-state-audit.md`
- [x] `/docs/architecture/target-architecture.md`
- [x] `/docs/roadmap/implementation-phases.md`

---

## PHASE 1 — Target Architecture + Foundation ✅ IN PROGRESS

**Goal:** Establish the foundational architecture: correct docker-compose, local-AI-first config, vector store, connector SDK interface, and missing data models.

**Tasks:**
- [x] Create architecture docs (ADRs, target architecture)
- [ ] Add Ollama + Qdrant to `docker-compose.yml`
- [ ] Fix `.env.example` to default to Ollama/Qwen3, not Anthropic
- [ ] Add `qdrant-client` to Python requirements
- [ ] Add local embedding pipeline (`apps/api/app/ai/embeddings/`)
- [ ] Add Qdrant vector store client (`apps/api/app/ai/vectorstore/`)
- [ ] Create `packages/connector-sdk/` — base connector interface
- [ ] Add missing DB migrations (source_connections, source_documents, trends, audience_segments, brand_profiles, geo_audits)
- [ ] Create product vision + MVP scope docs

**Exit criteria:** `docker compose up` starts all services including Ollama + Qdrant. LLM calls route to local Ollama by default.

---

## PHASE 2 — Local AI Foundation

**Goal:** A working local AI stack. Embeddings, vector retrieval, and agent completions all run locally.

**Tasks:**
- [ ] Local embedding pipeline: document → nomic-embed-text → Qdrant
- [ ] Qdrant collection management + health checks
- [ ] Embedding endpoint in API (`POST /api/v1/embed`)
- [ ] Semantic search endpoint (`POST /api/v1/search`)
- [ ] Model health dashboard in admin UI
- [ ] Add CPU-only `docker-compose.cpu.yml` for minimal deployments
- [ ] Evaluation harness for embedding quality (MTEB-style subset)
- [ ] Add `sentence-transformers` as alternative embedding backend

**Exit criteria:** A document can be ingested, embedded locally, and retrieved via semantic search. No external API called.

---

## PHASE 3 — Data Ingestion Foundation

**Goal:** Working connector framework. At minimum, website crawl, RSS/Atom, and Reddit (official API) connectors are fully functional.

**Tasks:**
- [ ] Connector SDK (`BaseConnector`, `ConnectorConfig`, `RawDocument`, `ConnectorRegistry`)
- [ ] Compliance mode enforcement in connector SDK
- [ ] Website crawler connector (wraps existing `WebCrawlerTool`)
- [ ] Sitemap connector
- [ ] RSS/Atom feed connector
- [ ] Reddit connector (PRAW, official API)
- [ ] CSV/JSON import connector
- [ ] Connector configuration API endpoints (`POST /api/v1/connectors/{type}/config`)
- [ ] Connector run scheduling (Dagster)
- [ ] Raw document storage pipeline
- [ ] Document normalization + dedup pipeline
- [ ] `source_connections` and `source_documents` tables

**Exit criteria:** A user can add an RSS feed or subreddit as a source. Documents are ingested, normalized, and stored with provenance.

---

## PHASE 4 — Brand + Trend Intelligence MVP

**Goal:** The system can analyze a brand and discover relevant trends.

**Tasks:**
- [ ] Brand profile builder (BrandIntelligenceAgent)
- [ ] Brand profile storage + versioning (`brand_profiles` table)
- [ ] Brand profile API (`GET /api/v1/brands/{workspace_id}`)
- [ ] Topic extraction pipeline (from crawled + ingested documents)
- [ ] Trend detection algorithm (keyword clustering + momentum scoring)
- [ ] `trends` table + TrendRecord schema
- [ ] Trend-to-brand relevance scoring
- [ ] Trend feed API (`GET /api/v1/trends`)
- [ ] Frontend: Trend Feed page (real data)
- [ ] Frontend: Brand Intelligence view
- [ ] Dagster: `daily_trend_discovery` job

**Exit criteria:** A user onboards a website. The system builds a brand profile and surfaces relevant trends from ingested sources.

---

## PHASE 5 — GEO / SEO Intelligence MVP

**Goal:** A working GEO/SEO audit engine producing actionable recommendations.

**Tasks:**
- [ ] `GEOAuditorAgent` with real tools:
  - [ ] `check_llms_txt` — verify llms.txt existence and quality
  - [ ] `check_robots_txt` — AI crawler access analysis
  - [ ] `analyze_schema_markup` — JSON-LD / structured data check
  - [ ] `score_content_citability` — can an AI cite this page?
  - [ ] `check_canonical_signals` — canonical, hreflang, etc.
  - [ ] `evaluate_entity_consistency` — brand/product name consistency
  - [ ] `score_ai_crawler_readiness` — aggregated AI discoverability score
- [ ] `SEOAuditorAgent` with technical SEO tools
- [ ] `geo_audits` and `seo_audits` tables
- [ ] GEO Audit API (`POST /api/v1/audits/geo`, `GET /api/v1/audits/geo/{id}`)
- [ ] Frontend: GEO workspace (real data)
- [ ] GEO improvement recommendation generation
- [ ] Scheduled weekly GEO audit (Dagster/Temporal)

**Exit criteria:** A user can trigger a GEO audit on their site and receive scored recommendations with evidence.

---

## PHASE 6 — Analytics + Conversion Intelligence

**Goal:** Analytics integration and funnel diagnostics.

**Tasks:**
- [ ] PostHog connector (official API)
- [ ] Umami connector (official API)
- [ ] Analytics adapter layer (abstract PostHog/Umami behind common interface)
- [ ] Funnel definition storage
- [ ] `FunnelAnalystAgent`
- [ ] Conversion drop-off detection
- [ ] Traffic source quality scoring
- [ ] OpenReplay integration (session replay hooks)
- [ ] Analytics API endpoints
- [ ] Frontend: Funnel/Analytics dashboard with real data

**Exit criteria:** A user can connect PostHog or Umami, see funnel drop-offs, and receive conversion improvement recommendations.

---

## PHASE 7 — Recommendation Engine

**Goal:** Intelligent, evidence-backed recommendations using semantic matching + ML.

**Tasks:**
- [ ] Rule-based recommendation engine (baseline)
- [ ] Semantic recommendation scoring (Qdrant similarity)
- [ ] LightFM hybrid recommendation model
  - [ ] Training pipeline (Dagster)
  - [ ] Inference endpoint
  - [ ] Evaluation pipeline
- [ ] `Recommendation` record improvements (confidence, evidence links)
- [ ] Recommendation feedback loop (`recommendation_feedback` table)
- [ ] RecBole integration (advanced experimentation, optional)
- [ ] Feast feature store for recommendation features (optional)
- [ ] Recommendation quality evaluation pipeline

**Exit criteria:** Recommendations are ranked by predicted impact using a trained model, with evidence and confidence scores.

---

## PHASE 8 — Activation + Reporting

**Goal:** Actionable outputs, report generation, optional automation.

**Tasks:**
- [ ] Improved report generation (`ReportingAgent`)
- [ ] Report templates (weekly, monthly, GEO, trend, audience)
- [ ] Report export (PDF, Markdown)
- [ ] Approval workflow improvements (commenting, delegation)
- [ ] Mautic interoperability (optional)
  - [ ] Mautic API connector
  - [ ] Campaign brief → Mautic campaign mapping
- [ ] Content brief generator (from trends + audience)
- [ ] Campaign brief API
- [ ] Frontend: Activation center (content briefs, campaign briefs)
- [ ] Webhook delivery for approved actions

**Exit criteria:** A user can generate a weekly intelligence report, create content briefs from trends, and optionally send campaign briefs to Mautic.

---

## PHASE 9 — Hardening

**Goal:** Production-ready platform with tests, docs, security pass, seed data, and observability.

**Tasks:**
- [ ] Complete test coverage (unit + integration, ≥80%)
- [ ] E2E tests for critical paths (onboarding, trend discovery, GEO audit)
- [ ] Production docker-compose with TLS, proper secrets
- [ ] Kubernetes Helm charts
- [ ] Security audit (OWASP top 10 check)
- [ ] Full observability (traces, metrics, alerts)
- [ ] Demo account + seed data
- [ ] Complete API documentation (OpenAPI)
- [ ] User documentation
- [ ] Performance benchmarks
- [ ] Database query optimization + indexing
- [ ] Rate limit hardening
- [ ] Backup + restore procedures

---

## Timeline Estimates

| Phase | Description | Estimated Effort |
|-------|-------------|-----------------|
| 0 | Audit | Done |
| 1 | Foundation | 1-2 weeks |
| 2 | Local AI | 1-2 weeks |
| 3 | Ingestion | 2-3 weeks |
| 4 | Brand + Trends | 3-4 weeks |
| 5 | GEO/SEO | 2-3 weeks |
| 6 | Analytics | 2-3 weeks |
| 7 | Recommendations | 3-4 weeks |
| 8 | Activation | 2-3 weeks |
| 9 | Hardening | 2-3 weeks |

**Total estimated effort:** 18-27 weeks for a complete platform.

**MVP milestone (Phases 1-5):** ~11-16 weeks for a brand onboarding + trend intelligence + GEO audit MVP.
