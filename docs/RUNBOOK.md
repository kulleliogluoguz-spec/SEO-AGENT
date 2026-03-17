# Runbook — AI CMO OS

Operational procedures for running and maintaining AI CMO OS.

## First-Time Setup

```bash
# 1. Clone and configure
git clone https://github.com/yourorg/ai-cmo-os.git
cd ai-cmo-os
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY if available

# 2. Start all services
make up

# 3. Wait for services to be ready (usually 30-60 seconds)
make health

# 4. Run migrations
make migrate

# 5. Seed demo data
make seed

# 6. Open browser
open http://localhost:3000
```

## Common Operations

### Starting / Stopping

```bash
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services
make ps          # Check status
```

### Viewing Logs

```bash
make logs        # All services
make logs-api    # API only
make logs-worker # Worker only
docker compose logs -f --tail=100 api  # Last 100 lines
```

### Database Operations

```bash
make migrate                      # Apply pending migrations
make migrate-down                 # Roll back last migration
make migrate-create NAME=add_foo  # Create new migration
make shell-db                     # Open psql session
```

### Running Tests

```bash
make test              # All tests
make test-unit         # Unit tests only (fast, ~5s)
make test-integration  # Integration tests (~15s)
make test-coverage     # With coverage report
```

## Troubleshooting

### API won't start

**Symptom:** `make health` returns "API not responding"

```bash
# Check logs
make logs-api

# Common causes:
# 1. DB not ready — wait 30s, retry
# 2. Port 8000 already in use: lsof -i :8000
# 3. Python import error — check logs for traceback
```

### Migrations fail

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check connection
make shell-db

# If alembic state is broken:
docker compose exec api alembic stamp head  # Mark as up-to-date without running
docker compose exec api alembic history     # See history
```

### Seed fails with "Email already exists"

Demo data is already seeded. Either use it as-is, or:

```bash
make reseed  # Drops all data and reseeds (DESTRUCTIVE)
```

### Worker not processing workflows

```bash
# Check worker is running
make ps

# Check Temporal is healthy
curl http://localhost:7233  # Should return gRPC response

# Check worker logs
make logs-worker

# Temporal UI
open http://localhost:8088
```

### LLM agents return placeholder content

Set `ANTHROPIC_API_KEY` in `.env` and restart:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
docker compose restart api worker
```

### Frontend shows blank page

```bash
# Check Next.js is running
make ps

# Check NEXT_PUBLIC_API_URL is correct
docker compose exec web env | grep API_URL

# Check API is accessible from browser
curl http://localhost:8000/health
```

## Health Check Summary

| Service | URL | Expected |
|---------|-----|----------|
| API liveness | http://localhost:8000/health | `{"status":"ok"}` |
| API readiness | http://localhost:8000/health/ready | `{"status":"ready"}` |
| API docs | http://localhost:8000/docs | Swagger UI |
| Frontend | http://localhost:3000 | Login page |
| Temporal UI | http://localhost:8088 | Workflow dashboard |

## Monitoring

In development, use `make logs` + `make health`.

For production, instrument with:
- **APM**: Datadog, Sentry, or New Relic
- **Logs**: Structured JSON logs ship to your log aggregator
- **Metrics**: OpenTelemetry integration (planned)
- **Alerts**: Set up on `GET /health/ready` returning non-200

## Backup Procedure

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U aicmo aicmo > backup-$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql -U aicmo aicmo < backup-20240101.sql
```

## Security Incidents

1. Rotate `SECRET_KEY` immediately (invalidates all sessions)
2. Rotate `ANTHROPIC_API_KEY`
3. Review `activity_logs` table for suspicious actions
4. Check approval queue for unauthorized actions

```bash
# View recent activity logs
make shell-db
# Then: SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 100;
```
