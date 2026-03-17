# Known Limitations — AI CMO OS v0.1.0

## LLM / AI

- **No API key = demo mode only**: Without `ANTHROPIC_API_KEY`, all LLM agents return placeholder content. This is intentional for safe first-run experience.
- **Hallucination risk**: LLM agents may produce inaccurate product summaries, ICP inferences, or recommendations. Always review outputs before acting.
- **Context window limits**: Very large sites (1000+ pages) may require chunked processing not yet implemented.

## GEO/AEO Module (Experimental)

- GEO/AEO signals are **inferred from site content**, not measured from live AI answer surfaces
- No integration with Perplexity, ChatGPT, or other AI answer surfaces (no public API available)
- Results should be treated as directional, not definitive
- This is an emerging field; scoring methodology will evolve

## Crawling

- JavaScript-heavy SPAs may not be fully crawled without Playwright enabled
- Playwright requires Chromium installed (added to Docker image; slower to build)
- Very large sitemaps (10,000+ URLs) are not fully parsed yet
- Authentication-gated pages are not crawled

## Analytics Connectors

- GA4 and Search Console connectors return **mock data by default**
- Real connector requires Google service account credentials and API setup
- No automatic data refresh scheduling yet (must trigger manually)

## Temporal Workflows

- Temporal requires a running Temporal server (included in Docker Compose)
- Without Temporal running, workflows fall back to direct async execution
- Temporal UI is available at localhost:8088 but workflow visibility is basic
- Scheduled/periodic workflows (weekly reports) require Temporal cron setup

## Content

- Generated content always goes to REVIEW status — no auto-publishing
- Content revision workflow (approve + request edits) is basic
- No real CMS connector implemented; stub only
- Social publishing connectors are stubs

## Frontend

- No real-time updates (WebSocket/SSE not implemented); manual refresh required
- Report export (PDF) is not implemented; Markdown export only
- Site detail pages (individual site view) are basic stubs
- No mobile-optimized layout

## Multi-Tenancy

- User invitation flow is not implemented (must create users via API/seed)
- Organization billing/plan management is a stub
- SSO/OAuth login not implemented (email/password only)

## Performance

- No query caching layer for repeated recommendation queries
- Large crawls (500+ pages) may time out on default Uvicorn configuration
- No background indexing for vector similarity search yet

## Security

- Rate limiting middleware is defined but Redis-backed enforcement requires Redis running
- CSP headers not configured for frontend
- Session invalidation (token revocation) requires Redis token blacklist (not implemented)

## Tests

- E2E browser tests use Playwright but are not fully implemented
- Integration tests use SQLite (not full PostgreSQL feature parity)
- Load/performance tests not included

## Future Work

See [ROADMAP.md](ROADMAP.md) for planned improvements.
