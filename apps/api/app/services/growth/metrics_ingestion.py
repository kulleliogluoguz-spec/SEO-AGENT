"""
Metrics Ingestion Service — autonomous background data collection.

Runs two loops (called from main.py lifespan):

  1. _post_metrics_loop() — every 60 minutes
     Scans all published posts from the last 7 days.
     For each post with a platform_post_id, calls the publisher's
     get_post_metrics() and stores the result in content_metrics_store.

  2. _follower_count_loop() — every 6 hours
     For each user who has a connected X or Instagram account,
     fetches the current follower count and appends a snapshot to
     growth_metrics_store (timeseries).

These loops are passive observers — they never publish or modify content.
All failures are swallowed so they never crash the main app.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from app.core.store.content_queue_store import get_published_posts_for_metrics
from app.core.store.content_metrics_store import record_post_metrics, get_post_metrics
from app.core.store.growth_metrics_store import append_follower_snapshot
from app.core.store.credential_store import get_credential
from app.services.publishers import get_publisher

logger = logging.getLogger(__name__)

# ── X API constants ───────────────────────────────────────────────────────────

X_API_BASE = "https://api.twitter.com/2"
GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


# ── Follower fetching ─────────────────────────────────────────────────────────

async def _fetch_x_follower_count(user_id: str) -> Optional[int]:
    """
    Fetch current follower count for the connected X account.
    Uses GET /2/users/me?user.fields=public_metrics
    Returns follower count or None if unavailable.
    """
    cred = get_credential(user_id, "x") or get_credential(user_id, "twitter")
    if not cred:
        return None
    token = cred.get("access_token") or cred.get("api_key")
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{X_API_BASE}/users/me",
                headers={"Authorization": f"Bearer {token}"},
                params={"user.fields": "public_metrics"},
            )
            if resp.status_code == 200:
                data = resp.json()
                metrics = data.get("data", {}).get("public_metrics", {})
                return metrics.get("followers_count")
            logger.debug("[metrics_ingestion] X follower fetch HTTP %s", resp.status_code)
            return None
    except Exception as e:
        logger.debug("[metrics_ingestion] X follower fetch error: %s", e)
        return None


async def _fetch_instagram_follower_count(user_id: str) -> Optional[int]:
    """
    Fetch current follower count for the connected Instagram Business account.
    Uses GET /{ig-user-id}?fields=followers_count
    """
    cred = get_credential(user_id, "meta") or get_credential(user_id, "instagram")
    if not cred:
        return None
    token = cred.get("access_token")
    if not token:
        return None

    # Resolve Instagram user ID
    account_id = (
        cred.get("instagram_account_id")
        or cred.get("extra", {}).get("instagram_account_id")
    )
    if not account_id:
        # Try to find it from linked accounts
        from app.core.store.credential_store import get_linked_accounts
        ig_accounts = get_linked_accounts(user_id, "instagram")
        if ig_accounts:
            account_id = ig_accounts[0].get("account_id")
    if not account_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{account_id}",
                params={
                    "fields": "followers_count,media_count",
                    "access_token": token,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("followers_count")
            logger.debug("[metrics_ingestion] IG follower fetch HTTP %s", resp.status_code)
            return None
    except Exception as e:
        logger.debug("[metrics_ingestion] IG follower fetch error: %s", e)
        return None


# ── Post metrics ingestion ────────────────────────────────────────────────────

async def _ingest_post_metrics_for_user(user_id: str) -> int:
    """
    Fetch and store metrics for all published posts (last 7 days) for a user.
    Returns the number of posts successfully updated.
    """
    updated = 0
    try:
        published = get_published_posts_for_metrics(user_id, days=7)
    except Exception as e:
        logger.debug("[metrics_ingestion] Could not load published posts for %s: %s", user_id, e)
        return 0

    for post in published:
        platform_post_id = post.get("platform_post_id")
        channel = post.get("channel", "x")
        if not platform_post_id:
            continue

        # Skip if metrics were fetched in the last 2 hours
        existing = get_post_metrics(post["id"], user_id)
        if existing:
            last_ts = existing.get("recorded_at", "")
            if last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts)
                    if datetime.now(timezone.utc) - last_dt < timedelta(hours=2):
                        continue
                except Exception:
                    pass

        try:
            publisher = get_publisher(channel, user_id)
            raw_metrics = await publisher.get_post_metrics(platform_post_id)
            if raw_metrics:
                record_post_metrics(
                    user_id=user_id,
                    draft_id=post.get("draft_id", ""),
                    scheduled_post_id=post["id"],
                    channel=channel,
                    platform_post_id=platform_post_id,
                    metrics=raw_metrics,
                    post_text=post.get("caption_override") or post.get("generated_text", ""),
                    topic=post.get("topic", ""),
                    content_type=post.get("content_type", "text_post"),
                )
                updated += 1

                # Auto-record strategy outcome if engagement is notable
                await _auto_record_strategy_outcome(user_id, post, raw_metrics)
        except Exception as e:
            logger.debug("[metrics_ingestion] Metrics fetch failed for post %s: %s", post["id"], e)

    return updated


async def _auto_record_strategy_outcome(user_id: str, post: dict, metrics: dict) -> None:
    """
    If a post has notable engagement, automatically record a strategy outcome
    to feed the learning loop without requiring manual input.
    """
    from math import tanh
    likes = metrics.get("likes", 0) + metrics.get("like_count", 0)
    comments = metrics.get("comments", 0) + metrics.get("reply_count", 0)
    shares = metrics.get("shares", 0) + metrics.get("retweet_count", 0)
    impressions = metrics.get("impressions", 0) + metrics.get("impression_count", 0)

    if impressions < 10:
        return  # Not enough data

    # Simple engagement rate
    eng_rate = (likes + comments + shares) / max(impressions, 1)

    # Determine outcome: >3% = success, <0.5% = failure
    if eng_rate >= 0.03:
        outcome = "success"
    elif eng_rate < 0.005 and impressions >= 100:
        outcome = "failure"
    else:
        return  # Inconclusive — don't record

    objective = post.get("objective", "")
    experiment_id = None
    if objective.startswith("growth_experiment:"):
        experiment_id = objective.split(":", 1)[1]

    if not experiment_id:
        return

    try:
        from app.core.store.growth_experiment_store import get_experiment
        from app.core.store.learning_store import record_strategy, update_strategy_outcome
        exp = get_experiment(experiment_id, user_id)
        if not exp:
            return

        niche = exp.get("niche", "general")
        content_type = post.get("content_type", "text_post")

        # Check if we already have a strategy record for this post
        from app.core.store.learning_store import get_strategy_records
        existing = get_strategy_records(
            user_id,
            niche=niche,
            strategy_type=content_type,
        )
        # Only record once per post
        post_id = post["id"]
        already_recorded = any(
            r.get("recommendation_data", {}).get("post_id") == post_id
            for r in existing
        )
        if already_recorded:
            return

        sr = record_strategy(
            user_id=user_id,
            strategy_type=content_type,
            strategy_title=post.get("title", post.get("topic", "untitled")),
            niche=niche,
            channel=post.get("channel", "x"),
            recommendation_data={
                "post_id": post_id,
                "platform_post_id": post.get("platform_post_id"),
                "topic": post.get("topic", ""),
                "engagement_rate": round(eng_rate, 4),
            },
            source="auto_metrics",
        )
        update_strategy_outcome(
            sr["id"],
            outcome=outcome,
            outcome_data={
                "impressions": impressions,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": round(eng_rate, 4),
            },
        )
        logger.info(
            "[metrics_ingestion] Auto-recorded %s outcome for post %s (eng_rate=%.3f)",
            outcome, post_id, eng_rate,
        )
    except Exception as e:
        logger.debug("[metrics_ingestion] Auto strategy outcome failed: %s", e)


# ── All-users helpers ─────────────────────────────────────────────────────────

def _get_all_user_ids() -> list[str]:
    """
    Return all user IDs that have any stored credentials.
    Reads the credential store directly to avoid DB dependency.
    """
    from app.core.store.credential_store import _load as load_credentials
    try:
        data = load_credentials()
        return list({c["user_id"] for c in data.get("credentials", []) if "user_id" in c})
    except Exception:
        return []


# ── Background loop functions (called from main.py) ──────────────────────────

async def run_post_metrics_ingestion() -> None:
    """
    One-shot: fetch post metrics for all users.
    Called by the hourly background loop in main.py.
    """
    user_ids = _get_all_user_ids()
    if not user_ids:
        return

    total_updated = 0
    for uid in user_ids:
        try:
            n = await _ingest_post_metrics_for_user(uid)
            total_updated += n
        except Exception as e:
            logger.debug("[metrics_ingestion] Error for user %s: %s", uid, e)

    if total_updated:
        logger.info("[metrics_ingestion] post_metrics updated=%d users=%d", total_updated, len(user_ids))


async def run_follower_count_ingestion() -> None:
    """
    One-shot: fetch follower counts for all users with connected accounts.
    Called by the 6-hour background loop in main.py.
    """
    user_ids = _get_all_user_ids()
    if not user_ids:
        return

    for uid in user_ids:
        # X followers
        try:
            count = await _fetch_x_follower_count(uid)
            if count is not None:
                append_follower_snapshot(uid, "x", count)
                logger.info("[metrics_ingestion] X followers user=%s count=%d", uid, count)
        except Exception as e:
            logger.debug("[metrics_ingestion] X follower error user=%s: %s", uid, e)

        # Instagram followers
        try:
            count = await _fetch_instagram_follower_count(uid)
            if count is not None:
                append_follower_snapshot(uid, "instagram", count)
                logger.info("[metrics_ingestion] IG followers user=%s count=%d", uid, count)
        except Exception as e:
            logger.debug("[metrics_ingestion] IG follower error user=%s: %s", uid, e)
