"""
Channel Connectors — Mock + Real Adapter Implementations
Each connector has:
  - Mock mode (for development/demo)
  - Real adapter structure (for production with actual API keys)
  - Auth, rate limiting, retry logic, error handling
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .base import (
    AuthStatus, BaseSocialConnector, ConnectorRegistry,
    MetricsResult, PublishResult, RateLimitState,
)

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
#  INSTAGRAM CONNECTOR
# ═════════════════════════════════════════════════════════════════════════════

class InstagramConnector(BaseSocialConnector):
    channel_name = "instagram"

    PLATFORM_LIMITS = {
        "max_caption_length": 2200,
        "max_hashtags": 30,
        "max_carousel_slides": 10,
        "posts_per_day": 25,
        "api_calls_per_hour": 200,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rate_limit = RateLimitState(
            remaining=self.PLATFORM_LIMITS["api_calls_per_hour"],
            limit=self.PLATFORM_LIMITS["api_calls_per_hour"],
            window_seconds=3600,
        )
        self._mock = not self.access_token

    async def authenticate(self) -> AuthStatus:
        if self._mock:
            return AuthStatus(connected=True, account_name="@demo_brand",
                              account_id="ig_mock_123", scopes=["publish_media", "read_insights"])
        # Real: call Instagram Graph API /me
        # response = await httpx.AsyncClient().get(
        #     "https://graph.instagram.com/me",
        #     params={"fields": "id,username", "access_token": self.access_token}
        # )
        return AuthStatus(connected=True, account_name="@real_account",
                          account_id=self.account_id or "unknown")

    async def refresh_auth(self) -> AuthStatus:
        if self._mock:
            return await self.authenticate()
        # Real: POST https://graph.instagram.com/refresh_access_token
        return await self.authenticate()

    async def publish(self, content: dict) -> PublishResult:
        self._validate_content(content)
        if self._mock:
            return await self._mock_publish(content)
        return await self._rate_limited_call(self._real_publish, content)

    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        # Instagram API doesn't natively support scheduling; store and use our scheduler
        return PublishResult(
            success=True,
            external_id=f"ig_scheduled_{uuid.uuid4().hex[:12]}",
            raw_response={"scheduled_at": publish_at.isoformat(), "note": "Managed by internal scheduler"},
        )

    async def delete(self, external_id: str) -> bool:
        if self._mock:
            return True
        # Real: DELETE https://graph.instagram.com/{media-id}
        return True

    async def get_metrics(self, external_id: str) -> MetricsResult:
        if self._mock:
            return MetricsResult(success=True, metrics=self._generate_mock_metrics())
        # Real: GET https://graph.instagram.com/{media-id}/insights
        return MetricsResult(success=True, metrics={})

    async def get_account_metrics(self) -> MetricsResult:
        if self._mock:
            return MetricsResult(success=True, metrics={
                "followers": random.randint(1000, 50000),
                "following": random.randint(100, 2000),
                "media_count": random.randint(50, 500),
            })
        return MetricsResult(success=True, metrics={})

    def _validate_content(self, content: dict):
        caption = content.get("caption", "")
        if len(caption) > self.PLATFORM_LIMITS["max_caption_length"]:
            raise ValueError(f"Caption exceeds {self.PLATFORM_LIMITS['max_caption_length']} chars")
        hashtags = content.get("hashtags", [])
        if len(hashtags) > self.PLATFORM_LIMITS["max_hashtags"]:
            raise ValueError(f"Too many hashtags (max {self.PLATFORM_LIMITS['max_hashtags']})")

    async def _mock_publish(self, content: dict) -> PublishResult:
        await asyncio.sleep(0.3)
        return PublishResult(
            success=True,
            external_id=f"ig_{uuid.uuid4().hex[:12]}",
            url=f"https://instagram.com/p/{uuid.uuid4().hex[:10]}",
        )

    async def _real_publish(self, content: dict) -> PublishResult:
        # Step 1: Create media container
        # Step 2: Publish container
        # Real implementation would use Instagram Graph API
        return PublishResult(success=False, error="Real Instagram API not configured")

    def _generate_mock_metrics(self) -> dict:
        impressions = random.randint(500, 15000)
        reach = int(impressions * random.uniform(0.6, 0.9))
        return {
            "impressions": impressions, "reach": reach,
            "likes": random.randint(20, int(reach * 0.1)),
            "comments": random.randint(0, 50),
            "saves": random.randint(5, 100),
            "shares": random.randint(0, 30),
            "engagement_rate": round(random.uniform(1.5, 8.0), 2),
        }


ConnectorRegistry.register("instagram", InstagramConnector)


# ═════════════════════════════════════════════════════════════════════════════
#  TIKTOK CONNECTOR
# ═════════════════════════════════════════════════════════════════════════════

class TikTokConnector(BaseSocialConnector):
    channel_name = "tiktok"

    PLATFORM_LIMITS = {
        "max_caption_length": 2200,
        "max_hashtags": 100,
        "max_video_duration": 600,  # 10 min
        "api_calls_per_day": 1000,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rate_limit = RateLimitState(remaining=1000, limit=1000, window_seconds=86400)
        self._mock = not self.access_token

    async def authenticate(self) -> AuthStatus:
        if self._mock:
            return AuthStatus(connected=True, account_name="@demo_tiktok",
                              account_id="tt_mock_456", scopes=["video.publish", "video.list"])
        # Real: TikTok Content Posting API auth verification
        return AuthStatus(connected=True, account_id=self.account_id or "unknown")

    async def refresh_auth(self) -> AuthStatus:
        # Real: POST https://open.tiktokapis.com/v2/oauth/token/ with refresh_token
        return await self.authenticate()

    async def publish(self, content: dict) -> PublishResult:
        if self._mock:
            await asyncio.sleep(0.5)
            return PublishResult(
                success=True,
                external_id=f"tt_{uuid.uuid4().hex[:12]}",
                url=f"https://tiktok.com/@demo/video/{random.randint(7000000000, 7999999999)}",
            )
        return await self._rate_limited_call(self._real_publish, content)

    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        return PublishResult(
            success=True,
            external_id=f"tt_scheduled_{uuid.uuid4().hex[:12]}",
            raw_response={"scheduled_at": publish_at.isoformat()},
        )

    async def delete(self, external_id: str) -> bool:
        return True

    async def get_metrics(self, external_id: str) -> MetricsResult:
        if self._mock:
            views = random.randint(1000, 500000)
            return MetricsResult(success=True, metrics={
                "views": views, "likes": int(views * random.uniform(0.03, 0.15)),
                "comments": random.randint(5, 500),
                "shares": random.randint(0, 200),
                "avg_watch_time": round(random.uniform(3.0, 45.0), 1),
                "completion_rate": round(random.uniform(0.15, 0.75), 3),
            })
        return MetricsResult(success=True, metrics={})

    async def get_account_metrics(self) -> MetricsResult:
        return MetricsResult(success=True, metrics={"followers": random.randint(500, 100000)})

    async def _real_publish(self, content: dict) -> PublishResult:
        return PublishResult(success=False, error="Real TikTok API not configured")


ConnectorRegistry.register("tiktok", TikTokConnector)


# ═════════════════════════════════════════════════════════════════════════════
#  TWITTER / X CONNECTOR
# ═════════════════════════════════════════════════════════════════════════════

class TwitterConnector(BaseSocialConnector):
    channel_name = "twitter"

    PLATFORM_LIMITS = {
        "max_tweet_length": 280,
        "max_thread_tweets": 25,
        "tweets_per_day": 2400,
        "api_calls_per_15min": 300,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rate_limit = RateLimitState(remaining=300, limit=300, window_seconds=900)
        self._mock = not self.access_token

    async def authenticate(self) -> AuthStatus:
        if self._mock:
            return AuthStatus(connected=True, account_name="@demo_brand",
                              account_id="tw_mock_789", scopes=["tweet.read", "tweet.write"])
        return AuthStatus(connected=True, account_id=self.account_id or "unknown")

    async def refresh_auth(self) -> AuthStatus:
        return await self.authenticate()

    async def publish(self, content: dict) -> PublishResult:
        """Publish a tweet or thread."""
        if self._mock:
            await asyncio.sleep(0.2)
            is_thread = isinstance(content.get("thread"), list)
            tweet_id = f"tw_{uuid.uuid4().hex[:12]}"
            return PublishResult(
                success=True, external_id=tweet_id,
                url=f"https://x.com/demo_brand/status/{random.randint(10**17, 10**18)}",
                raw_response={"is_thread": is_thread, "tweet_count": len(content.get("thread", [1]))},
            )
        return await self._rate_limited_call(self._real_publish, content)

    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        return PublishResult(
            success=True,
            external_id=f"tw_scheduled_{uuid.uuid4().hex[:12]}",
            raw_response={"scheduled_at": publish_at.isoformat()},
        )

    async def delete(self, external_id: str) -> bool:
        return True

    async def get_metrics(self, external_id: str) -> MetricsResult:
        if self._mock:
            impressions = random.randint(200, 50000)
            return MetricsResult(success=True, metrics={
                "impressions": impressions,
                "likes": random.randint(0, int(impressions * 0.05)),
                "retweets": random.randint(0, int(impressions * 0.02)),
                "replies": random.randint(0, 30),
                "bookmark": random.randint(0, 20),
                "url_clicks": random.randint(0, int(impressions * 0.03)),
                "profile_visits": random.randint(0, 50),
            })
        return MetricsResult(success=True, metrics={})

    async def get_account_metrics(self) -> MetricsResult:
        return MetricsResult(success=True, metrics={"followers": random.randint(500, 25000)})

    async def _real_publish(self, content: dict) -> PublishResult:
        # Real: POST https://api.twitter.com/2/tweets (OAuth 2.0)
        return PublishResult(success=False, error="Real Twitter API not configured")


ConnectorRegistry.register("twitter", TwitterConnector)


# ═════════════════════════════════════════════════════════════════════════════
#  LINKEDIN CONNECTOR
# ═════════════════════════════════════════════════════════════════════════════

class LinkedInConnector(BaseSocialConnector):
    channel_name = "linkedin"

    PLATFORM_LIMITS = {
        "max_post_length": 3000,
        "max_article_length": 125000,
        "api_calls_per_day": 1000,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rate_limit = RateLimitState(remaining=1000, limit=1000, window_seconds=86400)
        self._mock = not self.access_token

    async def authenticate(self) -> AuthStatus:
        if self._mock:
            return AuthStatus(connected=True, account_name="Demo Corp",
                              account_id="li_mock_abc", scopes=["w_member_social", "r_liteprofile"])
        return AuthStatus(connected=True, account_id=self.account_id or "unknown")

    async def refresh_auth(self) -> AuthStatus:
        return await self.authenticate()

    async def publish(self, content: dict) -> PublishResult:
        if self._mock:
            await asyncio.sleep(0.3)
            return PublishResult(
                success=True,
                external_id=f"li_{uuid.uuid4().hex[:12]}",
                url=f"https://linkedin.com/feed/update/urn:li:share:{random.randint(7000000000, 7999999999)}",
            )
        return await self._rate_limited_call(self._real_publish, content)

    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        return PublishResult(
            success=True,
            external_id=f"li_scheduled_{uuid.uuid4().hex[:12]}",
            raw_response={"scheduled_at": publish_at.isoformat()},
        )

    async def delete(self, external_id: str) -> bool:
        return True

    async def get_metrics(self, external_id: str) -> MetricsResult:
        if self._mock:
            impressions = random.randint(300, 20000)
            return MetricsResult(success=True, metrics={
                "impressions": impressions,
                "likes": random.randint(5, int(impressions * 0.08)),
                "comments": random.randint(0, 30),
                "shares": random.randint(0, 15),
                "clicks": random.randint(0, int(impressions * 0.04)),
                "engagement_rate": round(random.uniform(2.0, 10.0), 2),
            })
        return MetricsResult(success=True, metrics={})

    async def get_account_metrics(self) -> MetricsResult:
        return MetricsResult(success=True, metrics={"followers": random.randint(500, 15000)})

    async def _real_publish(self, content: dict) -> PublishResult:
        # Real: POST https://api.linkedin.com/v2/ugcPosts (OAuth 2.0)
        return PublishResult(success=False, error="Real LinkedIn API not configured")


ConnectorRegistry.register("linkedin", LinkedInConnector)


# ═════════════════════════════════════════════════════════════════════════════
#  META ADS CONNECTOR
# ═════════════════════════════════════════════════════════════════════════════

class MetaAdsConnector(BaseSocialConnector):
    channel_name = "meta_ads"

    PLATFORM_LIMITS = {
        "max_primary_text": 125,  # recommended
        "max_headline": 40,
        "max_description": 125,
        "api_calls_per_hour": 200,
    }

    def __init__(self, ad_account_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.ad_account_id = ad_account_id
        self._rate_limit = RateLimitState(remaining=200, limit=200, window_seconds=3600)
        self._mock = not self.access_token

    async def authenticate(self) -> AuthStatus:
        if self._mock:
            return AuthStatus(connected=True, account_name="Demo Ad Account",
                              account_id="act_mock_999", scopes=["ads_management", "ads_read"])
        return AuthStatus(connected=True, account_id=self.ad_account_id or "unknown")

    async def refresh_auth(self) -> AuthStatus:
        return await self.authenticate()

    async def publish(self, content: dict) -> PublishResult:
        """Create and launch an ad (in mock, just simulates)."""
        if self._mock:
            await asyncio.sleep(0.4)
            return PublishResult(
                success=True,
                external_id=f"meta_ad_{uuid.uuid4().hex[:12]}",
                raw_response={
                    "campaign_id": f"camp_{uuid.uuid4().hex[:8]}",
                    "adset_id": f"adset_{uuid.uuid4().hex[:8]}",
                    "ad_id": f"ad_{uuid.uuid4().hex[:8]}",
                    "status": "PAUSED",  # Always start paused for safety
                },
            )
        return await self._rate_limited_call(self._real_publish, content)

    async def schedule(self, content: dict, publish_at: datetime) -> PublishResult:
        return PublishResult(
            success=True,
            external_id=f"meta_scheduled_{uuid.uuid4().hex[:12]}",
            raw_response={"scheduled_at": publish_at.isoformat(), "start_paused": True},
        )

    async def delete(self, external_id: str) -> bool:
        return True

    async def get_metrics(self, external_id: str) -> MetricsResult:
        if self._mock:
            spend = round(random.uniform(5.0, 500.0), 2)
            impressions = random.randint(500, 100000)
            clicks = random.randint(10, int(impressions * 0.05))
            conversions = random.randint(0, int(clicks * 0.15))
            return MetricsResult(success=True, metrics={
                "impressions": impressions, "reach": int(impressions * 0.85),
                "clicks": clicks, "ctr": round(clicks / max(impressions, 1) * 100, 2),
                "spend": spend, "cpc": round(spend / max(clicks, 1), 2),
                "conversions": conversions,
                "cost_per_conversion": round(spend / max(conversions, 1), 2),
                "roas": round(random.uniform(0.5, 8.0), 2),
            })
        return MetricsResult(success=True, metrics={})

    async def get_account_metrics(self) -> MetricsResult:
        return MetricsResult(success=True, metrics={"account_status": "active"})

    async def _real_publish(self, content: dict) -> PublishResult:
        # Real: Meta Marketing API campaign/adset/ad creation flow
        return PublishResult(success=False, error="Real Meta Ads API not configured")


ConnectorRegistry.register("meta_ads", MetaAdsConnector)
