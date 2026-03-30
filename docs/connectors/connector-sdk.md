# Connector SDK

The Connector SDK defines how external data sources are integrated into the AI Growth OS platform. Every connector must implement the `BaseConnector` interface and declare its compliance mode.

---

## Compliance Modes

Every connector belongs to exactly one compliance mode:

| Mode | Description | Requirements |
|------|-------------|-------------|
| `official_api` | Uses an official, credentialed API | Valid credentials required; respects API TOS |
| `public_web` | Accesses publicly available web content | Must respect robots.txt; rate limited; no auth bypass |
| `user_upload` | User provides their own data export | No external calls; validates file format |

**This distinction is mandatory.** Connectors must never blur these modes.

---

## BaseConnector Interface

Location: `packages/connector-sdk/connector_sdk/base.py`

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator

class BaseConnector(ABC):
    source_type: ClassVar[str]           # e.g. "rss", "reddit", "ga4"
    compliance_mode: ClassVar[ComplianceMode]
    display_name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    async def validate_config(self, config: ConnectorConfig) -> ValidationResult:
        """Validate that the config is complete and credentials work."""

    @abstractmethod
    async def test_connection(self, config: ConnectorConfig) -> ConnectionTestResult:
        """Attempt a real connection to verify the source is reachable."""

    @abstractmethod
    async def fetch(
        self,
        config: ConnectorConfig,
        since: datetime | None = None,
    ) -> AsyncIterator[RawDocument]:
        """Yield RawDocument objects from the source."""

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        """Return the rate limiting policy for this connector."""
        return RateLimitPolicy(requests_per_second=1.0)

    async def health_check(self) -> HealthStatus:
        """Quick health check (no credentials needed)."""
        return HealthStatus(healthy=True)

    def get_config_schema(self) -> dict:
        """Return JSON Schema for the connector's config fields."""
        return {}
```

---

## RawDocument Schema

```python
@dataclass
class RawDocument:
    id: str                    # Deterministic UUID: sha256(source_type + source_url)
    source_type: str           # Connector type
    source_url: str            # Canonical URL
    content_hash: str          # SHA-256 of raw_text (for dedup)
    raw_text: str              # Full text content
    title: str = ""
    author: str = ""
    published_at: datetime | None = None
    language: str = "en"
    metadata: dict = field(default_factory=dict)
    compliance_mode: str = ""  # Inherited from connector
    ingested_at: datetime = field(default_factory=datetime.utcnow)
```

---

## ConnectorConfig Schema

```python
@dataclass
class ConnectorConfig:
    workspace_id: str
    source_type: str
    display_name: str
    params: dict                # Source-specific parameters
    credentials: dict = field(default_factory=dict)  # Encrypted at rest
    enabled: bool = True
    fetch_interval_minutes: int = 60
    max_documents_per_run: int = 500
    last_fetch_at: datetime | None = None
```

---

## Available Connectors

### Website Crawler (`website`)
- **Mode:** `public_web`
- **Purpose:** Crawl a website, extract pages + metadata
- **Params:** `url`, `max_pages`, `follow_sitemaps`, `respect_robots`
- **Compliance:** Respects robots.txt, rate limited, SSRF-protected

### Sitemap (`sitemap`)
- **Mode:** `public_web`
- **Purpose:** Parse sitemap.xml to discover all URLs
- **Params:** `sitemap_url`
- **Output:** URL list with metadata

### RSS/Atom (`rss`)
- **Mode:** `public_web`
- **Purpose:** Monitor RSS/Atom feeds for new content
- **Params:** `feed_url`, `tags` (optional filtering keywords)
- **Compliance:** Respects feed-level rate limits

### Reddit (`reddit`)
- **Mode:** `official_api`
- **Purpose:** Monitor subreddits for trends and discussions
- **Params:** `subreddits` (list), `keywords` (optional), `time_filter`
- **Credentials:** `client_id`, `client_secret`, `user_agent`
- **Rate limit:** 60 requests/minute (Reddit API limit)
- **Note:** Requires free Reddit API credentials

### Google Analytics 4 (`ga4`)
- **Mode:** `official_api`
- **Purpose:** Website traffic, session, and conversion data
- **Credentials:** Google Service Account JSON
- **Params:** `property_id`, `date_range_days`

### Google Search Console (`gsc`)
- **Mode:** `official_api`
- **Purpose:** Keyword rankings, click data, impressions
- **Credentials:** Google Service Account JSON
- **Params:** `site_url`, `date_range_days`

### PostHog (`posthog`)
- **Mode:** `official_api`
- **Purpose:** Product analytics, funnel data, event streams
- **Credentials:** `api_key`, `project_id`
- **Params:** `host` (for self-hosted PostHog)

### Umami (`umami`)
- **Mode:** `official_api`
- **Purpose:** Lightweight privacy-first web analytics
- **Credentials:** `api_key`, `website_id`
- **Params:** `host`

### CSV/JSON Import (`file_import`)
- **Mode:** `user_upload`
- **Purpose:** User-provided data exports (CRM, campaigns, etc.)
- **Params:** `file_path`, `schema_type`

---

## Adding a New Connector

1. Create `apps/api/app/connectors/{source_type}/connector.py`
2. Implement `BaseConnector`
3. Register in `apps/api/app/connectors/registry.py`
4. Add config schema and display metadata
5. Add Dagster op in `apps/dagster/ops/connectors/{source_type}.py`
6. Add to connector UI in `apps/web/app/dashboard/connectors/`

### Example: Minimal RSS Connector

```python
from connector_sdk.base import BaseConnector, ComplianceMode, RawDocument, ConnectorConfig
import feedparser

class RSSConnector(BaseConnector):
    source_type = "rss"
    compliance_mode = ComplianceMode.PUBLIC_WEB
    display_name = "RSS / Atom Feed"
    description = "Monitor any RSS or Atom feed for new content"

    async def validate_config(self, config: ConnectorConfig) -> ValidationResult:
        if "feed_url" not in config.params:
            return ValidationResult(valid=False, errors=["feed_url is required"])
        return ValidationResult(valid=True)

    async def test_connection(self, config: ConnectorConfig) -> ConnectionTestResult:
        feed = feedparser.parse(config.params["feed_url"])
        if feed.bozo:
            return ConnectionTestResult(success=False, error=str(feed.bozo_exception))
        return ConnectionTestResult(success=True, message=f"Found {len(feed.entries)} entries")

    async def fetch(self, config: ConnectorConfig, since=None) -> AsyncIterator[RawDocument]:
        feed = feedparser.parse(config.params["feed_url"])
        for entry in feed.entries:
            yield RawDocument(
                id=make_doc_id("rss", entry.link),
                source_type="rss",
                source_url=entry.link,
                content_hash=sha256(entry.get("summary", "")),
                raw_text=entry.get("summary", ""),
                title=entry.get("title", ""),
                author=entry.get("author", ""),
                published_at=parse_date(entry.get("published")),
            )
```

---

## Compliance Checklist

Before any connector can be merged, it must pass:

- [ ] Compliance mode is declared and accurate
- [ ] Credentials are never logged or stored in plain text
- [ ] Rate limiting is implemented and documented
- [ ] `robots.txt` is respected (for `public_web` mode)
- [ ] SSRF protection: no access to internal IPs/domains
- [ ] Error handling: connector fails gracefully, doesn't crash the pipeline
- [ ] `test_connection` actually tests the connection
- [ ] Documentation added to this file
