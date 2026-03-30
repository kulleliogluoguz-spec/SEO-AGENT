# Target Architecture — AI Growth OS

**Version:** 1.0
**Date:** 2026-03-28

---

## 1. Platform Vision

The AI Growth OS is a **fully local, self-hosted, modular, open-source** intelligence platform for growth and marketing teams. A company connects its website, brand accounts, and analytics sources. The platform continuously discovers trends, maps them to the company's positioning, identifies high-potential audiences, and orchestrates growth actions — all without requiring any external proprietary LLM API.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                               │
│   Next.js Dashboard  │  API Clients  │  Webhook Receivers          │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│                     CONTROL PLANE API                               │
│              FastAPI  (apps/api) — REST + WebSocket                │
│   Auth  │  Workspaces  │  Sites  │  Trends  │  Recommendations     │
│   Approvals  │  Reports  │  Connectors  │  Admin                   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
         ┌─────────────┴──────────────┐
         │                            │
┌────────▼──────────┐       ┌─────────▼──────────────────────────────┐
│  WORKFLOW ENGINE  │       │        DATA PIPELINE ENGINE             │
│  Temporal         │       │        Dagster                          │
│  - Onboarding     │       │  - Trend ingestion                      │
│  - Report gen     │       │  - Brand profile build                  │
│  - Approvals      │       │  - Audience scoring                     │
│  - Scheduled jobs │       │  - GEO audit runs                       │
└────────┬──────────┘       │  - Recommendation refresh               │
         │                  └──────────────┬─────────────────────────┘
         │                                 │
┌────────▼─────────────────────────────────▼─────────────────────────┐
│                     AGENT / AI LAYER                                │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Trend Research │  │  Brand Intel      │  │  GEO/SEO Auditor  │  │
│  │ Agent          │  │  Agent            │  │  Agent             │  │
│  └────────────────┘  └──────────────────┘  └────────────────────┘  │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Audience Match │  │ Campaign Recomm  │  │ Funnel Analyst     │  │
│  │ Agent          │  │ Agent            │  │ Agent              │  │
│  └────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                     │
│         Powered by: LOCAL LLM (Ollama / vLLM)                      │
│         Orchestrated by: LangGraph                                  │
└─────────────────────────────────────────────────────────────────────┘
         │                                 │
┌────────▼──────────┐           ┌──────────▼──────────────────────────┐
│   LOCAL AI STACK  │           │        STORAGE LAYER                │
│  ┌─────────────┐  │           │  PostgreSQL + pgvector              │
│  │ Ollama      │  │           │  Qdrant (vector store)              │
│  │ (inference) │  │           │  Redis (cache/queue)                │
│  └─────────────┘  │           │  Object Storage (local/S3)          │
│  ┌─────────────┐  │           └─────────────────────────────────────┘
│  │ Embedding   │  │
│  │ (nomic/bge) │  │           ┌──────────────────────────────────────┐
│  └─────────────┘  │           │     CONNECTOR / INGESTION LAYER     │
└───────────────────┘           │  RSS/Atom  │ Reddit  │ YouTube       │
                                │  GA4  │ GSC  │ PostHog  │ Umami      │
                                │  Website Crawler  │ Sitemap          │
                                │  CSV/JSON Import  │ Webhook          │
                                └──────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Specification

### LAYER 1 — Connector & Ingestion Layer

**Purpose:** Pull data from external sources into raw storage with full provenance.

**Interface Contract (every connector must implement):**
```python
class BaseConnector:
    source_type: str          # "rss" | "reddit" | "ga4" | etc.
    compliance_mode: str      # "official_api" | "public_web" | "user_upload"

    async def validate_config(config: ConnectorConfig) -> ValidationResult
    async def test_connection(config: ConnectorConfig) -> ConnectionTestResult
    async def fetch(config: ConnectorConfig, since: datetime) -> AsyncIterator[RawDocument]
    async def health_check() -> HealthStatus
    def get_rate_limit_policy() -> RateLimitPolicy
    def get_schema() -> ConnectorSchema
```

**Connectors to implement:**

| Connector | Mode | Priority |
|-----------|------|----------|
| Website crawler | public_web | P0 (exists) |
| Sitemap | public_web | P0 |
| RSS/Atom | public_web | P0 |
| Reddit (PRAW) | official_api | P0 |
| Google Analytics 4 | official_api | P1 |
| Google Search Console | official_api | P1 |
| YouTube Data API | official_api | P1 |
| PostHog | official_api | P1 |
| Umami | official_api | P2 |
| X/Twitter | official_api | P2 (requires credentials) |
| CSV/JSON import | user_upload | P1 |
| Webhook receiver | user_upload | P2 |

**Storage:**
- Raw documents → `source_documents` table (PostgreSQL)
- Full text → object storage
- Embeddings → Qdrant

---

### LAYER 2 — Raw Storage + Normalization

**Purpose:** Store, deduplicate, and normalize all incoming data with provenance.

**Canonical Document Schema:**
```
source_document:
  id: UUID
  workspace_id: UUID
  source_connection_id: UUID
  source_type: string
  source_url: string
  raw_content: text
  content_hash: string        # SHA-256 for dedup
  normalized_content: jsonb   # Canonical form
  embedding_id: string        # Qdrant point ID
  language: string
  published_at: timestamp
  ingested_at: timestamp
  freshness_score: float
  metadata: jsonb
```

**Normalization pipeline (Dagster):**
1. Ingest raw → `source_documents`
2. Deduplicate by `content_hash`
3. Extract entities (topics, brands, products, URLs)
4. Compute embeddings via local model
5. Upsert to Qdrant

---

### LAYER 3 — Knowledge / Feature / Profile Layer

**Purpose:** Build structured intelligence objects from normalized data.

**Key entities:**

**BrandProfile:**
```
brand_profile:
  id: UUID
  workspace_id: UUID
  site_id: UUID
  value_proposition: text
  target_audience: text
  product_features: jsonb
  positioning_keywords: string[]
  icp_description: text
  pricing_model: string
  trust_signals: jsonb
  content_topics: string[]
  last_rebuilt_at: timestamp
```

**TrendRecord:**
```
trend:
  id: UUID
  workspace_id: UUID (nullable — global trends have no workspace)
  title: text
  summary: text
  keywords: string[]
  source_documents: UUID[]
  relevance_scores: jsonb   # keyed by workspace_id
  momentum_score: float     # rising=high
  volume_7d: int
  sentiment: float
  category: string
  first_seen_at: timestamp
  last_active_at: timestamp
  evidence: jsonb           # supporting post excerpts
```

**AudienceSegment:**
```
audience_segment:
  id: UUID
  workspace_id: UUID
  name: text
  description: text
  defining_signals: jsonb   # keywords, subreddits, communities
  estimated_size: int
  intent_score: float       # purchase intent
  fit_score: float          # brand fit
  channel_distribution: jsonb
  personas: UUID[]
```

---

### LAYER 4 — Local AI / Model Layer

**Purpose:** Serve all model inference locally. Zero external LLM dependency.

**Model stack:**

| Role | Default Model | Provider | VRAM |
|------|--------------|----------|------|
| Core reasoning | qwen3:235b-a22b (MoE) | Ollama | 48GB |
| Tool execution | qwen3:30b-a3b (MoE) | Ollama | 8GB |
| Fast/router | qwen3:8b | Ollama | 5GB |
| Classification | qwen3:1.7b | Ollama | 1.5GB |
| Embedding | nomic-embed-text:latest | Ollama | 0.5GB |
| Embedding (alt) | bge-m3 | sentence-transformers | 1GB |
| Reranker | bge-reranker-v2-m3 | sentence-transformers | 2GB |
| Vision | llama4:scout | Ollama | 24GB |

**CPU-only fallback:** qwen3:8b runs on CPU, ~5 tok/s. Acceptable for async workloads.

**Model serving path:**
```
Agent request
  → AIRouter (selects model by role + profile)
  → ProviderManager (routes to Ollama/vLLM)
  → Ollama (OpenAI-compat endpoint)
  → Response
```

---

### LAYER 5 — Agent / Workflow Layer

**Purpose:** Bounded, observable, tool-using agents for intelligence tasks.

**Core agents to implement:**

| Agent | Tools | Output |
|-------|-------|--------|
| TrendResearchAgent | search_trends, fetch_reddit, score_relevance | TrendRecord[] |
| BrandIntelligenceAgent | crawl_site, extract_entities, build_profile | BrandProfile |
| AudienceMatchingAgent | vector_search, score_segment, cluster_personas | AudienceSegment[] |
| GEOAuditorAgent | crawl_page, check_schema, score_citability | GEOAudit |
| SEOAuditorAgent | analyze_technical, check_indexability, score_seo | SEOAudit |
| CampaignRecommenderAgent | get_trends, get_audience, score_channel | Recommendation[] |
| FunnelAnalystAgent | get_analytics, identify_dropoffs, explain_friction | FunnelReport |
| ReportingAgent | aggregate_insights, rank_opportunities, write_report | Report |

**Agent design principles:**
- Each agent has: system role, tool list, context inputs, output schema, retry policy, trace ID
- All tool calls are logged to `model_runs` table
- No agent has internet access directly — all external access goes through connectors
- Agents return structured outputs (Pydantic models), not free text

---

### LAYER 6 — Activation / Recommendation Layer

**Purpose:** Produce actionable, evidence-backed recommendations.

**Recommendation pipeline:**
1. Trend + Brand profile → relevance score
2. Trend + Audience segment → opportunity score
3. Rank by: `relevance × opportunity × recency × confidence`
4. Generate human-readable recommendation with evidence
5. Gate by autonomy level (0=review required, 3=auto-execute)

**Recommendation types:**
- `CONTENT_OPPORTUNITY` — create content on this trend
- `CHANNEL_ACTIVATION` — engage this community/channel
- `SEO_IMPROVEMENT` — fix technical SEO issue
- `GEO_IMPROVEMENT` — improve AI discoverability
- `LANDING_PAGE` — update landing page for intent cluster
- `AUDIENCE_SEGMENT` — activate this audience segment
- `FUNNEL_FIX` — address conversion drop-off

---

### LAYER 7 — App / Dashboard / API Layer

**Purpose:** Control plane UI for operators.

**Required dashboard sections:**
1. **Brand Intelligence** — profile view, crawl status, entity map
2. **Trend Feed** — ranked trends with relevance scores
3. **Audience Insights** — segment cards with intent/fit scores
4. **GEO/SEO Workspace** — audit results, improvement queue
5. **Opportunity Feed** — actionable recommendations
6. **Campaign Suggestions** — channel + content briefs
7. **Analytics** — traffic, funnel, conversion insights
8. **Approvals** — pending actions requiring human review
9. **Connectors** — source connection management
10. **Reports** — generated intelligence reports
11. **Admin** — model config, feature flags, user management

---

## 4. Data Flow Diagrams

### Brand Onboarding Flow
```
User enters URL
  → SiteOnboardingWorkflow (Temporal)
    → validate_domain_activity
    → run_crawl_activity (WebCrawlerTool)
    → run_seo_audit_activity (SEOAuditorAgent)
    → run_brand_intel_activity (BrandIntelligenceAgent)
      → extract entities, positioning, ICP
      → embed brand documents → Qdrant
      → write BrandProfile to DB
    → run_geo_audit_activity (GEOAuditorAgent)
    → generate_initial_recommendations_activity
    → notify_complete_activity
```

### Trend Discovery Flow
```
Dagster schedule (hourly/daily)
  → TrendIngestionJob
    → For each source_connection:
      → connector.fetch(since=last_run)
      → normalize documents
      → embed + upsert to Qdrant
      → extract topics + entities
    → TrendDetectionPipeline
      → cluster recent documents by topic
      → score momentum (volume delta)
      → compute relevance for each workspace
      → write TrendRecord to DB
    → RecommendationRefreshPipeline
      → for each workspace with new trends:
        → CampaignRecommenderAgent
        → write Recommendation records
```

### GEO Audit Flow
```
User triggers audit (or scheduled weekly)
  → GEOAuditWorkflow (Temporal)
    → GEOAuditorAgent with tools:
      → check_llms_txt
      → check_robots_txt
      → analyze_schema_markup
      → score_content_citability
      → check_ai_crawler_access
      → evaluate_entity_consistency
      → analyze_answer_fragment_quality
    → write GEOAudit to DB
    → generate GEO improvement recommendations
```

---

## 5. Storage Decisions

| Store | Technology | Purpose |
|-------|-----------|---------|
| Relational | PostgreSQL 16 | All structured data, config, records |
| Vector | Qdrant | Semantic search, similarity, embeddings |
| Object | Local FS / S3-compat | Raw crawl content, artifacts, exports |
| Cache | Redis 7 | API caching, task queues, rate limiting |
| In-process | pgvector (pg16) | Lightweight semantic ops within SQL |

**Qdrant collections:**
- `brand_documents` — embedded brand/site content
- `trend_documents` — embedded trend/social documents
- `audience_signals` — embedded audience behavior signals
- `content_assets` — embedded content pieces for similarity

---

## 6. Security Model

- All LLM inference is local — no data leaves the deployment
- SSRF protections on web crawler (domain blocklist, IP range checks)
- JWT authentication with role-based access control
- Approval gates for all consequential actions
- Connector compliance mode enforced at ingestion time
- Per-workspace data isolation at database level
- Rate limiting on all external-facing endpoints
- No connector can access internal network ranges

---

## 7. Deployment Model

### Local Development
```
docker compose up          # All services
```

### Minimal (CPU-only)
```
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up
# Uses qwen3:8b on CPU, no GPU required
```

### Production
```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
# Full model stack, TLS, persistent volumes
```

### Kubernetes (future)
- Helm charts to be added in Phase 9
- Dagster on k8s natively supported
- Temporal on k8s via helm
- Qdrant distributed mode

---

## 8. Integration Map (Open Source Systems)

| System | Integration Type | Layer |
|--------|----------------|-------|
| Ollama | Local LLM serving | AI Layer |
| Qdrant | Vector database | Storage |
| Dagster | Data pipeline orchestration | Pipeline |
| PostHog | Analytics backend | Analytics Connector |
| Umami | Lightweight analytics | Analytics Connector |
| OpenReplay | Session replay | Friction analysis |
| Airbyte | Structured data ingestion | Connector Layer |
| LightFM | Hybrid recommendation | Recommendation Engine |
| RecBole | Advanced recommendation | Recommendation (exp) |
| Feast | Feature store | Feature Layer |
| Mautic | Marketing automation | Activation Layer |
| Temporal | Durable workflows | Workflow Engine |
| LangGraph | Agent orchestration | Agent Layer |
| sentence-transformers | Local embeddings | AI Layer |
