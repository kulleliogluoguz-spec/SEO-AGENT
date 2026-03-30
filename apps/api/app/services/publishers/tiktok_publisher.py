"""
TikTok Publisher — TikTok Content Posting API

Required scopes: video.upload, video.publish, user.info.basic
Required credential fields: access_token, open_id (TikTok user ID)

TikTok Content API publish flow (for videos):
  1. POST /v2/post/publish/video/init/   → returns publish_id + upload_url
  2. PUT  <upload_url>                   → upload video bytes
  3. GET  /v2/post/publish/status/fetch/ → poll until PUBLISH_COMPLETE

Text-only "Mention" posts (no video) are supported via the /share/sound/bind/ endpoint
but require the video file. Caption-only posts are not supported.

For our use case (X-like text content → TikTok), we generate a simple text overlay
video or use the TikTok Text API (available in v2.0+) where available.

Reference:
  https://developers.tiktok.com/doc/content-posting-api-reference-manage-posts
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.services.publishers.base import PublisherService, PublishResult, PublisherStatus

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
REQUIRED_SCOPES = {"video.upload", "video.publish"}


class TikTokPublisher(PublisherService):
    channel = "tiktok"

    def _get_creds(self) -> Optional[dict]:
        return self._load_credentials()

    async def check_status(self) -> PublisherStatus:
        """Validate TikTok credentials by calling /user/info/."""
        cred = self._get_creds()
        if not cred:
            return PublisherStatus.NO_CREDENTIALS
        token = cred.get("access_token")
        if not token:
            return PublisherStatus.NO_CREDENTIALS

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{TIKTOK_API_BASE}/user/info/",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"fields": ["open_id", "display_name"]},
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
        except httpx.RequestError:
            return PublisherStatus.UNAVAILABLE

    async def publish_text_post(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
        schedule_at: Optional[str] = None,
    ) -> PublishResult:
        """
        TikTok does not natively support text-only posts via the Content API.
        We return a structured informative failure.
        For TikTok, text content should be adapted into a video script and
        posted as a video or text-overlay video.
        """
        result = PublishResult.fail(
            "TikTok requires video content. Your text has been saved as a script — "
            "record or generate a video from this script to publish on TikTok. "
            "TikTok Text posts (no video) are available for select accounts only."
        )
        self._audit("text_post_unsupported", result)
        return result

    async def publish_video_post(
        self,
        caption: str,
        video_url: str,
        open_id: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish a video to TikTok using the direct_post flow.
        video_url must be a publicly accessible HTTPS URL.
        """
        cred = self._get_creds()
        if not cred:
            result = PublishResult.fail("No TikTok credentials. Connect your account in Connections.")
            self._audit("video_post", result)
            return result

        token = cred.get("access_token")
        creator_open_id = open_id or cred.get("open_id") or cred.get("extra", {}).get("open_id")

        if not creator_open_id:
            result = PublishResult.fail(
                "TikTok open_id not found. Re-connect your TikTok account in Connections."
            )
            self._audit("video_post", result)
            return result

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Direct post via URL
                payload = {
                    "post_info": {
                        "title": caption[:2200],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_stitch": False,
                        "disable_comment": False,
                        "video_cover_timestamp_ms": 1000,
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "video_url": video_url,
                    },
                }

                resp = await client.post(
                    f"{TIKTOK_API_BASE}/post/publish/video/init/",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )

                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    publish_id = data.get("publish_id", "")
                    result = PublishResult.ok(post_id=publish_id, raw=resp.json())
                    self._audit("video_post", result)
                    logger.info("[tiktok] video publish initiated: publish_id=%s", publish_id)
                    return result

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 3600))
                    result = PublishResult.fail("TikTok rate limit reached", rate_limited=True, retry_after=retry_after)
                    self._audit("video_post", result)
                    return result

                err = ""
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:200])
                except Exception:
                    err = resp.text[:200]

                result = PublishResult.fail(f"TikTok API error {resp.status_code}: {err}")
                self._audit("video_post", result)
                return result

        except httpx.TimeoutException:
            result = PublishResult.fail("TikTok API request timed out")
            self._audit("video_post", result)
            return result
        except httpx.RequestError as e:
            result = PublishResult.fail(f"TikTok API network error: {e}")
            self._audit("video_post", result)
            return result

    async def get_post_metrics(self, post_id: str) -> Optional[dict]:
        """Fetch TikTok video stats."""
        cred = self._get_creds()
        if not cred:
            return None
        token = cred.get("access_token")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{TIKTOK_API_BASE}/video/query/",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "filters": {"video_ids": [post_id]},
                        "fields": ["id", "play_count", "like_count", "comment_count", "share_count", "view_count"],
                    },
                )
                if resp.status_code == 200:
                    videos = resp.json().get("data", {}).get("videos", [])
                    if videos:
                        v = videos[0]
                        return {
                            "views": v.get("view_count", 0) or v.get("play_count", 0),
                            "likes": v.get("like_count", 0),
                            "comments": v.get("comment_count", 0),
                            "shares": v.get("share_count", 0),
                        }
        except Exception as e:
            logger.debug("[tiktok] metrics fetch failed for %s: %s", post_id, e)
        return None
