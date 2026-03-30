"""
Instagram Publisher — Instagram Graph API

Required OAuth scopes: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
Required credential fields: access_token, instagram_account_id (or page_id to resolve)

Two-step publish flow for single images/videos:
  1. POST /v20.0/{ig-user-id}/media        → returns creation_id
  2. POST /v20.0/{ig-user-id}/media_publish → publishes it

Caption-only / text posts are not supported by Instagram Graph API.
All posts require at least one media item or a reel.

Supported content types:
  - IMAGE: JPEG/PNG image URL (must be publicly accessible)
  - REELS: MP4 video URL (must be publicly accessible)
  - CAROUSEL: up to 10 images/videos

Content window: published posts appear within ~30 seconds of publish call.
Rate limit: 50 API calls / hour per Instagram account, 25 posts/day

Reference: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.services.publishers.base import PublisherService, PublishResult, PublisherStatus

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"
REQUIRED_SCOPES = {"instagram_basic", "instagram_content_publish"}


class InstagramPublisher(PublisherService):
    channel = "instagram"

    def _get_creds(self) -> Optional[dict]:
        cred = self._load_credentials()
        if not cred:
            return None
        return cred

    async def check_status(self) -> PublisherStatus:
        """Validate by calling /me?fields=id on the Graph API."""
        cred = self._get_creds()
        if not cred:
            return PublisherStatus.NO_CREDENTIALS
        token = cred.get("access_token")
        if not token:
            return PublisherStatus.NO_CREDENTIALS

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{GRAPH_API_BASE}/me",
                    params={"access_token": token, "fields": "id,name"},
                )
                if resp.status_code == 200:
                    return PublisherStatus.READY
                if resp.status_code == 401:
                    return PublisherStatus.INVALID_CREDENTIALS
                if resp.status_code == 403:
                    return PublisherStatus.MISSING_SCOPES
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
        Instagram does not support text-only posts via the Graph API.
        This method returns an informative failure so the content queue
        can be updated to include a media attachment before retrying.
        """
        result = PublishResult.fail(
            "Instagram does not support text-only posts. "
            "Attach an image or reel to publish on Instagram. "
            "The caption has been saved — add media and retry."
        )
        self._audit("text_post_unsupported", result)
        return result

    async def publish_image_post(
        self,
        caption: str,
        image_url: str,
        ig_user_id: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish a single image post to Instagram.
        image_url must be a publicly accessible HTTPS URL.
        """
        cred = self._get_creds()
        if not cred:
            result = PublishResult.fail("No Instagram credentials. Connect your account in Connections.")
            self._audit("image_post", result)
            return result

        token = cred.get("access_token")
        account_id = ig_user_id or cred.get("instagram_account_id") or cred.get("extra", {}).get("instagram_account_id")

        if not account_id:
            result = PublishResult.fail(
                "Instagram account ID not found. Re-connect your Instagram account in Connections."
            )
            self._audit("image_post", result)
            return result

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Create media container
                container_resp = await client.post(
                    f"{GRAPH_API_BASE}/{account_id}/media",
                    params={
                        "image_url": image_url,
                        "caption": caption[:2200],  # IG caption limit
                        "access_token": token,
                    },
                )
                if container_resp.status_code != 200:
                    err = container_resp.json().get("error", {}).get("message", container_resp.text[:200])
                    result = PublishResult.fail(f"Instagram media container error: {err}")
                    self._audit("image_post", result)
                    return result

                creation_id = container_resp.json().get("id")
                if not creation_id:
                    result = PublishResult.fail("Instagram media container returned no ID")
                    self._audit("image_post", result)
                    return result

                # Step 2: Publish the container
                publish_resp = await client.post(
                    f"{GRAPH_API_BASE}/{account_id}/media_publish",
                    params={"creation_id": creation_id, "access_token": token},
                )
                if publish_resp.status_code == 200:
                    post_id = publish_resp.json().get("id", "")
                    post_url = f"https://www.instagram.com/p/{post_id}/" if post_id else None
                    result = PublishResult.ok(post_id=post_id, post_url=post_url, raw=publish_resp.json())
                    self._audit("image_post", result)
                    logger.info("[instagram] image post published: id=%s", post_id)
                    return result

                err = publish_resp.json().get("error", {}).get("message", publish_resp.text[:200])
                result = PublishResult.fail(f"Instagram publish error: {err}")
                self._audit("image_post", result)
                return result

        except httpx.TimeoutException:
            result = PublishResult.fail("Instagram API request timed out")
            self._audit("image_post", result)
            return result
        except httpx.RequestError as e:
            result = PublishResult.fail(f"Instagram API network error: {e}")
            self._audit("image_post", result)
            return result

    async def get_post_metrics(self, post_id: str) -> Optional[dict]:
        """Fetch Instagram media insights."""
        cred = self._get_creds()
        if not cred:
            return None
        token = cred.get("access_token")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{GRAPH_API_BASE}/{post_id}/insights",
                    params={
                        "metric": "impressions,reach,engagement,saved,profile_visits",
                        "access_token": token,
                    },
                )
                if resp.status_code == 200:
                    data_list = resp.json().get("data", [])
                    metrics = {item["name"]: item.get("values", [{}])[0].get("value", 0) for item in data_list}
                    return metrics
        except Exception as e:
            logger.debug("[instagram] metrics fetch failed for %s: %s", post_id, e)
        return None
