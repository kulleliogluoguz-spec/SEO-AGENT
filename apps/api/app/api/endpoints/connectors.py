"""
Connections Health & Capability API.

GET  /connectors/status                  — all connector statuses (legacy compat)
GET  /connectors/social/health           — real-time social channel health
GET  /connectors/social/health/{channel} — single channel health check
GET  /connectors/capabilities            — what each connection enables
GET  /connectors/summary                 — compact summary for overview
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

SOCIAL_CHANNELS = ["x", "instagram", "tiktok"]

CHANNEL_CAPABILITIES = {
    "x": {
        "label": "X / Twitter",
        "emoji": "𝕏",
        "supports_text_posts": True,
        "supports_media_posts": True,
        "supports_threads": True,
        "supports_ads": False,
        "required_scopes": ["tweet.write", "tweet.read", "users.read"],
        "post_limit_note": "500 tweets/month (Basic tier)",
        "setup_url": "/dashboard/connectors",
    },
    "instagram": {
        "label": "Instagram",
        "emoji": "📸",
        "supports_text_posts": False,
        "supports_media_posts": True,
        "supports_threads": False,
        "supports_ads": False,
        "required_scopes": ["instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement"],
        "post_limit_note": "25 posts/day",
        "setup_url": "/dashboard/connectors",
        "note": "Image or Reel required — text-only not supported.",
    },
    "tiktok": {
        "label": "TikTok",
        "emoji": "🎵",
        "supports_text_posts": False,
        "supports_media_posts": True,
        "supports_threads": False,
        "supports_ads": False,
        "required_scopes": ["video.upload", "video.publish"],
        "post_limit_note": "Based on account tier",
        "setup_url": "/dashboard/connectors",
        "note": "Video content required. No text-only posting.",
    },
}

STATUS_MESSAGES = {
    "ready": "Connected and ready",
    "no_credentials": "Not connected — add credentials in Connections",
    "invalid_credentials": "Token expired or invalid — reconnect",
    "missing_scopes": "Missing required permissions — reconnect with full access",
    "rate_limited": "Rate limited — retry in a few minutes",
    "unavailable": "Platform API unreachable",
    "not_implemented": "Not yet available",
    "not_configured": "Not configured",
}


async def _check_social_channel(channel: str, user_id: str) -> dict:
    """Check real health of a social channel by calling its publisher."""
    caps = CHANNEL_CAPABILITIES.get(channel, {})
    try:
        from app.services.publishers import get_publisher
        from app.services.publishers.base import PublisherStatus
        publisher = get_publisher(channel, user_id)
        status = await asyncio.wait_for(publisher.check_status(), timeout=3.0)
        status_val = status.value
        ready = status == PublisherStatus.READY
    except asyncio.TimeoutError:
        logger.debug("connector health check timed out for %s", channel)
        status_val = "unavailable"
        ready = False
    except ValueError:
        status_val = "not_implemented"
        ready = False
    except Exception as e:
        logger.debug("connector health check failed for %s: %s", channel, e)
        status_val = "unavailable"
        ready = False

    return {
        "channel": channel,
        "label": caps.get("label", channel.title()),
        "emoji": caps.get("emoji", "🔗"),
        "status": status_val,
        "ready": ready,
        "message": STATUS_MESSAGES.get(status_val, status_val),
        "publish_enabled": ready and (
            caps.get("supports_text_posts", False) or caps.get("supports_media_posts", False)
        ),
        "capabilities": {
            "text_posts": caps.get("supports_text_posts", False),
            "media_posts": caps.get("supports_media_posts", False),
            "threads": caps.get("supports_threads", False),
        },
        "required_scopes": caps.get("required_scopes", []),
        "post_limit_note": caps.get("post_limit_note", ""),
        "note": caps.get("note"),
        "setup_url": caps.get("setup_url", "/dashboard/connectors"),
    }


def _check_data_source(source: str, user_id: str) -> dict:
    try:
        from app.core.store.credential_store import get_credential
        cred = get_credential(user_id, source)
        if cred:
            return {"source": source, "status": "configured", "ready": True}
    except Exception:
        pass
    return {"source": source, "status": "not_configured", "ready": False}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def connectors_status(current_user=Depends(get_current_user)):
    """Legacy compatibility. Returns combined social + data source status."""
    social_results = await asyncio.gather(
        *[_check_social_channel(ch, str(current_user.id)) for ch in SOCIAL_CHANNELS],
        return_exceptions=True,
    )
    valid_social = [r for r in social_results if isinstance(r, dict)]

    data_sources = ["ga4", "search_console", "slack", "cms"]
    data_results = [_check_data_source(src, str(current_user.id)) for src in data_sources]

    return {
        "social": valid_social,
        "data_sources": data_results,
        "connectors": [
            {"name": r["source"], "status": r["status"]} for r in data_results
        ],
    }


@router.get("/social/health")
async def social_health_all(current_user=Depends(get_current_user)):
    """Real-time health check for all social publishing channels in parallel."""
    results = await asyncio.gather(
        *[_check_social_channel(ch, str(current_user.id)) for ch in SOCIAL_CHANNELS],
        return_exceptions=True,
    )
    valid = [r for r in results if isinstance(r, dict)]
    ready_count = sum(1 for r in valid if r.get("ready"))

    return {
        "channels": valid,
        "ready_count": ready_count,
        "total_channels": len(SOCIAL_CHANNELS),
        "any_ready": ready_count > 0,
    }


@router.get("/social/health/{channel}")
async def social_health_one(channel: str, current_user=Depends(get_current_user)):
    """Health check for a single social channel."""
    normalized = "x" if channel == "twitter" else channel
    if normalized not in CHANNEL_CAPABILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown channel: {channel}")
    return await _check_social_channel(normalized, str(current_user.id))


@router.get("/capabilities")
async def connector_capabilities(current_user=Depends(get_current_user)):
    """
    Return what each connection enables in the platform.
    Used by setup wizard, content creation, and campaign flows.
    """
    social_results = await asyncio.gather(
        *[_check_social_channel(ch, str(current_user.id)) for ch in SOCIAL_CHANNELS],
        return_exceptions=True,
    )
    valid = [r for r in social_results if isinstance(r, dict)]
    publish_channels = [r["channel"] for r in valid if r.get("ready")]

    not_connected = [r["channel"] for r in valid if not r.get("ready")]
    priority = ["x", "instagram", "tiktok"]
    next_recommended = next((ch for ch in priority if ch in not_connected), None)

    blocked: list[str] = []
    if not any(r.get("ready") and r["capabilities"].get("text_posts") for r in valid):
        blocked.append("text_post_publishing")
    if not any(r.get("ready") and r["capabilities"].get("media_posts") for r in valid):
        blocked.append("media_post_publishing")

    return {
        "publish_channels": publish_channels,
        "content_ready": len(publish_channels) > 0,
        "ads_ready": False,
        "analytics_ready": _check_data_source("ga4", str(current_user.id))["ready"],
        "trend_data_ready": True,
        "channels": {r["channel"]: r for r in valid},
        "blocked_features": blocked,
        "next_connection_recommended": next_recommended,
    }


class SaveCredentialRequest(BaseModel):
    connector_key: str
    fields: dict


@router.post("/credentials")
async def save_connector_credentials(
    body: SaveCredentialRequest,
    current_user=Depends(get_current_user),
):
    """
    Save data connector credentials (RSS, Reddit, GA4, GSC, CMS, Slack, etc).
    Tokens are base64-encoded at rest in storage/credentials.json.
    """
    from app.core.store.credential_store import store_credential

    # Extract the primary auth field — use access_token, api_key, webhook_url, or client_secret
    primary_token = (
        body.fields.get("api_key")
        or body.fields.get("webhook_url")
        or body.fields.get("client_secret")
        or body.fields.get("credentials")
        or body.fields.get("access_token")
        or "configured"
    )

    # Store extra fields without the primary token
    extra = {k: v for k, v in body.fields.items() if k not in ("api_key", "webhook_url", "client_secret", "credentials", "access_token")}

    record = store_credential(
        user_id=str(current_user.id),
        platform=body.connector_key,
        access_token=primary_token,
        extra=extra,
    )
    return {"saved": True, "connector": body.connector_key, "record": record}


@router.get("/summary")
async def connectors_summary(current_user=Depends(get_current_user)):
    """Compact summary for the overview dashboard."""
    try:
        results = await asyncio.gather(
            *[_check_social_channel(ch, str(current_user.id)) for ch in SOCIAL_CHANNELS],
            return_exceptions=True,
        )
        valid = [r for r in results if isinstance(r, dict)]
        ready_channels = [r["channel"] for r in valid if r.get("ready")]
    except Exception:
        ready_channels = []

    return {
        "ready_channels": ready_channels,
        "ready_count": len(ready_channels),
        "total_social_channels": len(SOCIAL_CHANNELS),
        "publish_ready": len(ready_channels) > 0,
        "needs_connection": len(ready_channels) == 0,
    }
