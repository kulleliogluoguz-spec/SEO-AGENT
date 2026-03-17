# Deployment Guide

## Development
```bash
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

## Production Checklist
- Set SECRET_KEY to 32+ random chars
- Set ENVIRONMENT=production
- Disable /docs endpoint
- Use managed PostgreSQL (RDS, Cloud SQL, Supabase)
- Use Temporal Cloud or self-hosted Temporal cluster
- Configure S3-compatible storage for artifacts
- Set up secrets manager for all credentials
- Enable HTTPS with TLS termination at load balancer
- Configure CORS origins explicitly
- Set up monitoring (Datadog, Sentry, etc.)
- Enable audit log retention policy

## Environment Variables (Production)
See .env.example for all variables. Critical:
- ENVIRONMENT=production
- DATABASE_URL (use a connection pooler like PgBouncer)
- SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
- ANTHROPIC_API_KEY
- TEMPORAL_HOST (Temporal Cloud endpoint)
