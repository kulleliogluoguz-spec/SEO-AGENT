# ADR-005: Connector SDK — Unified Source Ingestion Interface

**Status:** Accepted
**Date:** 2026-03-28

---

## Context

The platform needs to ingest data from many sources: websites, RSS feeds, Reddit, YouTube, Google Analytics, Search Console, PostHog, and more. Each source has different auth patterns, rate limits, data formats, and compliance requirements.

Without a unified connector SDK:
- Each source connector would be ad hoc
- Compliance requirements would be inconsistently enforced
- Rate limiting would be duplicated
- New connectors would be hard to add

## Decision

We adopt a formal **Connector SDK** at `packages/connector-sdk/` (Python package) with the following design:

### Compliance Modes (mandatory per connector)

```python
class ComplianceMode(str, Enum):
    OFFICIAL_API = "official_api"      # Uses official, credentialed API
    PUBLIC_WEB = "public_web"          # Accesses public, robots.txt-respecting web
    USER_UPLOAD = "user_upload"        # User provides their own data export
```

Every connector must declare its compliance mode. Connectors in `PUBLIC_WEB` mode must:
- Respect `robots.txt`
- Rate limit to ≤ 1 req/sec by default
- Include a `User-Agent` identifying the bot
- Check `CRAWL_BLOCKED_DOMAINS` list
- Never access credential-protected pages

### Base Interface

```python
class BaseConnector(ABC):
    source_type: ClassVar[str]
    compliance_mode: ClassVar[ComplianceMode]

    @abstractmethod
    async def validate_config(config: ConnectorConfig) -> ValidationResult: ...

    @abstractmethod
    async def test_connection(config: ConnectorConfig) -> ConnectionTestResult: ...

    @abstractmethod
    async def fetch(config: ConnectorConfig, since: datetime | None) -> AsyncIterator[RawDocument]: ...

    async def health_check() -> HealthStatus: ...
    def get_rate_limit_policy() -> RateLimitPolicy: ...
    def get_schema() -> ConnectorSchema: ...
```

### RawDocument Schema

Every connector yields `RawDocument` objects with:
- `id`: deterministic UUID based on source + content hash
- `source_type`: connector type
- `source_url`: canonical URL of the document
- `content_hash`: SHA-256 of raw content (for dedup)
- `raw_text`: full text content
- `title`: document title
- `author`: author if available
- `published_at`: original publish timestamp
- `metadata`: source-specific fields as dict
- `compliance_mode`: inherited from connector

### Connector Registry

Connectors are registered globally:
```python
ConnectorRegistry.register(RedditConnector)
ConnectorRegistry.get("reddit")
ConnectorRegistry.list_available()
```

## Implementation Plan

1. Create `packages/connector-sdk/` as a Python package
2. Implement `BaseConnector`, `RawDocument`, `ConnectorConfig`, `ConnectorRegistry`
3. Implement initial connectors: `WebsiteConnector`, `RSSConnector`, `RedditConnector`
4. Wire into Dagster pipelines for scheduled ingestion
5. Store in `source_connections` (config) + `source_documents` (raw data)

## Consequences

### Positive
- Consistent compliance enforcement across all sources
- Easy to add new connectors
- Rate limiting and error handling standardized
- Clear documentation of what data is collected and how

### Negative
- More initial complexity than ad hoc connectors
- Connectors must implement the full interface (boilerplate)

## Rejected Alternatives

- **Airbyte as primary connector framework:** Airbyte is excellent for structured ELT but is heavyweight and primarily designed for database-to-warehouse pipelines. Our connectors need real-time semantics, compliance mode tracking, and embedding integration. We may add Airbyte compatibility as an optional data import path but will not depend on it.
