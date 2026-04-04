"""
Brand profile API endpoints — Instagram-first brand intelligence.
All endpoints derive data from the user's brand profile + niche intelligence engine.

DATA MODE:
  real_test — user has provided instagram_handle and/or website_url
  demo      — no real account connected; all data is inferred/estimated

PROVENANCE LABELS (attached to every intelligence response):
  user_provided  — entered directly by the user during onboarding
  observed       — pulled from a live connected account or analytics source
  inferred       — derived by the niche intelligence engine from user inputs
  estimated      — industry benchmark / statistical estimate, not account-specific
  demo           — seeded placeholder data; no real account connected
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.store.brand_store import get_brand_profile, upsert_brand_profile
from app.intelligence.niche_data import get_dashboard_overview, get_intelligence, infer_niche

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Data mode helpers ─────────────────────────────────────────────────────────


def _data_mode(profile: dict) -> str:
    """Return 'real_test' if the user has provided real account data, else 'demo'."""
    has_instagram = bool(profile.get("instagram_handle"))
    has_website = bool(profile.get("website_url"))
    has_real_name = bool(
        profile.get("brand_name")
        and profile["brand_name"].lower() not in ("acme", "demo", "example")
    )
    return "real_test" if (has_instagram or has_website or has_real_name) else "demo"


def _provenance(mode: str, field: str) -> str:
    """Return the provenance label for a given field in the given data mode."""
    if mode == "demo":
        return "demo"
    user_provided_fields = {
        "brand_name",
        "instagram_handle",
        "website_url",
        "category",
        "target_audience",
        "geography",
        "business_goal",
        "description",
    }
    if field in user_provided_fields:
        return "user_provided"
    observed_fields = {"followers", "engagement_rate", "post_count", "reach"}
    if field in observed_fields:
        return "observed"
    estimated_fields = {
        "cpm_range",
        "cpc_range",
        "cac_estimate",
        "roas_estimate",
        "budget_estimate",
    }
    if field in estimated_fields:
        return "estimated"
    return "inferred"


def _meta(profile: dict, source: str = "niche_engine") -> dict:
    mode = _data_mode(profile)
    return {
        "data_mode": mode,
        "source": source,
        "provenance": {
            "brand_inputs": "user_provided" if mode == "real_test" else "demo",
            "niche_intelligence": "inferred",
            "audience_estimates": "estimated",
            "benchmark_metrics": "estimated",
            "recommendations": "inferred",
        },
        "confidence": 0.7 if mode == "real_test" else 0.5,
        "note": (
            "Intelligence derived from your brand inputs + niche engine. "
            "Connect analytics (GA4, GSC) for observed data."
            if mode == "real_test"
            else "Demo mode — connect your Instagram account or website to get personalized intelligence."
        ),
    }


# ── Schemas ───────────────────────────────────────────────────────────────────


class BrandProfileCreate(BaseModel):
    instagram_handle: str | None = None
    brand_name: str
    website_url: str | None = None
    description: str | None = None
    category: str | None = None
    niche: str | None = None
    target_audience: str | None = None
    geography: str | None = None
    business_goal: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_profile_or_404(user_id: str) -> dict:
    profile = get_brand_profile(str(user_id))
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No brand profile found. Complete onboarding first.",
        )
    return profile


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/profile")
async def create_or_update_profile(
    payload: BrandProfileCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """Create or update the brand profile for the authenticated user."""
    profile_data = payload.model_dump(exclude_none=False)
    # Infer and persist niche if not explicitly provided
    if not profile_data.get("niche") and profile_data.get("category"):
        profile_data["niche"] = infer_niche(profile_data["category"])
    profile = upsert_brand_profile(str(current_user.id), profile_data)
    return {"profile": profile, "message": "Brand profile saved."}


@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)) -> dict:
    """Get the current user's brand profile."""
    profile = get_brand_profile(str(current_user.id))
    if not profile:
        return {"profile": None, "onboarding_required": True}
    return {"profile": profile, "onboarding_required": False}


@router.get("/overview")
async def get_overview(current_user=Depends(get_current_user)) -> dict:
    """Dashboard overview driven by brand profile + niche intelligence."""
    profile = get_brand_profile(str(current_user.id))
    if not profile:
        return {
            "onboarding_required": True,
            "brand_name": None,
            "niche": None,
            "top_trends": [],
            "top_recommendations": [],
            "top_audiences": [],
            "kpis": {},
        }
    raw = get_dashboard_overview(profile)
    intel = get_intelligence(profile)

    trends = intel.get("trends", [])
    recs = intel.get("recommendations", [])
    segments = intel.get("audience_segments", [])

    top_trend = trends[0] if trends else None

    return {
        "brand_name": raw.get("brand_name"),
        "instagram_handle": raw.get("instagram_handle"),
        "niche": raw.get("niche"),
        "_meta": _meta(profile),
        "kpis": {
            "trend_count": len(trends),
            "top_trend_momentum": top_trend["momentum_score"] if top_trend else 0,
            "audience_segments": len(segments),
            "recommendation_count": len(recs),
            "top_recommendation_title": recs[0]["title"] if recs else "",
        },
        "top_trends": [
            {"keyword": t["keyword"], "momentum_score": t["momentum_score"]}
            for t in sorted(trends, key=lambda x: x["momentum_score"], reverse=True)[:5]
        ],
        "top_recommendations": [
            {
                "title": r["title"],
                "priority_score": r.get("priority_score", 0),
                "category": r.get("category", "growth"),
            }
            for r in sorted(recs, key=lambda x: x.get("priority_score", 0), reverse=True)[:5]
        ],
        "top_audiences": [
            {
                "segment_name": s.get("segment_name") or s.get("name", ""),
                "fit_score": s.get("fit_score", 0),
                "content_angle": s.get("content_angle", ""),
            }
            for s in segments[:3]
        ],
    }


@router.get("/trends")
async def get_trends(current_user=Depends(get_current_user)) -> dict:
    """Niche-specific trend intelligence for the brand."""
    profile = get_brand_profile(str(current_user.id))
    if not profile:
        return {"onboarding_required": True, "trends": [], "brand_name": None, "niche": None}
    intel = get_intelligence(profile)
    return {
        "trends": intel.get("trends", []),
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


@router.get("/audience")
async def get_audience(current_user=Depends(get_current_user)) -> dict:
    """Audience segment intelligence for the brand."""
    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    raw_segments = intel.get("audience_segments", [])
    segments = [
        {**s, "segment_name": s.get("segment_name") or s.get("name", "")} for s in raw_segments
    ]
    return {
        "segments": segments,
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


@router.get("/recommendations")
async def get_recommendations(current_user=Depends(get_current_user)) -> dict:
    """Prioritized growth recommendations for the brand."""
    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    return {
        "recommendations": intel.get("recommendations", []),
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


@router.get("/content-opportunities")
async def get_content_opportunities(current_user=Depends(get_current_user)) -> dict:
    """Content opportunity themes for the brand."""
    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    return {
        "opportunities": intel.get("content_opportunities", []),
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


@router.get("/media-plan")
async def get_media_plan(current_user=Depends(get_current_user)) -> dict:
    """Niche-specific media planning recommendations."""
    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    return {
        "media_plan": intel.get("media_plan", {}),
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


@router.get("/geo")
async def get_geo_signals(current_user=Depends(get_current_user)) -> dict:
    """GEO/SEO audit signals for the brand."""
    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    return {
        "geo_signals": intel.get("geo_signals", []),
        "website_url": profile.get("website_url"),
        "brand_name": profile.get("brand_name"),
        "niche": intel.get("niche"),
        "_meta": _meta(profile),
    }


# ── Growth Stage ──────────────────────────────────────────────────────────────


def _compute_growth_stage(profile: dict) -> dict:
    """
    Derive the current growth stage from brand profile data.

    Stages:
      cold_start   — new account, < 50 posts OR < 1000 followers
      growing      — posts >= 50 AND followers >= 1000
      optimizing   — growing + meaningful outcome data available
    """
    followers = int(profile.get("followers", 0) or 0)
    post_count = int(profile.get("post_count", 0) or 0)
    outcome_count = int(profile.get("labeled_outcome_count", 0) or 0)

    if followers < 1000 or post_count < 50:
        stage = "cold_start"
        description = "Building initial presence. Using niche-default content priors."
        next_milestone = f"{max(0, 1000 - followers)} more followers or {max(0, 50 - post_count)} more posts to exit cold-start"
    elif outcome_count >= 20:
        stage = "optimizing"
        description = "Enough labeled outcomes to optimize. Bandit learning is active."
        next_milestone = "Continue collecting outcomes to improve confidence"
    else:
        stage = "growing"
        description = "Account established. Collecting outcome data for bandit optimization."
        next_milestone = (
            f"{max(0, 20 - outcome_count)} more labeled outcomes to reach optimizing stage"
        )

    # Cold-start content mix priors by niche (used by content engine when in cold_start)
    niche = infer_niche(profile.get("category", "") or profile.get("niche", "") or "general")
    cold_start_mix = {
        "tech": {"educational": 0.45, "product": 0.25, "behind_scenes": 0.20, "engagement": 0.10},
        "fashion": {"inspirational": 0.40, "product": 0.35, "lifestyle": 0.15, "engagement": 0.10},
        "food": {"recipe": 0.50, "educational": 0.25, "behind_scenes": 0.15, "engagement": 0.10},
        "fitness": {"educational": 0.40, "motivational": 0.30, "product": 0.20, "engagement": 0.10},
        "beauty": {"tutorial": 0.45, "product": 0.30, "lifestyle": 0.15, "engagement": 0.10},
        "travel": {
            "inspirational": 0.45,
            "educational": 0.25,
            "lifestyle": 0.20,
            "engagement": 0.10,
        },
        "ecommerce": {
            "product": 0.40,
            "social_proof": 0.30,
            "educational": 0.20,
            "engagement": 0.10,
        },
        "creator": {
            "behind_scenes": 0.35,
            "educational": 0.30,
            "inspirational": 0.25,
            "engagement": 0.10,
        },
        "b2b": {
            "educational": 0.50,
            "case_study": 0.25,
            "thought_leadership": 0.15,
            "engagement": 0.10,
        },
        "wellness": {
            "educational": 0.40,
            "motivational": 0.30,
            "lifestyle": 0.20,
            "engagement": 0.10,
        },
        "general": {
            "educational": 0.35,
            "inspirational": 0.30,
            "product": 0.25,
            "engagement": 0.10,
        },
    }.get(niche, {"educational": 0.35, "inspirational": 0.30, "product": 0.25, "engagement": 0.10})

    return {
        "stage": stage,
        "description": description,
        "next_milestone": next_milestone,
        "followers": followers,
        "post_count": post_count,
        "labeled_outcome_count": outcome_count,
        "cold_start_content_mix": cold_start_mix if stage == "cold_start" else None,
        "posting_cadence_per_week": 5
        if stage == "cold_start"
        else (7 if stage == "growing" else None),
        "niche": niche,
    }


@router.get("/growth-stage")
async def get_growth_stage(current_user=Depends(get_current_user)) -> dict:
    """
    Return the brand's current growth stage and cold-start configuration.

    Stages: cold_start → growing → optimizing
    """
    profile = _get_profile_or_404(str(current_user.id))
    stage_data = _compute_growth_stage(profile)
    return {
        **stage_data,
        "brand_name": profile.get("brand_name"),
        "_meta": _meta(profile, source="growth_stage_engine"),
    }


@router.post("/growth-stage/update-metrics")
async def update_growth_metrics(
    payload: dict,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Update observable growth metrics on the brand profile.
    Called after fetching real follower/post counts from connected accounts.
    """
    profile = get_brand_profile(str(current_user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="No brand profile found")

    allowed_fields = {
        "followers",
        "post_count",
        "engagement_rate",
        "reach",
        "labeled_outcome_count",
    }
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    updated = upsert_brand_profile(str(current_user.id), {**profile, **updates})
    stage_data = _compute_growth_stage(updated)
    return {"profile": updated, "growth_stage": stage_data}


# ── Trend Intelligence (live) ─────────────────────────────────────────────────


@router.get("/live-trends")
async def get_live_trends(
    force_refresh: bool = False,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Return live trend signals for the brand's niche.
    Fetches from Reddit + Google Trends RSS with 6h TTL cache.
    Falls back to seeded niche intelligence if external sources fail.
    """
    from app.services.trend_intelligence import get_or_refresh_trends

    profile = _get_profile_or_404(str(current_user.id))
    intel = get_intelligence(profile)
    niche = intel.get("niche", "general")

    try:
        if force_refresh:
            from app.services.trend_intelligence import refresh_niche_trends

            signals = await refresh_niche_trends(niche, force=True)
        else:
            signals = await get_or_refresh_trends(niche)
    except Exception as e:
        logger.warning("[brand] live trends fetch failed for niche=%s: %s", niche, e)
        # Fall back to seeded intelligence
        signals = intel.get("trends", [])

    return {
        "niche": niche,
        "brand_name": profile.get("brand_name"),
        "signals": signals,
        "count": len(signals),
        "_meta": {**_meta(profile, source="trend_intelligence"), "trend_source": "live+seeded"},
    }


# ── Brand Activation ──────────────────────────────────────────────────────────


class ActivationRequest(BaseModel):
    brand_name: str
    website_url: str | None = None
    instagram_handle: str | None = None
    x_handle: str | None = None
    tiktok_handle: str | None = None
    primary_goal: str = (
        "grow_followers"  # grow_followers | drive_traffic | increase_sales | build_awareness
    )
    monthly_budget_usd: float | None = None
    category: str | None = None
    target_audience: str | None = None
    description: str | None = None


@router.post("/activate")
async def activate_brand(
    payload: ActivationRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Full brand activation sequence.

    Runs all intelligence layers and returns a structured activation result:
      - brand profile saved
      - niche inferred
      - growth stage computed
      - live trends fetched
      - content ideas generated
      - growth plan summary
      - recommended autonomy mode

    This powers the 8-step activation wizard in the frontend.
    Each step's data is returned in the response so the UI can reveal them progressively.
    """
    from app.services.trend_intelligence import get_or_refresh_trends

    # Step 1: Save brand profile
    profile_data = {
        "brand_name": payload.brand_name,
        "website_url": payload.website_url,
        "instagram_handle": payload.instagram_handle,
        "x_handle": payload.x_handle,
        "tiktok_handle": payload.tiktok_handle,
        "category": payload.category or payload.primary_goal,
        "target_audience": payload.target_audience,
        "description": payload.description,
        "business_goal": payload.primary_goal,
        "monthly_budget_usd": payload.monthly_budget_usd,
    }
    profile = upsert_brand_profile(str(current_user.id), profile_data)

    # Step 2: Run intelligence
    intel = get_intelligence(profile)
    niche = intel.get("niche", "general")
    # Persist inferred niche back to profile so downstream consumers don't re-infer it
    if not profile.get("niche") or profile.get("niche") != niche:
        profile = upsert_brand_profile(str(current_user.id), {**profile, "niche": niche})

    # Step 3: Growth stage
    stage_data = _compute_growth_stage(profile)

    # Step 4: Live trends (run in background, fall back to seeded)
    try:
        signals = await asyncio.wait_for(get_or_refresh_trends(niche), timeout=12.0)
    except (TimeoutError, Exception) as e:
        logger.warning("[activate] trend fetch timeout/error: %s", e)
        signals = intel.get("trends", [])[:8]

    # Step 5: Generate content ideas from top trends
    content_ideas = []
    content_types = ["reel_script", "carousel", "caption", "ad_copy", "story"]
    objectives = ["engagement", "awareness", "traffic", "conversion"]
    for i, signal in enumerate(signals[:5]):
        content_ideas.append(
            {
                "topic": signal.get("keyword", ""),
                "content_type": content_types[i % len(content_types)],
                "objective": objectives[i % len(objectives)],
                "action_hint": signal.get("action_hint", ""),
                "momentum_score": signal.get("momentum_score", 0.5),
            }
        )

    # Step 6: Campaign angles from top trends
    campaign_angles = []
    for signal in signals[:3]:
        campaign_angles.append(
            {
                "headline": signal.get("keyword", ""),
                "objective": "TRAFFIC" if payload.primary_goal == "drive_traffic" else "AWARENESS",
                "suggested_budget_usd": min((payload.monthly_budget_usd or 300) / 30, 50),
                "platform": "meta",
            }
        )

    # Step 7: Recommended autonomy mode
    has_budget = bool(payload.monthly_budget_usd and payload.monthly_budget_usd > 0)
    has_social = bool(payload.instagram_handle or payload.tiktok_handle or payload.x_handle)
    recommended_mode = "assisted" if (has_budget and has_social) else "manual"

    # Step 8: Summary
    channels_connected = []
    if payload.instagram_handle:
        channels_connected.append("instagram")
    if payload.x_handle:
        channels_connected.append("x")
    if payload.tiktok_handle:
        channels_connected.append("tiktok")
    if payload.website_url:
        channels_connected.append("website")

    return {
        "success": True,
        "brand_profile": profile,
        "niche": niche,
        "niche_confidence": 0.82 if payload.category else 0.62,
        "growth_stage": stage_data,
        "live_trends": signals[:8],
        "content_ideas": content_ideas,
        "campaign_angles": campaign_angles,
        "channels_connected": channels_connected,
        "recommended_autonomy_mode": recommended_mode,
        "growth_plan_summary": {
            "goal": payload.primary_goal,
            "stage": stage_data["stage"],
            "posting_cadence_per_week": stage_data.get("posting_cadence_per_week", 5),
            "paid_enabled": has_budget,
            "monthly_budget_usd": payload.monthly_budget_usd,
            "top_opportunity": intel.get("recommendations", [{}])[0].get("title", "")
            if intel.get("recommendations")
            else "",
        },
        "_meta": _meta(profile, source="brand_activation"),
    }
