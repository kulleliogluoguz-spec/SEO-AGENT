"""
Reddit Connector — Official API via PRAW

Compliance mode: OFFICIAL_API
- Uses Reddit's official API via PRAW (Python Reddit API Wrapper)
- Requires registered Reddit app credentials (free)
- Respects rate limits: 60 requests/minute for free tier
- Does NOT scrape Reddit; uses only the official REST API

Setup:
  1. Go to https://www.reddit.com/prefs/apps
  2. Create a "script" type app
  3. Note the client_id and client_secret
  4. Set user_agent to: "AIGrowthOS/1.0 (growth-intelligence)"

ConnectorConfig params:
    subreddits: list[str]     — subreddits to monitor (without r/)
    keywords: list[str]       — optional keyword filter
    time_filter: str          — "hour" | "day" | "week" (default: "day")
    sort: str                 — "hot" | "new" | "top" (default: "hot")
    limit: int                — max posts per subreddit per run (default: 25)

ConnectorConfig credentials:
    client_id: str
    client_secret: str
    user_agent: str           — defaults to "AIGrowthOS/1.0"
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

try:
    from connector_sdk.base import (
        BaseConnector,
        ComplianceMode,
        ConnectorConfig,
        ConnectionTestResult,
        RateLimitPolicy,
        RawDocument,
        ValidationResult,
        make_content_hash,
        make_doc_id,
    )
    from connector_sdk.registry import ConnectorRegistry
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../packages/connector-sdk"))
    from connector_sdk.base import (
        BaseConnector,
        ComplianceMode,
        ConnectorConfig,
        ConnectionTestResult,
        RateLimitPolicy,
        RawDocument,
        ValidationResult,
        make_content_hash,
        make_doc_id,
    )
    from connector_sdk.registry import ConnectorRegistry


@ConnectorRegistry.register
class RedditConnector(BaseConnector):
    """
    Reddit connector using the official PRAW library.

    Monitors subreddits for posts matching optional keywords.
    Supports incremental fetch via the `since` parameter.
    """

    source_type = "reddit"
    compliance_mode = ComplianceMode.OFFICIAL_API
    display_name = "Reddit"
    description = "Monitor subreddits for trending discussions and pain points (official Reddit API)"

    async def validate_config(self, config: ConnectorConfig) -> ValidationResult:
        errors = []
        if not config.credentials.get("client_id"):
            errors.append("client_id is required in credentials")
        if not config.credentials.get("client_secret"):
            errors.append("client_secret is required in credentials")
        if not config.params.get("subreddits"):
            errors.append("subreddits list is required in params")
        elif not isinstance(config.params["subreddits"], list):
            errors.append("subreddits must be a list of strings")
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def test_connection(self, config: ConnectorConfig) -> ConnectionTestResult:
        try:
            reddit = self._get_reddit_client(config)
            # Try a simple authenticated request
            loop = asyncio.get_event_loop()
            me = await loop.run_in_executor(None, lambda: reddit.user.me())
            return ConnectionTestResult(
                success=True,
                message=f"Connected to Reddit API (authenticated as {me})",
            )
        except Exception as e:
            return ConnectionTestResult(success=False, error=str(e))

    async def fetch(
        self,
        config: ConnectorConfig,
        since: Optional[datetime] = None,
    ) -> AsyncIterator[RawDocument]:
        subreddits = config.params.get("subreddits", [])
        keywords = config.params.get("keywords", [])
        time_filter = config.params.get("time_filter", "day")
        sort = config.params.get("sort", "hot")
        limit = min(config.params.get("limit", 25), 100)  # Cap at 100 per subreddit
        max_docs = config.max_documents_per_run

        reddit = self._get_reddit_client(config)
        total_yielded = 0

        for subreddit_name in subreddits:
            if total_yielded >= max_docs:
                break

            try:
                loop = asyncio.get_event_loop()
                posts = await loop.run_in_executor(
                    None,
                    lambda sr=subreddit_name: self._fetch_subreddit_posts(
                        reddit, sr, sort, time_filter, limit
                    ),
                )

                for post in posts:
                    if total_yielded >= max_docs:
                        break

                    # Incremental fetch filter
                    if since:
                        post_created = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
                        if post_created <= since.replace(tzinfo=timezone.utc):
                            continue

                    # Keyword filter
                    combined_text = f"{post['title']} {post['selftext']}".lower()
                    if keywords and not any(kw.lower() in combined_text for kw in keywords):
                        continue

                    raw_text = self._build_post_text(post)
                    if not raw_text.strip():
                        continue

                    yield RawDocument(
                        id=make_doc_id("reddit", post["url"]),
                        source_type="reddit",
                        source_url=post["url"],
                        content_hash=make_content_hash(raw_text),
                        raw_text=raw_text,
                        title=post["title"],
                        author=post.get("author", "[deleted]"),
                        published_at=datetime.fromtimestamp(
                            post["created_utc"], tz=timezone.utc
                        ),
                        compliance_mode=self.compliance_mode.value,
                        metadata={
                            "subreddit": subreddit_name,
                            "score": post.get("score", 0),
                            "num_comments": post.get("num_comments", 0),
                            "upvote_ratio": post.get("upvote_ratio", 0.0),
                            "is_self": post.get("is_self", True),
                            "flair": post.get("link_flair_text", ""),
                            "post_id": post["id"],
                        },
                    )
                    total_yielded += 1

            except Exception as e:
                logger.error(f"RedditConnector: error fetching r/{subreddit_name}: {e}")
                continue

        logger.info(f"RedditConnector: yielded {total_yielded} posts from {subreddits}")

    def _get_reddit_client(self, config: ConnectorConfig):
        """Create a PRAW Reddit client from config credentials."""
        try:
            import praw
        except ImportError:
            raise RuntimeError(
                "praw is not installed. Run: pip install praw"
            )

        return praw.Reddit(
            client_id=config.credentials["client_id"],
            client_secret=config.credentials["client_secret"],
            user_agent=config.credentials.get("user_agent", "AIGrowthOS/1.0 (growth-intelligence)"),
            read_only=True,  # Always read-only — we never post
        )

    def _fetch_subreddit_posts(
        self,
        reddit,
        subreddit_name: str,
        sort: str,
        time_filter: str,
        limit: int,
    ) -> list[dict]:
        """Synchronous fetch of subreddit posts (runs in thread pool)."""
        subreddit = reddit.subreddit(subreddit_name)

        if sort == "hot":
            submissions = subreddit.hot(limit=limit)
        elif sort == "new":
            submissions = subreddit.new(limit=limit)
        elif sort == "top":
            submissions = subreddit.top(time_filter=time_filter, limit=limit)
        elif sort == "rising":
            submissions = subreddit.rising(limit=limit)
        else:
            submissions = subreddit.hot(limit=limit)

        posts = []
        for sub in submissions:
            posts.append({
                "id": sub.id,
                "title": sub.title,
                "selftext": sub.selftext,
                "url": f"https://reddit.com{sub.permalink}",
                "score": sub.score,
                "upvote_ratio": sub.upvote_ratio,
                "num_comments": sub.num_comments,
                "created_utc": sub.created_utc,
                "author": str(sub.author) if sub.author else "[deleted]",
                "is_self": sub.is_self,
                "link_flair_text": sub.link_flair_text,
            })
        return posts

    def _build_post_text(self, post: dict) -> str:
        """Build normalized text content from a Reddit post."""
        parts = [post["title"]]
        if post.get("selftext") and post["selftext"] not in ("[removed]", "[deleted]"):
            parts.append(post["selftext"])
        return "\n\n".join(parts)

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(
            requests_per_second=1.0,
            requests_per_minute=60,   # Reddit free tier: 60/min
            requests_per_day=86400,
            retry_after_seconds=60,
        )

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of subreddit names to monitor (without r/)",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional keywords to filter posts (OR match on title + body)",
                },
                "sort": {
                    "type": "string",
                    "enum": ["hot", "new", "top", "rising"],
                    "default": "hot",
                    "description": "Post sort order",
                },
                "time_filter": {
                    "type": "string",
                    "enum": ["hour", "day", "week", "month", "year", "all"],
                    "default": "day",
                    "description": "Time filter (used with sort=top)",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 25,
                    "description": "Max posts per subreddit per run",
                },
            },
            "required": ["subreddits"],
        }

    def get_compliance_notes(self) -> str:
        return (
            "Reddit connector uses the official Reddit API via PRAW. "
            "Free-tier credentials provide 60 requests/minute. "
            "The connector is read-only and never posts to Reddit. "
            "Requires a Reddit developer app: https://www.reddit.com/prefs/apps"
        )
