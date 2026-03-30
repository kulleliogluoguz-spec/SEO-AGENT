# AI Growth OS — Local AI Growth Intelligence Platform

> **Fully local, self-hosted, open-source.** No external LLM API required.
> Policy-aware, approval-gated, evidence-backed growth intelligence.
> Default autonomy: **Level 1 — Draft Only.** Nothing is published without human approval.

---

## What It Is

AI CMO OS is an open, modular platform that helps growth teams:

- Understand their product and positioning (from crawled site data)
- Discover SEO opportunities with evidence-backed recommendations
- Generate content briefs and AI-assisted drafts (always in review mode)
- Evaluate AI/LLM discoverability (GEO/AEO — experimental)
- Manage an approval queue before any publishing action
- Generate weekly/monthly growth reports
- Track recommendations and experiments

It is **not** a spam bot. It is **not** autonomous. By default, all AI output goes into a human review queue.

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB RAM minimum
- Ports 3000, 5432, 6379, 7233, 8000, 8088 available

### 1. Clone and configure

```bash
git clone https://github.com/yourorg/ai-growth-os.git
cd ai-growth-os
cp .env.example .env
# No external API key needed — the platform runs fully locally via Ollama
```

### 2. Start all services

```bash
make up
# or: docker compose up --build -d
```

This starts: PostgreSQL, Redis, Temporal, **Ollama** (local LLM), **Qdrant** (vector store), API, Worker, Frontend.

### 2a. CPU-only machines (no GPU)

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
```

### 2b. Pull local AI models

```bash
make models-pull          # Tier 1: qwen3:8b + nomic-embed-text (~6GB)
make models-pull-tier2    # Tier 2: + qwen3:30b-a3b (~15GB, consumer GPU)
make models-pull-tier3    # Tier 3: + qwen3:235b-a22b (~60GB, production GPU)
```

### 3. Run migrations and seed demo data

```bash
make migrate   # Creates all database tables
make seed      # Loads demo workspace, site, recommendations, reports
```

### 4. Open the app

```
http://localhost:3000
```

Sign in: `demo@aicmo.os` / `Demo1234!`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Next.js Frontend (port 3000)                  │
│     Login · Dashboard · SEO · Content · Approvals · Reports  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/JSON — Bearer JWT
┌──────────────────────────▼──────────────────────────────────┐
│              FastAPI Backend (port 8000)                       │
│   /auth · /sites · /crawls · /recommendations                 │
│   /content · /approvals · /reports · /connectors             │
├──────────────────────────┬──────────────────────────────────┤
│    LangGraph Agent Graphs │   Temporal Durable Workflows      │
│    138 agents / 13 layers │   Scheduling · Retries · Resumes │
└──────────────┬────────────┴───────────────┬─────────────────┘
               │                            │
┌──────────────▼────────────────────────────▼─────────────────┐
│            PostgreSQL 16 + pgvector + Redis                   │
└─────────────────────────────────────────────────────────────┘
```

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| ORM / Migrations | SQLAlchemy 2.x, Alembic |
| Agent Orchestration | LangGraph |
| Durable Workflows | Temporal |
| Crawling | httpx + Playwright (JS fallback) |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Auth | JWT (HS256) + bcrypt, workspace RBAC |
| Container | Docker Compose |

---

## Developer Commands

```bash
make help          # Full command list
make up            # Start all services
make migrate       # Run DB migrations
make seed          # Load demo data
make test          # All backend tests
make test-unit     # Unit tests only (fast)
make lint          # Ruff + ESLint
make health        # Check service health
make shell-api     # Shell into API container
make shell-db      # Open psql session
make logs-api      # Tail API logs
make reseed        # Wipe and re-seed (DESTRUCTIVE)
```

---

## Environment Variables

See `.env.example` for all variables. Critical ones:

| Variable | Default | Required |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | _(empty)_ | For real AI output |
| `SECRET_KEY` | `change-me...` | **Change in production** |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Yes |
| `DEMO_MODE` | `false` | `true` for mock data |
| `AUTONOMY_DEFAULT_LEVEL` | `1` | 0–3 (never set 4 by default) |

---

## Autonomy Levels

| Level | Behavior |
|-------|----------|
| 0 | Analysis only — read-only intelligence |
| 1 | **Draft only (default)** — all output requires human review |
| 2 | Approval-required — queued actions need explicit approval |
| 3 | Low-risk auto — minor changes execute without approval |
| 4 | Advanced auto — **disabled by default, never set in production without careful policy review** |

---

## Repo Structure

```
ai-cmo-os/
├── apps/
│   ├── api/                     # FastAPI backend
│   │   ├── app/
│   │   │   ├── agents/          # 138 agents across 13 layers
│   │   │   ├── api/endpoints/   # REST endpoints
│   │   │   ├── core/            # Config, DB, security, feature flags
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── services/        # Business logic + scoring
│   │   │   ├── tools/           # WebCrawlerTool (SSRF-protected)
│   │   │   ├── workers/         # Temporal workflow definitions
│   │   │   ├── connectors/      # GA4, GSC, Slack (mock + real)
│   │   │   ├── prompts/         # Versioned prompt registry
│   │   │   └── evaluations/     # Quality harness
│   │   ├── tests/               # Unit + integration tests
│   │   ├── alembic/             # Migrations (initial schema included)
│   │   ├── scripts/             # seed_demo.py
│   │   └── worker_main.py       # Temporal worker entry point
│   ├── web/                     # Next.js 14 frontend (11 screens)
│   └── workers/                 # Legacy worker path (symlinked)
├── docs/                        # Architecture, ADRs, security, runbook
├── infra/postgres/init/         # pgvector + uuid extension setup
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flows |
| [AGENT_REGISTRY.md](docs/AGENT_REGISTRY.md) | All 138 agents documented |
| [SECURITY.md](docs/SECURITY.md) | Security model and SSRF protections |
| [DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Step-by-step demo walkthrough |
| [RUNBOOK.md](docs/RUNBOOK.md) | Operational procedures |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | What's demo vs production-ready |
| [ROADMAP.md](docs/ROADMAP.md) | Planned improvements |

---

## What's Real vs Mocked

| Component | Status |
|-----------|--------|
| FastAPI backend, auth, RBAC | ✅ Production-quality |
| SQLAlchemy models + initial migration | ✅ Complete |
| WebCrawlerTool (SSRF-protected) | ✅ Real |
| PolicyGateAgent + ComplianceGuardian | ✅ Real |
| TechnicalSEOAuditAgent (rule-based) | ✅ Real |
| LLM agents (all layers) | ✅ Real (needs `ANTHROPIC_API_KEY`) |
| LangGraph onboarding graph | ✅ Real |
| Temporal workflow definitions | ✅ Real (needs Temporal running) |
| Next.js dashboard (11 screens) | ✅ Working |
| GA4 / Search Console connectors | 🟡 Mock with realistic data |
| Slack connector | 🟡 Mock (real adapter ready) |
| CMS / social publishing | 🔲 Interface stub only |
| Report PDF export | 🔲 Not implemented (Markdown export works) |
| Real-time updates (WebSocket) | 🔲 Not implemented |

---

## Troubleshooting

See [RUNBOOK.md](docs/RUNBOOK.md) for detailed procedures.

**Common issues:**
- `make migrate` fails → PostgreSQL may not be ready. Wait 30s, retry.
- Agents return placeholder content → Add `ANTHROPIC_API_KEY` to `.env`
- Worker exits immediately → Temporal taking longer to start; worker has graceful retry
- Frontend blank page → Check `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## Contributing

1. Fork and create a feature branch
2. `pre-commit install` (installs ruff, mypy hooks)
3. Make changes + add tests
4. `make test && make lint`
5. Submit PR with clear description

See [CONTRIBUTING.md](CONTRIBUTING.md) for more.

---

## License

MIT — see [LICENSE](LICENSE)
