"""
Trend Intelligence Service
==========================
Ingests real trending signals from external sources, scores and normalizes them,
and stores per-niche in trend_store.

Sources (in order of preference):
  1. Reddit JSON API — hot posts from niche-relevant subreddits (no auth required)
  2. Google Trends RSS — general trending searches (free, no key)
  3. Seeded niche_data.py — reliable fallback when external sources fail

Scoring:
  momentum_score = tanh(upvotes / K_upvotes) * 0.6 + tanh(comments / K_comments) * 0.4
  Normalized to [0.0, 1.0]. Top 12 signals per niche retained.

Refresh cadence: every 6 hours via background job in main.py lifespan.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.store.trend_store import get_signals, is_cache_fresh, store_signals
from app.intelligence.niche_data import _trends as seeded_trends

logger = logging.getLogger(__name__)

# ── Niche → subreddit mapping ─────────────────────────────────────────────────
# Each niche maps to 2-4 high-signal subreddits to maximize relevance.

NICHE_SUBREDDITS: dict[str, list[str]] = {
    "tech":      ["technology", "artificial", "programming", "MachineLearning"],
    "fashion":   ["femalefashionadvice", "malefashionadvice", "streetwear", "frugalmalefashion"],
    "food":      ["food", "recipes", "Cooking", "EatCheapAndHealthy"],
    "fitness":   ["fitness", "bodybuilding", "loseit", "running"],
    "travel":    ["travel", "solotravel", "backpacking", "TravelHacks"],
    "ecommerce": ["entrepreneur", "smallbusiness", "Flipping", "dropship"],
    "creator":   ["NewTubers", "podcasting", "content_marketing", "Blogging"],
    "beauty":    ["SkincareAddiction", "MakeupAddiction", "beauty", "HaircareScience"],
    "b2b":       ["marketing", "sales", "startups", "analytics"],
    "wellness":  ["selfimprovement", "meditation", "mentalhealth", "Mindfulness"],
    "general":   ["AskReddit", "worldnews", "technology", "todayilearned"],
}

# Normalization constants (tuned to typical subreddit hot post volumes)
K_UPVOTES = 2000.0
K_COMMENTS = 300.0

# Reddit JSON endpoint — public, no auth, rate limit ~60 req/min
REDDIT_HOT_URL = "https://www.reddit.com/r/{subreddit}/hot.json?limit=25&raw_json=1"
REDDIT_HEADERS = {"User-Agent": "ai-growth-os/0.1 trend-intel"}

# Google Trends daily RSS — US geo, general
GOOGLE_TRENDS_RSS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"


def _make_signal_id(keyword: str, source: str) -> str:
    return hashlib.md5(f"{keyword}:{source}".encode()).hexdigest()[:16]


def _clean_title(title: str) -> str:
    """Strip Reddit/RSS formatting noise from a post title."""
    title = re.sub(r"\[.*?\]", "", title).strip()
    title = re.sub(r"\s+", " ", title)
    # Truncate to ~60 chars for display
    if len(title) > 70:
        title = title[:67].rsplit(" ", 1)[0] + "…"
    return title


def _momentum_score(upvotes: int, comments: int) -> float:
    """Tanh-compressed momentum score in [0, 1]."""
    u = math.tanh(upvotes / K_UPVOTES) * 0.6
    c = math.tanh(comments / K_COMMENTS) * 0.4
    return round(u + c, 3)


async def _fetch_reddit_signals(niche: str, timeout: float = 10.0) -> list[dict]:
    """Fetch hot posts from niche subreddits and score them."""
    subreddits = NICHE_SUBREDDITS.get(niche, NICHE_SUBREDDITS["general"])
    signals: list[dict] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for sub in subreddits[:3]:  # max 3 subreddits per niche per refresh
            try:
                url = REDDIT_HOT_URL.format(subreddit=sub)
                resp = await client.get(url, headers=REDDIT_HEADERS)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts[:10]:  # top 10 hot posts per subreddit
                    p = post.get("data", {})
                    title = _clean_title(p.get("title", ""))
                    if len(title) < 8:
                        continue

                    upvotes = p.get("ups", 0)
                    comments = p.get("num_comments", 0)
                    score = _momentum_score(upvotes, comments)

                    if score < 0.05:  # filter noise
                        continue

                    signals.append({
                        "id": _make_signal_id(title, f"reddit/{sub}"),
                        "keyword": title,
                        "source": f"reddit/r/{sub}",
                        "provenance": "observed",
                        "momentum_score": score,
                        "velocity": round(score * 1.2, 3),  # velocity = score amplified (proxy)
                        "volume_current": upvotes,
                        "volume_prior": max(0, upvotes - comments * 3),  # rough prior estimate
                        "confidence": 0.75,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "evidence": [f"reddit/r/{sub}"],
                        "action_hint": f"Create content around: {title}",
                    })

            except (httpx.RequestError, httpx.TimeoutException, KeyError, ValueError) as e:
                logger.debug("[trends] reddit/%s fetch failed: %s", sub, e)
                continue

    return signals


async def _fetch_google_trends_signals(timeout: float = 8.0) -> list[dict]:
    """Fetch daily trending searches from Google Trends RSS."""
    try:
        import feedparser  # already in requirements
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(GOOGLE_TRENDS_RSS_URL)
            if resp.status_code != 200:
                return []

        # feedparser is sync, run in thread
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, resp.text)

        signals = []
        for entry in feed.entries[:15]:
            title = _clean_title(entry.get("title", ""))
            if len(title) < 6:
                continue

            # Google Trends embeds traffic estimate in the ht:approx_traffic tag
            traffic = 1000
            try:
                traffic = int(entry.get("ht_approx_traffic", "1+").replace("+", "").replace(",", ""))
            except (ValueError, AttributeError):
                pass

            score = _momentum_score(traffic, traffic // 10)

            signals.append({
                "id": _make_signal_id(title, "google_trends"),
                "keyword": title,
                "source": "google_trends",
                "provenance": "observed",
                "momentum_score": min(score, 0.95),
                "velocity": min(score * 1.3, 1.0),
                "volume_current": traffic,
                "volume_prior": traffic // 2,
                "confidence": 0.80,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "evidence": ["google_trends/daily"],
                "action_hint": f"Trending topic to tap: {title}",
            })

        return signals

    except Exception as e:
        logger.debug("[trends] google_trends fetch failed: %s", e)
        return []


def _seeded_signals(niche: str) -> list[dict]:
    """Return seeded signals from niche_data.py as TrendSignal-compatible dicts."""
    # seeded_trends is called with a dummy brand_name since we only need the trend shape
    raw = seeded_trends(niche, "brand")
    if isinstance(raw, dict):
        raw = raw.get(niche, [])
    result = []
    for t in raw[:8]:
        result.append({
            "id": _make_signal_id(t.get("keyword", ""), "seeded"),
            "keyword": t.get("keyword", ""),
            "source": "seeded_niche_data",
            "provenance": "estimated",
            "momentum_score": t.get("momentum_score", 0.5),
            "velocity": t.get("momentum_score", 0.5) * 0.8,
            "volume_current": t.get("volume_current", 5000),
            "volume_prior": t.get("volume_prior", 3000),
            "confidence": 0.55,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "evidence": t.get("evidence", []),
            "action_hint": t.get("action_hint", ""),
        })
    return result


def _dedupe_and_rank(signals: list[dict], limit: int = 12) -> list[dict]:
    """Remove near-duplicates (same first 30 chars) and rank by momentum_score."""
    seen: set[str] = set()
    unique = []
    for s in signals:
        key = s.get("keyword", "")[:30].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return sorted(unique, key=lambda x: x.get("momentum_score", 0), reverse=True)[:limit]


async def refresh_niche_trends(niche: str, force: bool = False) -> list[dict]:
    """
    Refresh trend signals for a given niche.

    Fetch order:
      1. Reddit hot posts (niche subreddits)
      2. Google Trends RSS (general trending)
      3. Seeded fallback (always included to ensure min 5 signals)

    Results are stored in trend_store with 6h TTL.
    Returns the stored signals.
    """
    if not force and is_cache_fresh(niche):
        logger.debug("[trends] cache hit for niche=%s", niche)
        return get_signals(niche)

    logger.info("[trends] refreshing niche=%s", niche)

    reddit_task = asyncio.create_task(_fetch_reddit_signals(niche))
    google_task = asyncio.create_task(_fetch_google_trends_signals())

    reddit_signals, google_signals = await asyncio.gather(
        reddit_task, google_task, return_exceptions=True
    )

    all_signals: list[dict] = []

    if isinstance(reddit_signals, list):
        all_signals.extend(reddit_signals)
    else:
        logger.warning("[trends] reddit fetch exception: %s", reddit_signals)

    if isinstance(google_signals, list):
        # Google Trends is general; only include signals if they partially match niche keywords
        niche_keywords = NICHE_SUBREDDITS.get(niche, [])
        filtered_google = [
            s for s in google_signals
            if _is_niche_relevant(s.get("keyword", ""), niche)
        ]
        all_signals.extend(filtered_google[:5])

    # Always augment with seeded signals to ensure coverage
    seeded = _seeded_signals(niche)
    all_signals.extend(seeded)

    final = _dedupe_and_rank(all_signals)
    store_signals(niche, final)

    logger.info("[trends] stored %d signals for niche=%s (reddit=%d, seeded=%d)",
                len(final), niche,
                len(reddit_signals) if isinstance(reddit_signals, list) else 0,
                len(seeded))
    return final


def _is_niche_relevant(keyword: str, niche: str) -> bool:
    """Rough relevance check: does keyword contain niche-related terms?"""
    kw = keyword.lower()
    niche_terms: dict[str, list[str]] = {
        "tech":      ["tech", "ai", "software", "app", "digital", "data", "cloud"],
        "fashion":   ["fashion", "style", "clothing", "outfit", "wear", "dress"],
        "food":      ["food", "recipe", "eat", "cook", "meal", "restaurant", "diet"],
        "fitness":   ["fitness", "workout", "gym", "health", "exercise", "weight"],
        "travel":    ["travel", "trip", "vacation", "flight", "hotel", "destination"],
        "ecommerce": ["shop", "price", "deal", "buy", "store", "product"],
        "creator":   ["creator", "content", "video", "channel", "streaming", "social"],
        "beauty":    ["beauty", "skincare", "makeup", "hair", "skin", "cosmetic"],
        "b2b":       ["business", "marketing", "sales", "startup", "revenue", "growth"],
        "wellness":  ["mental", "wellness", "stress", "mindful", "meditation", "anxiety"],
    }
    terms = niche_terms.get(niche, [])
    return any(t in kw for t in terms)


async def get_or_refresh_trends(niche: str) -> list[dict]:
    """
    Public interface: return cached signals if fresh, otherwise refresh.
    Always returns at least seeded signals.
    """
    if is_cache_fresh(niche):
        cached = get_signals(niche)
        if cached:
            return cached

    return await refresh_niche_trends(niche)


async def refresh_all_active_niches() -> dict[str, int]:
    """Refresh trends for all known niches. Called by the scheduled job."""
    niches = list(NICHE_SUBREDDITS.keys())
    results = {}
    for niche in niches:
        try:
            signals = await refresh_niche_trends(niche, force=False)
            results[niche] = len(signals)
        except Exception as e:
            logger.error("[trends] failed to refresh niche=%s: %s", niche, e)
            results[niche] = 0
    return results
