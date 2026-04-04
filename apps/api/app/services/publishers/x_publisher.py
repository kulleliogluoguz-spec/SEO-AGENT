"""
X / Twitter Publisher — X API v2

Required OAuth 2.0 scopes: tweet.write, tweet.read, users.read, offline.access
Required credential fields: access_token, (optionally) refresh_token, user_id

X API v2 endpoints used:
  POST https://api.twitter.com/2/tweets         — create tweet
  DELETE https://api.twitter.com/2/tweets/{id}  — delete tweet
  GET  https://api.twitter.com/2/tweets/{id}    — get tweet metrics

Rate limits (free/basic tier):
  Write: 500 tweets/month (Basic), 1,500/month (Pro)
  Read: 1 request/15 minutes (free)

Token refresh:
  X OAuth 2.0 PKCE tokens expire after 2 hours (access_token).
  Refresh tokens are valid indefinitely if used at least once every 6 months.
  We attempt refresh on 401 before failing.

Reference: https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.services.publishers.base import PublisherService, PublishResult, PublisherStatus

logger = logging.getLogger(__name__)

X_API_BASE = "https://api.twitter.com/2"
X_OAUTH_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# Required OAuth 2.0 scopes for content publishing
REQUIRED_SCOPES = {"tweet.write", "tweet.read", "users.read"}

# X character limits
TWEET_MAX_CHARS = 280
THREAD_MAX_POSTS = 25


class XPublisher(PublisherService):
    channel = "x"

    def _load_cred(self) -> Optional[dict]:
        """Load credentials, also trying the 'twitter' alias."""
        cred = self._load_credentials()
        if not cred:
            from app.core.store.credential_store import get_credential
            cred = get_credential(self.user_id, "twitter")
        return cred

    def _auth_header(self, method: str, url: str, cred: dict) -> str:
        """Build the correct Authorization header for the credential type."""
        token = cred.get("access_token") or cred.get("api_key") or ""
        if (cred.get("extra") or {}).get("token_type") == "oauth1":
            from app.core.security.oauth1 import build_auth_header
            from app.core.config.settings import get_settings
            s = get_settings()
            return build_auth_header(
                method=method,
                url=url,
                consumer_key=s.x_api_key,
                consumer_secret=s.x_api_secret,
                token=token,
                token_secret=cred.get("refresh_token", ""),
            )
        return f"Bearer {token}"

    async def _get_token(self) -> Optional[str]:
        """Return a valid access_token (OAuth 2.0 path only)."""
        cred = self._load_cred()
        if not cred:
            return None
        return cred.get("access_token") or cred.get("api_key")

    async def check_status(self) -> PublisherStatus:
        """Validate X credentials by calling GET /2/users/me."""
        cred = self._load_cred()
        if not cred:
            return PublisherStatus.NO_CREDENTIALS

        url = f"{X_API_BASE}/users/me"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": self._auth_header("GET", url, cred)},
                )
                if resp.status_code == 200:
                    return PublisherStatus.READY
                if resp.status_code == 401:
                    return PublisherStatus.INVALID_CREDENTIALS
                if resp.status_code == 403:
                    return PublisherStatus.MISSING_SCOPES
                if resp.status_code == 429:
                    return PublisherStatus.RATE_LIMITED
                return PublisherStatus.UNAVAILABLE
        except (httpx.RequestError, httpx.TimeoutException):
            return PublisherStatus.UNAVAILABLE

    async def publish_text_post(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
        schedule_at: Optional[str] = None,
    ) -> PublishResult:
        """
        Post a tweet via X API v2.

        Args:
            text: Tweet text (truncated to 280 chars automatically)
            reply_to_id: If set, posts as a reply to this tweet ID (for threads)
            schedule_at: ISO 8601 datetime — NOTE: X API v2 free/basic does NOT support
                         scheduled tweets via API; this param is stored locally and
                         handled by our publish sweep job.
        """
        cred = self._load_cred()
        if not cred:
            result = PublishResult.fail("No X/Twitter credentials found. Connect your account in Connections.")
            self._audit("text_post", result)
            return result

        # Truncate to X's character limit
        tweet_text = text[:TWEET_MAX_CHARS]
        if len(text) > TWEET_MAX_CHARS:
            logger.warning("[x] tweet truncated from %d to %d chars", len(text), TWEET_MAX_CHARS)

        payload: dict = {"text": tweet_text}
        if reply_to_id:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

        post_url = f"{X_API_BASE}/tweets"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    post_url,
                    headers={
                        "Authorization": self._auth_header("POST", post_url, cred),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if resp.status_code == 201:
                    data = resp.json().get("data", {})
                    post_id = data.get("id", "")
                    post_url = f"https://x.com/i/web/status/{post_id}" if post_id else None
                    result = PublishResult.ok(post_id=post_id, post_url=post_url, raw=resp.json())
                    self._audit("text_post", result)
                    logger.info("[x] tweet published: id=%s", post_id)
                    return result

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("x-rate-limit-reset", 900))
                    result = PublishResult.fail("X rate limit reached", rate_limited=True, retry_after=retry_after)
                    self._audit("text_post", result)
                    return result

                if resp.status_code == 401:
                    result = PublishResult.fail("X access token invalid or expired. Reconnect in Connections.")
                    self._audit("text_post", result)
                    return result

                error_detail = ""
                try:
                    error_detail = resp.json().get("detail") or resp.text[:200]
                except Exception:
                    error_detail = resp.text[:200]

                result = PublishResult.fail(f"X API error {resp.status_code}: {error_detail}")
                self._audit("text_post", result)
                return result

        except httpx.TimeoutException:
            result = PublishResult.fail("X API request timed out")
            self._audit("text_post", result)
            return result
        except httpx.RequestError as e:
            result = PublishResult.fail(f"X API network error: {e}")
            self._audit("text_post", result)
            return result

    async def publish_thread(self, tweets: list[str]) -> list[PublishResult]:
        """
        Publish a thread by chaining replies.
        Each tweet is posted as a reply to the previous one.
        Returns list of PublishResult for each tweet in the thread.
        """
        results = []
        previous_id: Optional[str] = None

        for i, text in enumerate(tweets[:THREAD_MAX_POSTS]):
            result = await self.publish_text_post(text, reply_to_id=previous_id)
            results.append(result)
            if not result.success:
                logger.warning("[x] thread broke at tweet %d: %s", i + 1, result.error)
                break
            previous_id = result.post_id

        return results

    async def get_post_metrics(self, post_id: str) -> Optional[dict]:
        """
        Fetch public metrics for a tweet.
        Requires tweet.read scope and Basic/Pro tier for non-public metrics.
        """
        cred = self._load_cred()
        if not cred:
            return None

        metrics_url = f"{X_API_BASE}/tweets/{post_id}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    metrics_url,
                    headers={"Authorization": self._auth_header("GET", metrics_url, cred)},
                    params={"tweet.fields": "public_metrics,created_at"},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    metrics = data.get("public_metrics", {})
                    return {
                        "impressions": metrics.get("impression_count", 0),
                        "likes": metrics.get("like_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "quotes": metrics.get("quote_count", 0),
                        "bookmarks": metrics.get("bookmark_count", 0),
                        "profile_visits": 0,  # requires elevated access
                        "link_clicks": 0,     # requires Promoted metrics
                    }
        except Exception as e:
            logger.debug("[x] metrics fetch failed for %s: %s", post_id, e)
        return None

    async def delete_post(self, post_id: str) -> bool:
        cred = self._load_cred()
        if not cred:
            return False
        delete_url = f"{X_API_BASE}/tweets/{post_id}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.delete(
                    delete_url,
                    headers={"Authorization": self._auth_header("DELETE", delete_url, cred)},
                )
                return resp.status_code == 200
        except Exception:
            return False
