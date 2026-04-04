"""
Campaign Draft API — approval-gated campaign management.

All campaigns start as drafts. No campaign is published to any platform without
explicit human approval. This is Layer 7 (Official Ads Execution) of the platform.

Endpoints:
  POST   /api/v1/campaigns/drafts                  — create campaign draft
  GET    /api/v1/campaigns/drafts                  — list drafts
  GET    /api/v1/campaigns/drafts/{id}             — get draft
  PATCH  /api/v1/campaigns/drafts/{id}             — update draft
  POST   /api/v1/campaigns/drafts/{id}/submit      — submit for approval
  POST   /api/v1/campaigns/drafts/{id}/publish     — publish (post-approval only)
  GET    /api/v1/campaigns/reallocation            — list reallocation decisions
  POST   /api/v1/campaigns/reallocation            — create reallocation decision
  GET    /api/v1/campaigns/audit-log               — full audit trail
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.adapters import ADAPTER_REGISTRY
from app.adapters.base import AdapterCapabilityStage, AdapterCredentials
from app.api.dependencies.auth import get_current_user
from app.core.store.campaign_store import (
    create_campaign_draft,
    create_reallocation_decision,
    get_audit_log,
    get_campaign_draft,
    get_campaign_drafts,
    get_reallocation_decisions,
    mark_published,
    submit_for_approval,
    update_campaign_draft,
)
from app.core.store.credential_store import get_credential, get_linked_accounts, get_platform_stage

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class CampaignDraftCreate(BaseModel):
    platform: str = Field(..., description="meta | google | tiktok | linkedin | pinterest | snap")
    account_id: str | None = Field(
        None, description="Ad account ID. Optional for drafts — required at publish time."
    )
    name: str
    objective: str = Field(
        ...,
        description="awareness | traffic | engagement | leads | conversions | app_installs | video_views | catalog_sales",
    )
    daily_budget_usd: float = Field(..., ge=1.0, description="Daily budget in USD")
    start_date: str | None = Field(None, description="ISO date string YYYY-MM-DD")
    end_date: str | None = Field(None, description="ISO date string YYYY-MM-DD")
    target_audiences: list[dict] = Field(default_factory=list)
    creatives: list[dict] = Field(default_factory=list)
    notes: str = ""
    strategy_version: str = "v1"


class CampaignDraftUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    daily_budget_usd: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    target_audiences: list[dict] | None = None
    creatives: list[dict] | None = None
    notes: str | None = None


class PublishRequest(BaseModel):
    approval_id: str = Field(..., description="Approval record ID that authorized this publish")
    platform_campaign_id: str = Field(
        ..., description="Campaign ID returned by the platform API after publishing"
    )


class ReallocationCreate(BaseModel):
    platform: str
    account_id: str
    campaign_id: str
    old_budget_usd: float = Field(..., ge=0)
    new_budget_usd: float = Field(..., ge=0)
    reason: str
    supporting_metrics: dict = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_approval: bool = True
    rollback_plan: str = "Revert to previous budget if ROAS drops below threshold."


# ── Endpoints ─────────────────────────────────────────────────────────────────

VALID_PLATFORMS = {"meta", "google", "tiktok", "linkedin", "pinterest", "snap"}
VALID_OBJECTIVES = {
    "awareness",
    "traffic",
    "engagement",
    "leads",
    "conversions",
    "app_installs",
    "video_views",
    "catalog_sales",
}


@router.post("/drafts", status_code=201)
async def create_draft(
    payload: CampaignDraftCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Create a campaign draft.

    The draft is always in PAUSED/DRAFT state — it is never published to the
    ad platform without going through the approval workflow.

    Requires: the platform must be connected (account_linked stage).
    """
    if payload.platform not in VALID_PLATFORMS:
        raise HTTPException(400, f"Unsupported platform. Must be one of: {sorted(VALID_PLATFORMS)}")

    if payload.objective not in VALID_OBJECTIVES:
        raise HTTPException(
            400, f"Unsupported objective. Must be one of: {sorted(VALID_OBJECTIVES)}"
        )

    # Check platform stage — warn if not connected, but allow draft creation for planning
    stage = get_platform_stage(str(current_user.id), payload.platform)
    stage_warning = None
    if stage not in ("account_linked",):
        stage_warning = (
            f"Platform '{payload.platform}' is not yet connected (stage: {stage}). "
            f"Draft created for planning purposes. Connect via "
            f"POST /api/v1/ads-connectors/{payload.platform}/auth-url to enable publishing."
        )

    draft = create_campaign_draft(
        user_id=str(current_user.id),
        platform=payload.platform,
        account_id=payload.account_id,
        name=payload.name,
        objective=payload.objective,
        daily_budget_usd=payload.daily_budget_usd,
        start_date=payload.start_date,
        end_date=payload.end_date,
        target_audiences=payload.target_audiences,
        creatives=payload.creatives,
        notes=payload.notes,
        strategy_version=payload.strategy_version,
    )
    result: dict = {
        "draft": draft,
        "message": f"Campaign draft '{payload.name}' created in draft state. Submit for approval to publish.",
        "next_step": f"POST /api/v1/campaigns/drafts/{draft['id']}/submit to begin approval workflow.",
    }
    if stage_warning:
        result["warning"] = stage_warning
    return result


@router.get("/drafts")
async def list_drafts(
    platform: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict:
    """List campaign drafts with optional platform and status filters."""
    drafts = get_campaign_drafts(
        user_id=str(current_user.id),
        platform=platform,
        status=status,
        limit=limit,
    )
    status_counts: dict[str, int] = {}
    for d in drafts:
        status_counts[d["status"]] = status_counts.get(d["status"], 0) + 1

    return {
        "drafts": drafts,
        "total": len(drafts),
        "by_status": status_counts,
    }


@router.get("/drafts/{draft_id}")
async def get_draft(
    draft_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Get a specific campaign draft."""
    draft = get_campaign_draft(draft_id)
    if not draft or draft["user_id"] != str(current_user.id):
        raise HTTPException(404, "Campaign draft not found.")
    return {"draft": draft}


@router.patch("/drafts/{draft_id}")
async def update_draft(
    draft_id: str,
    payload: CampaignDraftUpdate,
    current_user=Depends(get_current_user),
) -> dict:
    """Update a campaign draft. Only drafts in 'draft' status can be edited."""
    draft = get_campaign_draft(draft_id)
    if not draft or draft["user_id"] != str(current_user.id):
        raise HTTPException(404, "Campaign draft not found.")
    if draft["status"] not in ("draft",):
        raise HTTPException(
            409,
            f"Cannot edit a draft in '{draft['status']}' status. Only 'draft' status drafts can be updated.",
        )

    updates = dict(payload.model_dump(exclude_none=True).items())
    updated = update_campaign_draft(draft_id, updates)
    return {"draft": updated, "message": "Draft updated."}


@router.post("/drafts/{draft_id}/submit")
async def submit_draft(
    draft_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Submit a campaign draft for human approval.

    Creates an approval queue item. The draft will not be published until
    explicitly approved via POST /api/v1/approvals/{approval_id}/action.
    """
    draft = get_campaign_draft(draft_id)
    if not draft or draft["user_id"] != str(current_user.id):
        raise HTTPException(404, "Campaign draft not found.")
    if draft["status"] != "draft":
        raise HTTPException(409, f"Draft is already in '{draft['status']}' status.")

    updated = submit_for_approval(draft_id, str(current_user.id))
    return {
        "draft": updated,
        "message": "Draft submitted for approval. Review in the Approvals queue.",
        "next_step": "GET /api/v1/approvals to see the pending approval.",
    }


@router.post("/drafts/{draft_id}/publish")
async def publish_draft(
    draft_id: str,
    payload: PublishRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Mark a campaign draft as published after the ad platform API call succeeded.

    This endpoint is called after:
    1. Approval was granted via the Approvals workflow
    2. The platform adapter successfully created the campaign
    3. The platform returned a campaign ID

    IMPORTANT: This endpoint records the publish event and updates the draft state.
    The actual API call to the ad platform happens in the adapter layer, not here.
    """
    draft = get_campaign_draft(draft_id)
    if not draft or draft["user_id"] != str(current_user.id):
        raise HTTPException(404, "Campaign draft not found.")
    if draft["status"] != "approved":
        raise HTTPException(
            409,
            f"Draft must be in 'approved' status to publish. Current status: '{draft['status']}'. "
            "Submit for approval first via POST /campaigns/drafts/{id}/submit.",
        )

    published = mark_published(draft_id, str(current_user.id), payload.platform_campaign_id)
    return {
        "draft": published,
        "message": f"Campaign published successfully. Platform campaign ID: {payload.platform_campaign_id}",
    }


@router.post("/reallocation", status_code=201)
async def propose_reallocation(
    payload: ReallocationCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Propose a budget reallocation decision.

    All reallocations are logged. If requires_approval=True, the decision
    goes into the approval queue before being applied.

    Safety rules:
    - Maximum single reallocation: +/- 50% of current budget
    - Minimum sample size: 100 impressions before reallocation
    - Floor/ceiling enforced by adapter layer
    """
    budget_change_pct = (
        abs(payload.new_budget_usd - payload.old_budget_usd) / max(payload.old_budget_usd, 1) * 100
    )
    if budget_change_pct > 50:
        raise HTTPException(
            400,
            f"Budget change of {budget_change_pct:.0f}% exceeds the 50% single-reallocation safety limit. "
            "Make multiple smaller adjustments with measurement between each step.",
        )

    decision = create_reallocation_decision(
        user_id=str(current_user.id),
        platform=payload.platform,
        account_id=payload.account_id,
        campaign_id=payload.campaign_id,
        old_budget_usd=payload.old_budget_usd,
        new_budget_usd=payload.new_budget_usd,
        reason=payload.reason,
        supporting_metrics=payload.supporting_metrics,
        confidence=payload.confidence,
        requires_approval=payload.requires_approval,
        rollback_plan=payload.rollback_plan,
    )
    return {
        "decision": decision,
        "message": (
            "Reallocation decision submitted for approval."
            if payload.requires_approval
            else "Reallocation decision recorded and applied."
        ),
    }


@router.get("/reallocation")
async def list_reallocations(
    platform: str | None = Query(None),
    current_user=Depends(get_current_user),
) -> dict:
    """List budget reallocation decisions."""
    decisions = get_reallocation_decisions(str(current_user.id), platform=platform)
    return {"decisions": decisions, "total": len(decisions)}


@router.get("/audit-log")
async def audit_log(
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_user),
) -> dict:
    """Full campaign audit trail — every action is logged immutably."""
    entries = get_audit_log(str(current_user.id), limit=limit)
    return {
        "entries": entries,
        "total": len(entries),
        "note": "All campaign actions are logged immutably for compliance and rollback.",
    }


@router.get("/performance/{platform}")
async def pull_performance(
    platform: str,
    date_start: str | None = Query(None, description="YYYY-MM-DD"),
    date_end: str | None = Query(None, description="YYYY-MM-DD"),
    campaign_ids: str | None = Query(None, description="Comma-separated platform campaign IDs"),
    current_user=Depends(get_current_user),
) -> dict:
    """
    Pull live campaign performance metrics from the platform adapter.

    Fetches real metrics from the connected platform API:
      - Impressions, clicks, spend, CTR, CPM, CPC
      - Conversions, ROAS, CPA
      - Reach, frequency, video views

    Requires: platform must be at READ_REPORT stage (token + account linked).
    """
    if platform not in VALID_PLATFORMS:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    # Default date range: last 7 days
    end = date_end or datetime.utcnow().strftime("%Y-%m-%d")
    start = date_start or (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Get stored credentials
    cred_data = get_credential(str(current_user.id), platform)
    if not cred_data:
        raise HTTPException(
            403,
            detail={
                "message": f"No credentials found for {platform}. Connect the platform first.",
                "connect_url": f"POST /api/v1/ads-connectors/{platform}/auth-url",
            },
        )

    # Get linked accounts
    linked = get_linked_accounts(str(current_user.id), platform)
    if not linked:
        raise HTTPException(
            403,
            detail={
                "message": f"No ad account linked for {platform}. List accounts and link one.",
                "link_url": f"POST /api/v1/ads-connectors/{platform}/link-account",
            },
        )

    account_id = linked[0]["account_id"]

    # Build adapter credentials
    import os

    credentials = AdapterCredentials(
        platform=platform,
        access_token=cred_data.get("access_token"),
        refresh_token=cred_data.get("refresh_token"),
        client_id=os.environ.get(f"{platform.upper()}_CLIENT_ID"),
        client_secret=os.environ.get(f"{platform.upper()}_CLIENT_SECRET"),
        developer_token=os.environ.get("GOOGLE_DEVELOPER_TOKEN"),
        account_id=account_id,
    )

    adapter_class = ADAPTER_REGISTRY.get(platform)
    if not adapter_class:
        raise HTTPException(500, f"No adapter registered for {platform}")

    adapter = adapter_class(credentials, stage=AdapterCapabilityStage.READ_REPORT)

    # Build campaign_ids list
    ids = [c.strip() for c in campaign_ids.split(",")] if campaign_ids else []

    # If no specific campaign IDs, pull from all published drafts
    if not ids:
        all_drafts = get_campaign_drafts(
            str(current_user.id), platform=platform, status="published"
        )
        ids = [d["platform_campaign_id"] for d in all_drafts if d.get("platform_campaign_id")]

    if not ids:
        return {
            "platform": platform,
            "date_start": start,
            "date_end": end,
            "metrics": [],
            "note": "No published campaigns found for this platform. Publish a campaign first.",
        }

    try:
        metrics = adapter.pull_campaign_metrics(ids, start, end)
        serialized = []
        for m in metrics:
            serialized.append(
                {
                    "campaign_id": m.campaign_id,
                    "platform": m.platform,
                    "date": m.date,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "spend_usd": m.spend_usd,
                    "conversions": m.conversions,
                    "revenue_usd": m.revenue_usd,
                    "cpm_usd": m.cpm_usd,
                    "cpc_usd": m.cpc_usd,
                    "ctr_pct": m.ctr_pct,
                    "roas": m.roas,
                    "cpa_usd": m.cpa_usd,
                    "reach": m.reach,
                    "frequency": m.frequency,
                    "video_views": m.video_views,
                    "video_completion_rate": m.video_completion_rate,
                }
            )

        # Compute aggregates
        total_spend = sum(m.spend_usd for m in metrics)
        total_impressions = sum(m.impressions for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        total_revenue = sum(m.revenue_usd for m in metrics)

        return {
            "platform": platform,
            "date_start": start,
            "date_end": end,
            "metrics": serialized,
            "summary": {
                "total_campaigns": len(ids),
                "total_spend_usd": round(total_spend, 2),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "total_revenue_usd": round(total_revenue, 2),
                "blended_roas": round(total_revenue / total_spend, 3) if total_spend > 0 else 0,
                "blended_cpa": round(total_spend / total_conversions, 2)
                if total_conversions > 0
                else 0,
                "overall_ctr": round(total_clicks / total_impressions * 100, 3)
                if total_impressions > 0
                else 0,
            },
            "data_mode": "observed",
            "source": f"{platform}_api",
        }

    except NotImplementedError as e:
        raise HTTPException(
            501,
            detail={
                "message": f"{platform} performance pull is not yet implemented.",
                "detail": str(e),
            },
        )
    except Exception as e:
        logger.error("[campaigns] performance pull error platform=%s: %s", platform, e)
        raise HTTPException(
            502,
            detail={
                "message": f"Error pulling performance from {platform}: {str(e)[:200]}",
            },
        )


# ─── Promote My Site Wizard ───────────────────────────────────────────────────


class PromoteSiteRequest(BaseModel):
    landing_page_url: str
    objective: str = "traffic"  # traffic | awareness | leads | conversions
    platform: str = "meta"  # meta | google | tiktok | linkedin
    daily_budget_usd: float = Field(10.0, ge=1.0)
    target_audience_description: str | None = None
    niche: str | None = None


PROMOTE_SITE_AUDIENCES = {
    "meta": [
        {
            "name": "Lookalike — website visitors (1%)",
            "type": "lookalike",
            "estimated_size": "500K–1M",
        },
        {"name": "Interest-based — niche relevant", "type": "interest", "estimated_size": "2M–5M"},
        {
            "name": "Retargeting — past visitors",
            "type": "retargeting",
            "estimated_size": "depends on traffic",
        },
    ],
    "google": [
        {
            "name": "Search — branded keywords",
            "type": "search",
            "estimated_size": "depends on search volume",
        },
        {
            "name": "Search — competitor keywords",
            "type": "search",
            "estimated_size": "depends on search volume",
        },
        {"name": "Display — contextual targeting", "type": "display", "estimated_size": "5M–20M"},
    ],
    "tiktok": [
        {"name": "Interest — broad niche", "type": "interest", "estimated_size": "3M–10M"},
        {
            "name": "Custom audience — video viewers",
            "type": "custom",
            "estimated_size": "depends on views",
        },
        {"name": "Broad — TikTok algorithm optimized", "type": "broad", "estimated_size": "20M+"},
    ],
    "linkedin": [
        {
            "name": "Job title targeting — decision makers",
            "type": "job_title",
            "estimated_size": "500K–2M",
        },
        {"name": "Company size — SMB / Enterprise", "type": "company", "estimated_size": "1M–5M"},
        {"name": "Skill-based — niche professionals", "type": "skill", "estimated_size": "500K–3M"},
    ],
}

AD_COPY_ANGLES = {
    "traffic": [
        "Curiosity gap: 'The one thing about [topic] most people miss — see for yourself'",
        "Value hook: 'Free guide: how to [benefit] without [pain point]'",
        "Social proof: '[N] people already use this — you should too'",
    ],
    "awareness": [
        "Brand story: 'We built this because [relatable problem]'",
        "Mission-driven: 'Our mission is to [mission] — here's how we do it'",
        "Educational: 'Did you know [surprising fact about niche]?'",
    ],
    "leads": [
        "Lead magnet: 'Free [resource] — download now and [specific benefit]'",
        "Webinar/event: 'Join [N] people learning how to [achieve goal]'",
        "Quiz/assessment: 'Find out your [niche] score — takes 2 minutes'",
    ],
    "conversions": [
        "Urgency: 'Limited offer: [benefit] — ends [timeframe]'",
        "Testimonial: '[Customer name]: I got [result] in [timeframe] using this'",
        "ROI: 'Stop [losing X] — [product] helps you [gain Y]'",
    ],
}


@router.post("/promote-site")
async def promote_site_wizard(
    body: PromoteSiteRequest,
    current_user=Depends(get_current_user),
):
    """
    Promote My Site wizard — generates a campaign blueprint and immediately
    creates a draft campaign ready for review.

    Returns:
    - campaign_blueprint: full strategy and ad copy angles
    - recommended_audiences: platform-specific audiences
    - estimated_results: expected range based on budget
    - draft_campaign: the created campaign draft (in 'draft' status, no platform call made)
    """

    if body.platform not in VALID_PLATFORMS:
        body.platform = "meta"

    # Generate ad copy angles
    angles = AD_COPY_ANGLES.get(body.objective, AD_COPY_ANGLES["traffic"])
    audiences = PROMOTE_SITE_AUDIENCES.get(body.platform, PROMOTE_SITE_AUDIENCES["meta"])

    # Estimated results (rough model based on budget and objective)
    cpc_estimates = {"meta": 0.80, "google": 2.50, "tiktok": 0.50, "linkedin": 4.00}
    cpl_estimates = {"meta": 8.0, "google": 15.0, "tiktok": 5.0, "linkedin": 25.0}
    cpc = cpc_estimates.get(body.platform, 1.0)
    monthly_budget = body.daily_budget_usd * 30

    estimated_results = {
        "daily_budget_usd": body.daily_budget_usd,
        "monthly_budget_usd": round(monthly_budget, 2),
        "estimated_daily_clicks": f"{int(body.daily_budget_usd / cpc * 0.7)}–{int(body.daily_budget_usd / cpc * 1.3)}",
        "estimated_monthly_clicks": f"{int(monthly_budget / cpc * 0.7)}–{int(monthly_budget / cpc * 1.3)}",
        "estimated_cpc_usd": cpc,
        "note": "Estimates based on platform averages. Actual results vary by creative quality, audience, and landing page.",
    }
    if body.objective in ("leads", "conversions"):
        cpl = cpl_estimates.get(body.platform, 10.0)
        estimated_results["estimated_monthly_leads"] = (
            f"{int(monthly_budget / cpl * 0.5)}–{int(monthly_budget / cpl * 1.5)}"
        )
        estimated_results["estimated_cpl_usd"] = cpl

    # Create draft campaign
    campaign_name = f"{body.objective.title()} — {body.landing_page_url.split('//')[-1][:30]}"
    draft = create_campaign_draft(
        user_id=str(current_user.id),
        platform=body.platform,
        account_id=None,
        name=campaign_name,
        objective=body.objective if body.objective in VALID_OBJECTIVES else "traffic",
        daily_budget_usd=body.daily_budget_usd,
        start_date=None,
        end_date=None,
        target_audiences=[audiences[0]] if audiences else [],
        creatives=[
            {
                "type": "copy_angle",
                "headline": angles[0],
                "destination_url": body.landing_page_url,
            }
        ],
        notes=f"Created via Promote My Site wizard. Landing page: {body.landing_page_url}",
        strategy_version="promote_site_v1",
    )

    return {
        "campaign_blueprint": {
            "objective": body.objective,
            "platform": body.platform,
            "landing_page_url": body.landing_page_url,
            "daily_budget_usd": body.daily_budget_usd,
            "ad_copy_angles": angles,
            "recommended_audiences": audiences,
            "estimated_results": estimated_results,
        },
        "draft_campaign": draft,
        "next_steps": [
            "Review your campaign draft in Campaigns",
            "Pair ad copy with a creative (image or video)",
            f"Connect {body.platform.title()} Ads in Connections to enable publishing",
            "Submit for approval when ready to go live",
        ],
    }
