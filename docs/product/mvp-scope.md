# MVP Scope

**Version:** 1.0
**Date:** 2026-03-28

The MVP covers Phases 1-5 of the implementation roadmap.
It represents the minimum valuable product that delivers the core GrowthOS value proposition.

---

## MVP Boundary

### IN SCOPE (MVP)

#### Infrastructure
- [x] Docker Compose with: PostgreSQL, Redis, Temporal, Ollama, Qdrant, API, Worker, Web, Nginx
- [x] Local model serving via Ollama (no external LLM API required)
- [x] Qdrant vector database for semantic search
- [x] JWT authentication, multi-tenant workspace model

#### Brand Onboarding + Intelligence
- [ ] Website onboarding wizard (URL → crawl → brand profile)
- [ ] Automated brand profile extraction:
  - Value proposition
  - Target audience / ICP guess
  - Product features
  - Positioning keywords
  - Trust signals
- [ ] Brand profile storage + versioning

#### Data Ingestion
- [ ] Website crawler connector (existing, needs productionizing)
- [ ] RSS/Atom feed connector
- [ ] Reddit connector (official API)
- [ ] Connector management UI (add, test, view status)

#### Trend Discovery
- [ ] Trend detection from ingested documents
- [ ] Trend-to-brand relevance scoring
- [ ] Trend feed UI with scored cards
- [ ] Manual trend detection trigger

#### GEO / SEO Intelligence
- [x] GEO auditor engine (llms.txt, robots.txt, schema, citability, entity)
- [ ] GEO audit trigger from UI
- [ ] GEO score display with check-by-check breakdown
- [ ] GEO improvement recommendations
- [ ] Scheduled weekly GEO audit

#### Recommendations
- [ ] Rule-based + keyword matching recommendation engine
- [ ] Evidence-backed recommendation cards
- [ ] Human approval workflow

#### Reports
- [ ] Weekly intelligence summary report
- [ ] GEO audit report

---

### OUT OF SCOPE (MVP)

These are planned for post-MVP phases:

- Advanced audience segmentation with ML scoring
- LightFM / RecBole recommendation models
- PostHog / Umami analytics integration
- OpenReplay session replay integration
- Mautic marketing automation integration
- YouTube connector
- X/Twitter connector
- Feast feature store
- Kubernetes deployment
- Multi-language support
- White-label / multi-org SaaS mode
- Auto-posting / content publishing automation

---

## MVP Success Criteria

A successful MVP allows a user to:

1. **Connect a website** → system crawls it and produces a brand profile
2. **Add RSS feeds + a subreddit** → system ingests and analyzes content
3. **See a trend feed** → ranked trends with relevance scores and evidence
4. **Run a GEO audit** → get a scored report with improvement recommendations
5. **See growth recommendations** → prioritized list with evidence
6. **No external LLM API required** → everything runs locally

---

## MVP Definition of Done

- [ ] `docker compose up && make migrate && make models-pull && make seed` boots a working demo
- [ ] Demo user can log in and see the full dashboard with seeded data
- [ ] Brand onboarding flow works end-to-end for a real website
- [ ] At least one real RSS connector and Reddit connector returns data
- [ ] GEO audit runs against a real URL and returns a score
- [ ] Trend detection runs and produces ranked trend cards
- [ ] All critical paths have unit tests
- [ ] README guides a new developer to a running system in < 30 minutes
