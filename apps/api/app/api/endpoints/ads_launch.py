"""
Ads Launch API — POST /api/v1/ads/launch

Routes campaign launch requests to MetaAdsService or GoogleAdsService.
Both services operate on real API credentials stored via OAuth social flow.

Endpoints:
  POST /ads/launch          — Create + optionally activate a paid campaign
  POST /ads/{ad_id}/activate — Activate a paused campaign
  POST /ads/{ad_id}/pause   — Pause a running campaign
  GET  /ads/{ad_id}/insights — Fetch campaign performance metrics
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.services.ads.meta_ads import MetaAdsService
from app.services.ads.google_ads import GoogleAdsService

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / Response models ────────────────────────────────────────────────

class AdLaunchRequest(BaseModel):
    platform: Literal["meta", "google"]
    name: str
    objective: str = "traffic"           # traffic | conversions | awareness | leads
    daily_budget_usd: float = Field(gt=0)
    landing_page_url: str
    # Creative
    headline: str
    description: str
    # Targeting
    age_min: int = 18
    age_max: int = 65
    geo_locations: Optional[list[str]] = None   # e.g. ["US", "CA"]
    interests: Optional[list[str]] = None       # Meta interest names
    # Google-specific
    keywords: Optional[list[str]] = None
    extra_headlines: Optional[list[str]] = None
    extra_descriptions: Optional[list[str]] = None
    # Behaviour
    activate_immediately: bool = False


class AdLaunchResponse(BaseModel):
    success: bool
    platform: str
    campaign_id: Optional[str] = None
    ad_set_id: Optional[str] = None
    ad_id: Optional[str] = None
    creative_id: Optional[str] = None
    budget_resource_name: Optional[str] = None
    ad_group_id: Optional[str] = None
    status: str = "paused"
    error: Optional[str] = None


class AdInsightsResponse(BaseModel):
    platform: str
    campaign_id: str
    impressions: int = 0
    clicks: int = 0
    spend_usd: float = 0.0
    cpc: float = 0.0
    ctr: float = 0.0
    reach: int = 0
    conversions: int = 0
    date_preset: str


# ─── Launch ───────────────────────────────────────────────────────────────────

@router.post("/ads/launch", response_model=AdLaunchResponse)
async def launch_campaign(
    body: AdLaunchRequest,
    current_user=Depends(get_current_user),
) -> AdLaunchResponse:
    """
    Create a paid advertising campaign on Meta or Google.
    Campaign starts PAUSED unless activate_immediately=true.
    """
    user_id = str(current_user.id)

    if body.platform == "meta":
        svc = MetaAdsService(user_id=user_id)
        result = await svc.create_campaign(
            name=body.name,
            objective=body.objective,
            daily_budget_usd=body.daily_budget_usd,
            landing_page_url=body.landing_page_url,
            headline=body.headline,
            description=body.description,
            age_min=body.age_min,
            age_max=body.age_max,
            geo_locations=body.geo_locations,
            interests=body.interests,
        )
        if not result.success:
            return AdLaunchResponse(
                success=False, platform="meta", error=result.error,
                campaign_id=result.campaign_id,
            )

        if body.activate_immediately and result.campaign_id:
            await svc.activate_campaign(result.campaign_id)

        return AdLaunchResponse(
            success=True,
            platform="meta",
            campaign_id=result.campaign_id,
            ad_set_id=result.ad_set_id,
            ad_id=result.ad_id,
            creative_id=result.creative_id,
            status="active" if body.activate_immediately else "paused",
        )

    elif body.platform == "google":
        svc = GoogleAdsService(user_id=user_id)
        headlines = [body.headline] + (body.extra_headlines or [])
        descriptions = [body.description] + (body.extra_descriptions or [])
        keywords = body.keywords or [body.name]

        result = await svc.create_search_campaign(
            name=body.name,
            daily_budget_usd=body.daily_budget_usd,
            landing_page_url=body.landing_page_url,
            headlines=headlines,
            descriptions=descriptions,
            keywords=keywords,
            geo_location_ids=body.geo_locations,
        )
        if not result.success:
            return AdLaunchResponse(
                success=False, platform="google", error=result.error,
                campaign_id=result.campaign_id,
            )

        if body.activate_immediately and result.campaign_id:
            await svc.activate_campaign(result.campaign_id)

        return AdLaunchResponse(
            success=True,
            platform="google",
            campaign_id=result.campaign_id,
            budget_resource_name=result.budget_id,
            ad_group_id=result.ad_group_id,
            ad_id=result.ad_id,
            status="active" if body.activate_immediately else "paused",
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {body.platform}")


# ─── Activate ─────────────────────────────────────────────────────────────────

@router.post("/ads/{platform}/{campaign_id}/activate")
async def activate_campaign(
    platform: Literal["meta", "google"],
    campaign_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    user_id = str(current_user.id)
    if platform == "meta":
        ok = await MetaAdsService(user_id=user_id).activate_campaign(campaign_id)
    else:
        ok = await GoogleAdsService(user_id=user_id).activate_campaign(campaign_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to activate campaign. Check credentials.")
    return {"success": True, "campaign_id": campaign_id, "status": "active"}


# ─── Pause ────────────────────────────────────────────────────────────────────

@router.post("/ads/{platform}/{campaign_id}/pause")
async def pause_campaign(
    platform: Literal["meta", "google"],
    campaign_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    user_id = str(current_user.id)
    if platform == "meta":
        ok = await MetaAdsService(user_id=user_id).pause_campaign(campaign_id)
    else:
        ok = await GoogleAdsService(user_id=user_id).pause_campaign(campaign_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to pause campaign.")
    return {"success": True, "campaign_id": campaign_id, "status": "paused"}


# ─── Insights ─────────────────────────────────────────────────────────────────

@router.get("/ads/{platform}/{campaign_id}/insights", response_model=AdInsightsResponse)
async def get_campaign_insights(
    platform: Literal["meta", "google"],
    campaign_id: str,
    date_preset: str = "last_7d",
    days: int = 7,
    current_user=Depends(get_current_user),
) -> AdInsightsResponse:
    user_id = str(current_user.id)

    if platform == "meta":
        data = await MetaAdsService(user_id=user_id).get_campaign_insights(
            campaign_id, date_preset=date_preset
        )
        if not data:
            raise HTTPException(status_code=502, detail="Could not fetch Meta insights.")
        return AdInsightsResponse(
            platform="meta",
            campaign_id=campaign_id,
            impressions=data.get("impressions", 0),
            clicks=data.get("clicks", 0),
            spend_usd=data.get("spend_usd", 0.0),
            cpc=data.get("cpc", 0.0),
            ctr=data.get("ctr", 0.0),
            reach=data.get("reach", 0),
            date_preset=date_preset,
        )

    else:
        data = await GoogleAdsService(user_id=user_id).get_campaign_metrics(
            campaign_id, days=days
        )
        if not data:
            raise HTTPException(status_code=502, detail="Could not fetch Google insights.")
        return AdInsightsResponse(
            platform="google",
            campaign_id=campaign_id,
            impressions=data.get("impressions", 0),
            clicks=data.get("clicks", 0),
            spend_usd=data.get("cost_usd", 0.0),
            cpc=data.get("cpc", 0.0),
            ctr=data.get("ctr", 0.0),
            conversions=data.get("conversions", 0),
            date_preset=f"last_{days}d",
        )
