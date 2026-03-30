# Platform Integration Policy

**Version:** 1.0
**Date:** 2026-03-28

This document defines the compliance and legal framework for integrating external data sources into the AI Growth OS platform.

---

## 1. Three Integration Modes

### Mode A: Official API Integration (Preferred)
- Uses the platform's official, public API
- Requires valid credentials (API keys, OAuth tokens)
- Governed by the platform's Terms of Service and API Terms
- Rate limits set by the platform must be respected
- **Examples:** Reddit API, Google Analytics API, Twitter API v2, YouTube Data API

### Mode B: Limited Public Web Intelligence
- Accesses publicly available, non-authenticated web content
- Must respect `robots.txt` directives
- Must identify the bot via User-Agent
- Rate limited to avoid server burden
- Cannot access content behind login walls
- Cannot access paywalled or restricted content
- **Examples:** RSS feeds, public blog posts, public sitemaps, news articles

### Mode C: User-Provided Data
- User uploads or provides their own data exports
- No external network requests
- User is responsible for the legality of the data they provide
- **Examples:** GA4 data exports, CRM exports, campaign CSVs, analytics exports

---

## 2. What We Do NOT Do

The platform is explicitly NOT designed to:

- Scrape platforms in violation of their Terms of Service
- Bypass authentication or rate limits
- Mass-harvest user data from social platforms
- Build unauthorized shadow profiles of individuals
- Operate fake accounts, bots, or sockpuppets
- Auto-post content to third-party platforms without explicit user authorization
- Access private or member-only content without authorization
- Violate copyright or intellectual property rights
- Engage in competitive scraping attacks

---

## 3. Platform-Specific Notes

### Reddit
- **Official API:** PRAW with registered app credentials (free)
- Rate limit: 60 requests/minute (enforced)
- Must use valid `User-Agent` identifying the application
- Do not extract or store personally identifying information about Reddit users
- Respect subreddit rules regarding data usage

### Google Analytics / Search Console
- Official Google APIs only (via Service Account credentials)
- Data belongs to the website owner who grants access
- Do not share analytics data across workspaces

### Twitter / X
- Official API v2 only (when credentials are provided)
- Disabled by default (requires API credentials)
- Academic and elevated access tiers may be needed for trend-level access
- Do not store full tweet content beyond what the API terms allow

### YouTube
- YouTube Data API v3 only
- API quota limits must be respected
- Video content analysis (if any) must comply with YouTube TOS

### Web Crawling
- Respect `robots.txt` in all crawling operations
- `Crawl-delay` directives in robots.txt are honored
- Internal IP ranges and local hosts are blocked (SSRF protection)
- User-Agent is set to identify the bot: `AIGrowthOS/1.0 (growth-analysis; +https://your-domain)`
- Maximum crawl rate: 1 request/second default, configurable down, not up

---

## 4. Data Retention and Privacy

- Raw source documents are stored for the configured retention period (default: 90 days)
- Personal data in documents (emails, names) is not indexed in vector stores
- Workspace data is isolated — no cross-workspace data leakage
- Users can delete their workspace and all associated data at any time
- No raw data is used to train any shared model

---

## 5. Compliance Warnings

The following features carry compliance risks that users must acknowledge:

| Feature | Risk Level | Notes |
|---------|-----------|-------|
| Public web crawling | LOW | Limited to robots.txt-compliant access |
| Reddit trend monitoring | LOW | Official API; respect TOS |
| Social media auto-posting | HIGH | Disabled by default; requires explicit opt-in + credentials |
| Web content scraping beyond crawl | HIGH | Not implemented by default |
| Competitor website monitoring | MEDIUM | Only public pages; rate limited |
| Email harvesting | PROHIBITED | Not implemented, never will be |

---

## 6. User Responsibilities

Users of the platform are responsible for:

1. Ensuring they have the right to access data they connect
2. Complying with the TOS of any platform they connect
3. Not using the platform to violate privacy laws (GDPR, CCPA, etc.)
4. Obtaining necessary consents before engaging with individuals based on platform intelligence
5. Keeping API credentials secure

The platform operators are not liable for user misuse.

---

## 7. Enforcement in Code

Every connector in `apps/api/app/connectors/` must:

1. Declare `compliance_mode` as `official_api`, `public_web`, or `user_upload`
2. Implement `robots.txt` checking if `compliance_mode == "public_web"`
3. Enforce rate limits via `RateLimitPolicy`
4. Block requests to `CRAWL_BLOCKED_DOMAINS`
5. Include a compliance warning in the connector's `get_compliance_notes()` method

Connectors that bypass these requirements will not be merged.
