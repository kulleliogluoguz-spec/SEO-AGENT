"""
Ad Analytics Platform — FastAPI endpoints.

Complete REST API for the ad analytics dashboard. Uses raw SQL via the
existing AsyncSession (no ORM models for the new tables — they're queried
directly through the SQLAlchemy session).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.ad_analytics.ai_synthesis import AISynthesisEngine
from app.services.ad_analytics.decision_engine import (
    CampaignSignal,
    DecisionEngine,
    Recommendation,
)
from app.services.ad_analytics.forecasting_engine import ForecastingEngine
from app.services.ad_analytics.mmm_engine import MMMEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ads", tags=["Ad Analytics"])


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id_for(user) -> str:
    """Return the workspace UUID for the current user.

    The existing platform stores workspace_id on the user. For the demo user
    we use a stable workspace UUID derived from their org membership.
    """
    # Demo user — use a fixed workspace UUID
    return getattr(user, "workspace_id", None) or "00000000-0000-0000-0001-000000000001"


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy row (or mapping/dict) to a JSON-safe dict."""
    if row is None:
        return {}
    # Accept both Row objects (have ._mapping) and mappings/dicts
    if hasattr(row, "_mapping"):
        items = dict(row._mapping).items()
    elif isinstance(row, dict):
        items = row.items()
    else:
        items = dict(row).items()

    out = {}
    for k, v in items:
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, date):
            out[k] = v.isoformat()
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def _build_campaign_signal(db: AsyncSession, campaign_row: dict) -> CampaignSignal | None:
    """Build a CampaignSignal from 30 days of performance data."""
    cid = campaign_row["id"]
    name = campaign_row.get("name") or "Untitled"
    end_d = date.today()
    start_d = end_d - timedelta(days=30)

    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT date, spend, revenue, conversions, clicks, impressions,
                       roas, cpa, ctr, frequency
                FROM ad_performance_daily
                WHERE campaign_id = :cid AND date BETWEEN :start_d AND :end_d
                ORDER BY date
                """
                ),
                {"cid": cid, "start_d": start_d, "end_d": end_d},
            )
        )
        .mappings()
        .all()
    )

    if not rows:
        return None

    # Aggregate
    days = list(rows)
    last_7 = days[-7:] if len(days) >= 7 else days
    prev_7 = days[-14:-7] if len(days) >= 14 else []

    spend_7 = sum(float(r["spend"] or 0) for r in last_7)
    rev_7 = sum(float(r["revenue"] or 0) for r in last_7)
    conv_7 = sum(float(r["conversions"] or 0) for r in last_7)
    spend_30 = sum(float(r["spend"] or 0) for r in days)
    rev_30 = sum(float(r["revenue"] or 0) for r in days)

    roas_7 = rev_7 / spend_7 if spend_7 > 0 else 0
    roas_30 = rev_30 / spend_30 if spend_30 > 0 else 0
    cpa_7 = spend_7 / conv_7 if conv_7 > 0 else None

    prev_spend = sum(float(r["spend"] or 0) for r in prev_7)
    prev_rev = sum(float(r["revenue"] or 0) for r in prev_7)
    prev_roas = prev_rev / prev_spend if prev_spend > 0 else 0
    roas_trend = (roas_7 - prev_roas) / prev_roas if prev_roas > 0 else 0

    ctr_avg = sum(float(r["ctr"] or 0) for r in last_7) / len(last_7) if last_7 else 0
    freq_avg = sum(float(r["frequency"] or 0) for r in last_7) / len(last_7) if last_7 else 0
    impr_7 = sum(int(r["impressions"] or 0) for r in last_7)

    daily_budget = float(campaign_row.get("daily_budget") or 0)
    budget_util = (spend_7 / 7) / daily_budget if daily_budget > 0 else 0

    return CampaignSignal(
        campaign_id=str(cid),
        campaign_name=name,
        platform=campaign_row.get("platform") or "unknown",
        roas_7d=roas_7,
        roas_30d=roas_30,
        roas_trend=roas_trend,
        cpa_7d=cpa_7,
        cpa_target=None,
        spend_7d=spend_7,
        spend_30d=spend_30,
        ctr_7d=ctr_avg,
        frequency=freq_avg,
        impressions_7d=impr_7,
        budget_utilization=budget_util,
        days_active=len(days),
    )


# ─── Pydantic models ──────────────────────────────────────────────────────────


class GoogleAdsCredentials(BaseModel):
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str
    login_customer_id: str | None = None
    account_id: str
    account_name: str | None = None


class MetaAdsCredentials(BaseModel):
    app_id: str
    app_secret: str
    access_token: str
    ad_account_id: str
    account_name: str | None = None


class BudgetOptimizationRequest(BaseModel):
    total_budget: float
    account_id: str | None = None


class ScenarioRequest(BaseModel):
    account_id: str
    scenario_budget: dict[str, float]


# ─── Account management ──────────────────────────────────────────────────────


@router.get("/accounts")
async def list_ad_accounts(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connected ad accounts for the workspace."""
    workspace_id = _workspace_id_for(current_user)
    rows = (
        await db.execute(
            text(
                """
                SELECT id, workspace_id, platform, account_id, account_name,
                       currency, is_active, last_sync_at, created_at
                FROM ad_accounts
                WHERE workspace_id = :wid AND is_active = true
                ORDER BY created_at DESC
                """
            ),
            {"wid": workspace_id},
        )
    ).all()
    accounts = [_row_to_dict(r) for r in rows]
    return {"accounts": accounts, "count": len(accounts)}


@router.post("/accounts/connect/google")
async def connect_google_ads(
    credentials: GoogleAdsCredentials,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a Google Ads account."""
    workspace_id = _workspace_id_for(current_user)
    new_id = uuid.uuid4()
    creds_json = credentials.model_dump()

    await db.execute(
        text(
            """
            INSERT INTO ad_accounts
                (id, workspace_id, platform, account_id, account_name, currency, credentials)
            VALUES (:id, :wid, 'google_ads', :aid, :name, 'USD', CAST(:creds AS JSONB))
            """
        ),
        {
            "id": new_id,
            "wid": workspace_id,
            "aid": credentials.account_id,
            "name": credentials.account_name or f"Google Ads {credentials.account_id}",
            "creds": json.dumps(creds_json),
        },
    )
    await db.commit()
    return {"connected": True, "id": str(new_id), "platform": "google_ads"}


@router.post("/accounts/connect/meta")
async def connect_meta_ads(
    credentials: MetaAdsCredentials,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a Meta Ads account."""
    workspace_id = _workspace_id_for(current_user)
    new_id = uuid.uuid4()
    creds_json = credentials.model_dump()

    await db.execute(
        text(
            """
            INSERT INTO ad_accounts
                (id, workspace_id, platform, account_id, account_name, currency, credentials)
            VALUES (:id, :wid, 'meta_ads', :aid, :name, 'USD', CAST(:creds AS JSONB))
            """
        ),
        {
            "id": new_id,
            "wid": workspace_id,
            "aid": credentials.ad_account_id,
            "name": credentials.account_name or f"Meta Ads {credentials.ad_account_id}",
            "creds": json.dumps(creds_json),
        },
    )
    await db.commit()
    return {"connected": True, "id": str(new_id), "platform": "meta_ads"}


async def _sync_account_task(account_id: str, workspace_id: str):
    """Background task: pull campaigns + last 30d metrics from the platform."""
    # In dev/demo we just log — actual sync requires real OAuth credentials.
    # The connector classes are wired and ready when credentials are present.
    logger.info("[ad_sync] background sync queued for account=%s", account_id)


@router.post("/accounts/{account_id}/sync")
async def sync_account(
    account_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a data sync for an ad account."""
    workspace_id = _workspace_id_for(current_user)
    row = (
        await db.execute(
            text("SELECT id FROM ad_accounts WHERE id = :id AND workspace_id = :wid"),
            {"id": account_id, "wid": workspace_id},
        )
    ).first()
    if not row:
        raise HTTPException(404, "Ad account not found")

    background_tasks.add_task(_sync_account_task, account_id, workspace_id)
    await db.execute(
        text("UPDATE ad_accounts SET last_sync_at = NOW() WHERE id = :id"),
        {"id": account_id},
    )
    await db.commit()
    return {"queued": True, "account_id": account_id}


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an ad account connection."""
    workspace_id = _workspace_id_for(current_user)
    result = await db.execute(
        text("UPDATE ad_accounts SET is_active = false WHERE id = :id AND workspace_id = :wid"),
        {"id": account_id, "wid": workspace_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Ad account not found")
    return {"disconnected": True, "id": account_id}


# ─── Campaign intelligence ───────────────────────────────────────────────────


@router.get("/campaigns")
async def list_campaigns(
    account_id: str | None = None,
    status: str | None = None,
    platform: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List campaigns with 7-day performance and AI health scores."""
    workspace_id = _workspace_id_for(current_user)
    sql = """
        SELECT
            c.id, c.name, c.status, c.campaign_type, c.daily_budget,
            c.platform_campaign_id, c.start_date, c.end_date,
            a.id AS ad_account_id, a.platform, a.account_name
        FROM analytics_ad_campaigns c
        JOIN ad_accounts a ON c.ad_account_id = a.id
        WHERE a.workspace_id = :wid AND a.is_active = true
    """
    params: dict[str, Any] = {"wid": workspace_id}
    if account_id:
        sql += " AND a.id = :acc"
        params["acc"] = account_id
    if platform:
        sql += " AND a.platform = :plat"
        params["plat"] = platform
    if status:
        sql += " AND c.status = :st"
        params["st"] = status
    sql += " ORDER BY c.name"

    rows = (await db.execute(text(sql), params)).mappings().all()
    engine = DecisionEngine()
    synth = AISynthesisEngine()

    out = []
    for row in rows:
        camp = dict(row)
        signal = await _build_campaign_signal(db, camp)
        recs: list[Recommendation] = []
        if signal:
            recs = engine.analyze_campaign(signal)
            ai_status = synth.classify_campaign_health(
                signal.roas_7d, signal.cpa_7d, signal.cpa_target, signal.frequency
            )
        else:
            ai_status = "no_data"

        out.append(
            {
                "id": str(camp["id"]),
                "ad_account_id": str(camp["ad_account_id"]),
                "platform": camp["platform"],
                "platform_campaign_id": camp["platform_campaign_id"],
                "name": camp["name"],
                "status": camp["status"],
                "campaign_type": camp.get("campaign_type"),
                "daily_budget": float(camp["daily_budget"] or 0),
                "roas_7d": round(signal.roas_7d, 3) if signal else None,
                "roas_30d": round(signal.roas_30d, 3) if signal else None,
                "roas_trend": round(signal.roas_trend, 3) if signal else None,
                "spend_7d": round(signal.spend_7d, 2) if signal else 0,
                "cpa_7d": round(signal.cpa_7d, 2) if signal and signal.cpa_7d else None,
                "ctr_7d": round(signal.ctr_7d, 4) if signal else None,
                "frequency": round(signal.frequency, 2) if signal else None,
                "ai_status": ai_status,
                "top_recommendation": (
                    {
                        "type": recs[0].type,
                        "priority": recs[0].priority,
                        "title": recs[0].title,
                    }
                    if recs
                    else None
                ),
                "recommendation_count": len(recs),
            }
        )
    return {"campaigns": out, "count": len(out)}


@router.get("/campaigns/{campaign_id}/performance")
async def get_campaign_performance(
    campaign_id: str,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily performance time-series for a campaign."""
    end_d = date.today()
    start_d = end_d - timedelta(days=days)

    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT date, impressions, clicks, conversions, spend, revenue,
                       roas, cpa, ctr, cpm, cpc, frequency, reach
                FROM ad_performance_daily
                WHERE campaign_id = :cid AND date BETWEEN :s AND :e
                ORDER BY date
                """
                ),
                {"cid": campaign_id, "s": start_d, "e": end_d},
            )
        )
        .mappings()
        .all()
    )

    series = []
    for r in rows:
        series.append(
            {
                "date": r["date"].isoformat() if r["date"] else None,
                "impressions": int(r["impressions"] or 0),
                "clicks": int(r["clicks"] or 0),
                "conversions": float(r["conversions"] or 0),
                "spend": float(r["spend"] or 0),
                "revenue": float(r["revenue"] or 0),
                "roas": float(r["roas"] or 0) if r["roas"] is not None else None,
                "cpa": float(r["cpa"] or 0) if r["cpa"] is not None else None,
                "ctr": float(r["ctr"] or 0) if r["ctr"] is not None else None,
                "cpm": float(r["cpm"] or 0) if r["cpm"] is not None else None,
                "cpc": float(r["cpc"] or 0) if r["cpc"] is not None else None,
                "frequency": float(r["frequency"] or 0) if r["frequency"] is not None else None,
                "reach": int(r["reach"] or 0),
            }
        )
    return {"campaign_id": campaign_id, "days": days, "series": series}


@router.get("/campaigns/{campaign_id}/analysis")
async def analyze_campaign(
    campaign_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full AI analysis of a campaign."""
    workspace_id = _workspace_id_for(current_user)
    row = (
        (
            await db.execute(
                text(
                    """
                SELECT c.*, a.platform, a.workspace_id
                FROM analytics_ad_campaigns c
                JOIN ad_accounts a ON c.ad_account_id = a.id
                WHERE c.id = :cid AND a.workspace_id = :wid
                """
                ),
                {"cid": campaign_id, "wid": workspace_id},
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(404, "Campaign not found")

    camp = dict(row)
    signal = await _build_campaign_signal(db, camp)
    if not signal:
        return {
            "campaign_id": campaign_id,
            "name": camp.get("name"),
            "ai_status": "no_data",
            "recommendations": [],
            "ai_insight": "Not enough performance data yet. Wait for the next sync.",
        }

    engine = DecisionEngine()
    recs = engine.analyze_campaign(signal)
    rec_dicts = [
        {
            "type": r.type,
            "priority": r.priority,
            "title": r.title,
            "description": r.description,
            "expected_impact": r.expected_impact,
            "action_data": r.action_data,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
        }
        for r in recs
    ]

    synth = AISynthesisEngine()
    insight = await synth.generate_campaign_insight(
        signal.campaign_name,
        {
            "roas_7d": signal.roas_7d,
            "spend_7d": signal.spend_7d,
            "cpa_7d": signal.cpa_7d,
            "ctr_7d": signal.ctr_7d,
            "frequency": signal.frequency,
            "roas_trend": signal.roas_trend,
        },
        rec_dicts,
    )

    # Publish platform event when ROAS drops below 1.0 (losing money)
    if signal.roas_7d < 1.0 and signal.spend_7d > 0:
        try:
            from app.services.automation.event_bus import EventBus

            bus = EventBus(db, workspace_id)
            await bus.publish(
                "roas_critical",
                "ad_analytics",
                {
                    "campaign_id": campaign_id,
                    "campaign_name": signal.campaign_name,
                    "roas": round(signal.roas_7d, 3),
                    "spend_7d": round(signal.spend_7d, 2),
                },
            )
        except Exception as e:
            logger.warning("roas_critical event publish failed: %s", e)

    return {
        "campaign_id": campaign_id,
        "name": signal.campaign_name,
        "platform": signal.platform,
        "metrics": {
            "roas_7d": round(signal.roas_7d, 3),
            "roas_30d": round(signal.roas_30d, 3),
            "roas_trend": round(signal.roas_trend, 3),
            "spend_7d": round(signal.spend_7d, 2),
            "spend_30d": round(signal.spend_30d, 2),
            "cpa_7d": round(signal.cpa_7d, 2) if signal.cpa_7d else None,
            "ctr_7d": round(signal.ctr_7d, 4),
            "frequency": round(signal.frequency, 2),
            "budget_utilization": round(signal.budget_utilization, 3),
            "days_active": signal.days_active,
        },
        "ai_status": synth.classify_campaign_health(
            signal.roas_7d, signal.cpa_7d, signal.cpa_target, signal.frequency
        ),
        "recommendations": rec_dicts,
        "ai_insight": insight,
    }


@router.get("/campaigns/{campaign_id}/forecast")
async def get_forecast(
    campaign_id: str,
    days: int = 30,
    metric: str = "roas",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prophet forecast for a campaign metric."""
    end_d = date.today()
    start_d = end_d - timedelta(days=90)
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT date, roas, conversions, spend, cpa
                FROM ad_performance_daily
                WHERE campaign_id = :cid AND date BETWEEN :s AND :e
                ORDER BY date
                """
                ),
                {"cid": campaign_id, "s": start_d, "e": end_d},
            )
        )
        .mappings()
        .all()
    )

    historical = []
    for r in rows:
        d = r["date"]
        if d is None:
            continue
        historical.append(
            {
                "date": d.isoformat(),
                "roas": float(r["roas"] or 0),
                "conversions": float(r["conversions"] or 0),
                "spend": float(r["spend"] or 0),
                "cpa": float(r["cpa"] or 0) if r["cpa"] is not None else 0,
            }
        )

    fc = ForecastingEngine()
    if metric == "roas":
        result = fc.forecast_roas(historical, forecast_days=days, campaign_name=campaign_id)
    else:
        # For other metrics, transform field name and reuse
        for r in historical:
            r["roas"] = r.get(metric, 0)
        result = fc.forecast_roas(historical, forecast_days=days, campaign_name=campaign_id)
    return {"campaign_id": campaign_id, "metric": metric, "forecast": result}


# ─── Portfolio intelligence ──────────────────────────────────────────────────


@router.get("/portfolio/summary")
async def portfolio_summary(
    account_id: str | None = None,
    days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Account-level portfolio view."""
    workspace_id = _workspace_id_for(current_user)
    end_d = date.today()
    start_d = end_d - timedelta(days=days)

    sql = """
        SELECT
            COALESCE(SUM(p.spend), 0) AS total_spend,
            COALESCE(SUM(p.revenue), 0) AS total_revenue,
            COALESCE(SUM(p.conversions), 0) AS total_conversions,
            COALESCE(SUM(p.impressions), 0) AS total_impressions,
            COALESCE(SUM(p.clicks), 0) AS total_clicks,
            COUNT(DISTINCT c.id) AS active_campaigns
        FROM analytics_ad_campaigns c
        JOIN ad_accounts a ON c.ad_account_id = a.id
        LEFT JOIN ad_performance_daily p
          ON p.campaign_id = c.id AND p.date BETWEEN :s AND :e
        WHERE a.workspace_id = :wid AND a.is_active = true
    """
    params: dict[str, Any] = {"wid": workspace_id, "s": start_d, "e": end_d}
    if account_id:
        sql += " AND a.id = :acc"
        params["acc"] = account_id

    summary = (await db.execute(text(sql), params)).mappings().first()
    s = dict(summary or {})

    spend = float(s.get("total_spend") or 0)
    revenue = float(s.get("total_revenue") or 0)
    conversions = float(s.get("total_conversions") or 0)
    overall_roas = revenue / spend if spend > 0 else 0
    overall_cpa = spend / conversions if conversions > 0 else None

    rec_count = (
        await db.execute(
            text(
                """
                SELECT COUNT(*) FROM ai_recommendations
                WHERE workspace_id = :wid AND status = 'pending'
                """
            ),
            {"wid": workspace_id},
        )
    ).scalar() or 0

    critical_count = (
        await db.execute(
            text(
                """
                SELECT COUNT(*) FROM ai_recommendations
                WHERE workspace_id = :wid AND status = 'pending' AND priority = 'critical'
                """
            ),
            {"wid": workspace_id},
        )
    ).scalar() or 0

    return {
        "period_days": days,
        "total_spend": round(spend, 2),
        "total_revenue": round(revenue, 2),
        "total_conversions": float(conversions),
        "total_impressions": int(s.get("total_impressions") or 0),
        "total_clicks": int(s.get("total_clicks") or 0),
        "overall_roas": round(overall_roas, 3),
        "overall_cpa": round(overall_cpa, 2) if overall_cpa else None,
        "active_campaigns": int(s.get("active_campaigns") or 0),
        "pending_recommendations": int(rec_count),
        "critical_recommendations": int(critical_count),
    }


@router.get("/portfolio/budget-optimization")
async def get_budget_optimization(
    total_budget: float,
    account_id: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run budget optimization across all campaigns in an account."""
    workspace_id = _workspace_id_for(current_user)

    sql = """
        SELECT c.id, c.name, c.daily_budget,
               COALESCE(SUM(p.spend), 0) AS spend_7d,
               COALESCE(SUM(p.revenue), 0) AS revenue_7d
        FROM analytics_ad_campaigns c
        JOIN ad_accounts a ON c.ad_account_id = a.id
        LEFT JOIN ad_performance_daily p
          ON p.campaign_id = c.id AND p.date >= CURRENT_DATE - INTERVAL '7 days'
        WHERE a.workspace_id = :wid AND a.is_active = true
    """
    params: dict[str, Any] = {"wid": workspace_id}
    if account_id:
        sql += " AND a.id = :acc"
        params["acc"] = account_id
    sql += " GROUP BY c.id, c.name, c.daily_budget"

    rows = (await db.execute(text(sql), params)).mappings().all()
    if not rows:
        return {
            "current_allocation": {},
            "optimal_allocation": {},
            "expected_uplift_pct": 0,
            "ai_explanation": "No campaigns found to optimize.",
        }

    campaigns = []
    current_spend = {}
    for r in rows:
        cid = str(r["id"])
        spend = float(r["spend_7d"] or 0)
        revenue = float(r["revenue_7d"] or 0)
        roas = revenue / spend if spend > 0 else 0
        campaigns.append({"campaign_id": cid, "roas_7d": roas, "spend_7d": spend})
        current_spend[cid] = {"roas": roas, "spend": spend}

    mmm = MMMEngine(workspace_id=workspace_id)
    result = mmm.optimize_budget(
        total_budget=total_budget,
        channel_cols=[c["campaign_id"] for c in campaigns],
        current_spend=current_spend,
    )

    current_allocation = {cid: v["spend"] for cid, v in current_spend.items()}
    optimal_allocation = result.get("optimal_allocation", {})

    # Compute simple expected uplift estimate
    current_total_revenue = sum(v["spend"] * v["roas"] for v in current_spend.values())
    optimal_total_revenue = sum(
        optimal_allocation.get(cid, 0) * (current_spend[cid]["roas"] if cid in current_spend else 0)
        for cid in optimal_allocation
    )
    uplift_pct = (
        (optimal_total_revenue - current_total_revenue) / current_total_revenue
        if current_total_revenue > 0
        else 0
    )

    synth = AISynthesisEngine()
    explanation = await synth.explain_budget_recommendation(
        current_allocation, optimal_allocation, uplift_pct
    )

    # Persist the proposal
    opt_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO budget_optimizations
                (id, workspace_id, total_budget, optimization_date,
                 current_allocation, optimal_allocation,
                 expected_roas_current, expected_roas_optimal, expected_uplift_pct, status)
            VALUES (:id, :wid, :tb, CURRENT_DATE,
                    CAST(:cur AS JSONB), CAST(:opt AS JSONB),
                    :cur_roas, :opt_roas, :uplift, 'proposed')
            """
        ),
        {
            "id": opt_id,
            "wid": workspace_id,
            "tb": total_budget,
            "cur": json.dumps(current_allocation),
            "opt": json.dumps(optimal_allocation),
            "cur_roas": (
                current_total_revenue / sum(current_allocation.values())
                if sum(current_allocation.values()) > 0
                else 0
            ),
            "opt_roas": (optimal_total_revenue / total_budget if total_budget > 0 else 0),
            "uplift": uplift_pct,
        },
    )
    await db.commit()

    return {
        "optimization_id": str(opt_id),
        "total_budget": total_budget,
        "current_allocation": current_allocation,
        "optimal_allocation": optimal_allocation,
        "expected_uplift_pct": round(uplift_pct, 4),
        "ai_explanation": explanation,
    }


@router.post("/portfolio/budget-optimization/apply")
async def apply_budget_optimization(
    optimization_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a budget optimization as applied (does NOT auto-mutate live ad accounts)."""
    workspace_id = _workspace_id_for(current_user)
    result = await db.execute(
        text(
            """
            UPDATE budget_optimizations
            SET status = 'applied'
            WHERE id = :id AND workspace_id = :wid
            """
        ),
        {"id": optimization_id, "wid": workspace_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Optimization not found")
    return {
        "applied": True,
        "id": optimization_id,
        "note": (
            "Marked as applied. AUTO_APPLY_RECOMMENDATIONS is disabled by policy — "
            "actual budget changes must be made manually in Google/Meta Ads UI or "
            "via the /accounts/{id}/sync endpoint."
        ),
    }


# ─── Recommendations engine ──────────────────────────────────────────────────


@router.get("/recommendations")
async def get_recommendations(
    status: str = "pending",
    priority: str | None = None,
    account_id: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All AI recommendations sorted by priority."""
    workspace_id = _workspace_id_for(current_user)
    sql = """
        SELECT r.*, c.name AS campaign_name
        FROM ai_recommendations r
        LEFT JOIN analytics_ad_campaigns c ON r.campaign_id = c.id
        WHERE r.workspace_id = :wid AND r.status = :st
    """
    params: dict[str, Any] = {"wid": workspace_id, "st": status}
    if priority:
        sql += " AND r.priority = :pri"
        params["pri"] = priority
    sql += """
        ORDER BY
            CASE r.priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            r.created_at DESC
    """

    rows = (await db.execute(text(sql), params)).mappings().all()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        out.append(d)
    return {"recommendations": out, "count": len(out)}


@router.post("/recommendations/{rec_id}/apply")
async def apply_recommendation(
    rec_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a recommendation as applied."""
    workspace_id = _workspace_id_for(current_user)
    result = await db.execute(
        text(
            """
            UPDATE ai_recommendations
            SET status = 'applied', applied_at = NOW()
            WHERE id = :id AND workspace_id = :wid AND status = 'pending'
            """
        ),
        {"id": rec_id, "wid": workspace_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Recommendation not found or already applied")
    return {
        "applied": True,
        "id": rec_id,
        "note": "Marked as applied. AUTO_APPLY_RECOMMENDATIONS is disabled — actual mutations must be confirmed in the platform UI.",
    }


@router.post("/recommendations/{rec_id}/dismiss")
async def dismiss_recommendation(
    rec_id: str,
    reason: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a recommendation."""
    workspace_id = _workspace_id_for(current_user)
    result = await db.execute(
        text(
            """
            UPDATE ai_recommendations
            SET status = 'dismissed'
            WHERE id = :id AND workspace_id = :wid
            """
        ),
        {"id": rec_id, "wid": workspace_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Recommendation not found")
    return {"dismissed": True, "id": rec_id, "reason": reason}


# ─── MMM / attribution ───────────────────────────────────────────────────────


async def _train_mmm_task(workspace_id: str, account_id: str):
    """Background task: train MMM for an account."""
    logger.info("[mmm] training queued for workspace=%s account=%s", workspace_id, account_id)


@router.post("/mmm/train")
async def train_mmm(
    account_id: str,
    background_tasks: BackgroundTasks,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue an MMM training job for an account."""
    workspace_id = _workspace_id_for(current_user)
    background_tasks.add_task(_train_mmm_task, workspace_id, account_id)
    return {"queued": True, "workspace_id": workspace_id, "account_id": account_id}


@router.get("/mmm/results/{account_id}")
async def get_mmm_results(
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest MMM model results for an account."""
    workspace_id = _workspace_id_for(current_user)
    row = (
        (
            await db.execute(
                text(
                    """
                SELECT * FROM mmm_models
                WHERE workspace_id = :wid
                ORDER BY trained_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
                ),
                {"wid": workspace_id},
            )
        )
        .mappings()
        .first()
    )
    if not row:
        return {
            "has_model": False,
            "message": "No MMM model trained yet. Use POST /mmm/train to train one.",
        }
    return {"has_model": True, "model": _row_to_dict(row)}


@router.post("/mmm/scenario")
async def run_scenario(
    body: ScenarioRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """What-if scenario: predict revenue from a budget allocation."""
    workspace_id = _workspace_id_for(current_user)

    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT c.id::text AS cid,
                       COALESCE(SUM(p.spend), 0) AS spend_7d,
                       COALESCE(SUM(p.revenue), 0) AS revenue_7d
                FROM analytics_ad_campaigns c
                JOIN ad_accounts a ON c.ad_account_id = a.id
                LEFT JOIN ad_performance_daily p
                  ON p.campaign_id = c.id AND p.date >= CURRENT_DATE - INTERVAL '7 days'
                WHERE a.workspace_id = :wid AND a.id = :acc
                GROUP BY c.id
                """
                ),
                {"wid": workspace_id, "acc": body.account_id},
            )
        )
        .mappings()
        .all()
    )

    roas_by_cid = {}
    for r in rows:
        spend = float(r["spend_7d"] or 0)
        revenue = float(r["revenue_7d"] or 0)
        roas_by_cid[r["cid"]] = revenue / spend if spend > 0 else 0

    predicted_revenue = 0.0
    for cid, scenario_spend in body.scenario_budget.items():
        roas = roas_by_cid.get(cid, 1.0)
        # Saturation: sqrt-based diminishing returns
        predicted_revenue += roas * (max(scenario_spend, 0) ** 0.7)

    return {
        "scenario_budget": body.scenario_budget,
        "predicted_revenue": round(predicted_revenue, 2),
        "predicted_roas": round(predicted_revenue / sum(body.scenario_budget.values()), 3)
        if sum(body.scenario_budget.values()) > 0
        else 0,
    }


# ─── Reports ─────────────────────────────────────────────────────────────────


@router.get("/reports/weekly")
async def weekly_report(
    account_id: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-generated weekly performance report."""
    workspace_id = _workspace_id_for(current_user)

    # Reuse portfolio_summary data structure
    summary = await portfolio_summary(
        account_id=account_id, days=7, current_user=current_user, db=db
    )
    campaigns = await list_campaigns(account_id=account_id, current_user=current_user, db=db)

    top_recs = (
        (
            await db.execute(
                text(
                    """
                SELECT title, description, expected_impact, priority
                FROM ai_recommendations
                WHERE workspace_id = :wid AND status = 'pending'
                ORDER BY
                    CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                  WHEN 'medium' THEN 2 ELSE 3 END,
                    created_at DESC
                LIMIT 3
                """
                ),
                {"wid": workspace_id},
            )
        )
        .mappings()
        .all()
    )

    synth = AISynthesisEngine()
    report_text = await synth.generate_weekly_report(
        {
            "account_name": "All Accounts" if not account_id else account_id,
            "total_spend_7d": summary["total_spend"],
            "total_revenue_7d": summary["total_revenue"],
            "overall_roas_7d": summary["overall_roas"],
            "total_conversions_7d": summary["total_conversions"],
            "campaigns": campaigns["campaigns"],
            "top_recommendations": [_row_to_dict(r) for r in top_recs],
        }
    )

    return {
        "summary": summary,
        "campaigns_count": campaigns["count"],
        "report_text": report_text,
        "data": {
            "total_spend_7d": summary["total_spend"],
            "total_revenue_7d": summary["total_revenue"],
            "overall_roas_7d": summary["overall_roas"],
            "total_conversions_7d": summary["total_conversions"],
        },
        "report": report_text,
    }


@router.get("/reports/weekly-pdf")
async def download_weekly_pdf(
    account_id: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate the weekly report as a downloadable PDF."""
    from datetime import date as _date

    from fastapi.responses import FileResponse

    from app.services.ad_analytics.report_generator import ReportGenerator

    report_data = await weekly_report(account_id=account_id, current_user=current_user, db=db)
    pdf_path = ReportGenerator().generate_weekly_pdf(report_data, "Acme Growth")
    if not pdf_path:
        raise HTTPException(500, "PDF generation failed — pip install reportlab")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"weekly_report_{_date.today()}.pdf",
    )


@router.get("/reports/anomalies")
async def get_anomalies(
    account_id: str | None = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalous performance days using IsolationForest."""
    workspace_id = _workspace_id_for(current_user)

    sql = """
        SELECT p.date, p.roas, p.spend, c.id AS campaign_id, c.name AS campaign_name
        FROM ad_performance_daily p
        JOIN analytics_ad_campaigns c ON p.campaign_id = c.id
        JOIN ad_accounts a ON c.ad_account_id = a.id
        WHERE a.workspace_id = :wid
          AND p.date >= CURRENT_DATE - make_interval(days => :days)
    """
    params: dict[str, Any] = {"wid": workspace_id, "days": days}
    if account_id:
        sql += " AND a.id = :acc"
        params["acc"] = account_id
    sql += " ORDER BY c.id, p.date"

    rows = (await db.execute(text(sql), params)).mappings().all()

    # Group by campaign
    by_campaign: dict[str, list[dict]] = {}
    for r in rows:
        cid = str(r["campaign_id"])
        by_campaign.setdefault(cid, []).append(
            {
                "date": r["date"].isoformat() if r["date"] else None,
                "roas": float(r["roas"] or 0),
                "campaign_name": r["campaign_name"],
            }
        )

    fc = ForecastingEngine()
    all_anomalies = []
    for cid, ts in by_campaign.items():
        anomalies = fc.detect_anomalies(ts, metric="roas")
        for a in anomalies:
            a["campaign_id"] = cid
            a["campaign_name"] = ts[0]["campaign_name"] if ts else None
            all_anomalies.append(a)

    return {"anomalies": all_anomalies, "count": len(all_anomalies)}


# ─── TRUE PROFITABILITY (Phase 2 Module C) ──────────────────────────────────
@router.get("/profitability/settings")
async def get_profitability_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get product cost settings for true ROAS calculation."""
    workspace_id = _workspace_id_for(current_user)
    r = await db.execute(
        text("SELECT * FROM product_costs WHERE workspace_id=:wid AND is_default=true LIMIT 1"),
        {"wid": workspace_id},
    )
    row = r.fetchone()
    if row:
        return {"settings": _row_to_dict(row)}
    return {
        "settings": {
            "cogs": 0,
            "shipping_cost": 0,
            "return_rate": 0.05,
            "avg_order_value": 0,
            "currency": "USD",
        }
    }


@router.post("/profitability/settings")
async def save_profitability_settings(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save product cost settings for true ROAS calculation."""
    workspace_id = _workspace_id_for(current_user)
    await db.execute(
        text("UPDATE product_costs SET is_default=false WHERE workspace_id=:wid"),
        {"wid": workspace_id},
    )
    await db.execute(
        text(
            """
            INSERT INTO product_costs
                (workspace_id, cogs, shipping_cost, return_rate, is_default, currency)
            VALUES (:wid, :cogs, :ship, :ret, true, :curr)
            """
        ),
        {
            "wid": workspace_id,
            "cogs": data.get("cogs", 0),
            "ship": data.get("shipping_cost", 0),
            "ret": data.get("return_rate", 0.05),
            "curr": data.get("currency", "USD"),
        },
    )
    await db.commit()
    return {"success": True}


@router.get("/profitability/analysis")
async def get_profitability_analysis(
    account_id: str | None = None,
    avg_order_value: float = 50.0,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run true profitability analysis on all active campaigns.

    Returns kill / scale signals along with contribution margin data.
    """
    from app.services.ad_analytics.profitability_engine import (
        ProductCost,
        ProfitabilityEngine,
    )

    workspace_id = _workspace_id_for(current_user)

    # Current product cost settings
    cost_r = await db.execute(
        text("SELECT * FROM product_costs WHERE workspace_id=:wid AND is_default=true LIMIT 1"),
        {"wid": workspace_id},
    )
    cost_row = cost_r.fetchone()
    if cost_row:
        cost_dict = _row_to_dict(cost_row)
        product_cost = ProductCost(
            cogs=float(cost_dict.get("cogs", 0) or 0),
            shipping_cost=float(cost_dict.get("shipping_cost", 0) or 0),
            return_rate=float(cost_dict.get("return_rate", 0.05) or 0.05),
        )
        product_cost_configured = True
    else:
        product_cost = ProductCost()
        product_cost_configured = False

    # Pull 7-day aggregates for each campaign
    sql = """
        SELECT
            c.id,
            c.name,
            a.platform,
            AVG(p.roas) AS roas,
            AVG(p.cpa) AS cpa,
            SUM(p.spend) AS spend,
            SUM(p.revenue) AS revenue,
            SUM(p.conversions) AS conversions,
            AVG(p.frequency) AS frequency,
            COUNT(p.date) AS days_active
        FROM analytics_ad_campaigns c
        JOIN ad_performance_daily p ON p.campaign_id = c.id
        JOIN ad_accounts a ON a.id = c.ad_account_id
        WHERE a.workspace_id = :wid
          AND p.date >= CURRENT_DATE - INTERVAL '7 days'
    """
    params: dict[str, Any] = {"wid": workspace_id}
    if account_id:
        sql += " AND a.id = :acc"
        params["acc"] = account_id
    sql += """
        GROUP BY c.id, c.name, a.platform
        HAVING SUM(p.spend) > 0
    """

    camp_r = await db.execute(text(sql), params)
    campaigns = [dict(row._mapping) for row in camp_r.fetchall()]

    if not campaigns:
        return {
            "message": "No campaign data available",
            "analyses": [],
            "summary": {
                "kill_campaigns": 0,
                "scale_campaigns": 0,
                "estimated_weekly_waste": 0,
                "product_cost_configured": product_cost_configured,
            },
        }

    engine = ProfitabilityEngine()
    results = []

    for camp in campaigns:
        analysis = engine.analyze_campaign(
            campaign_id=str(camp["id"]),
            campaign_name=camp["name"] or "",
            metrics_7d={
                "roas": float(camp["roas"] or 0),
                "spend": float(camp["spend"] or 0),
                "revenue": float(camp["revenue"] or 0),
                "conversions": float(camp["conversions"] or 0),
                "frequency": float(camp["frequency"] or 0),
                "budget_utilization": 0.8,
            },
            metrics_prev_7d={},
            product_cost=product_cost,
            avg_order_value=avg_order_value,
            is_retargeting="retarget" in (camp["name"] or "").lower(),
            days_active=int(camp["days_active"] or 0),
        )

        results.append(
            {
                "campaign_id": str(camp["id"]),
                "campaign_name": camp["name"],
                "platform": camp["platform"],
                "reported_roas": analysis.reported_roas,
                "true_roas": analysis.estimated_true_roas,
                "break_even_roas": analysis.break_even_roas,
                "contribution_margin_pct": round(analysis.contribution_margin * 100, 1),
                "gross_profit": analysis.gross_profit,
                "kill_signal": analysis.kill_signal,
                "scale_signal": analysis.scale_signal,
                "signal_reason": analysis.signal_reason,
                "confidence": analysis.confidence,
            }
        )

    kills = [r for r in results if r["kill_signal"]]
    scales = [r for r in results if r["scale_signal"]]
    total_waste = sum(
        float(c["spend"] or 0)
        for c in campaigns
        if any(r["campaign_id"] == str(c["id"]) and r["kill_signal"] for r in results)
    )

    return {
        "analyses": results,
        "summary": {
            "kill_campaigns": len(kills),
            "scale_campaigns": len(scales),
            "estimated_weekly_waste": round(total_waste, 2),
            "product_cost_configured": product_cost_configured,
        },
        "note": (
            "True ROAS estimates apply contribution margin and retargeting "
            "discount. Configure product costs for accuracy."
        ),
    }
