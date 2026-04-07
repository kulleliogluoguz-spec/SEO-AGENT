"""
Ad analytics background jobs.

These functions are designed to be called from main.py's lifespan as
asyncio loops, matching the existing background-job pattern in this codebase.
We don't use APScheduler — the existing pattern uses asyncio.create_task with
sleep loops, and we follow the same convention for consistency.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ad_analytics.decision_engine import (
    CampaignSignal,
    DecisionEngine,
)
from app.services.ad_analytics.forecasting_engine import ForecastingEngine

logger = logging.getLogger(__name__)


async def sync_all_accounts(db: AsyncSession) -> dict:
    """
    Pull latest data from connected ad accounts.

    For each ad_account row, instantiate the appropriate connector
    (GoogleAdsConnector or MetaAdsConnector) and call sync_campaigns +
    get_performance_metrics for the last 7 days.
    """
    rows = (
        await db.execute(
            text(
                "SELECT id, workspace_id, platform, account_id, credentials "
                "FROM ad_accounts WHERE is_active = true"
            )
        )
    ).mappings().all()

    synced = 0
    failed = 0
    for row in rows:
        try:
            # Connector instantiation requires real OAuth creds. In dev we
            # only attempt to connect if creds are non-empty.
            creds = row.get("credentials") or {}
            if not creds:
                continue

            if row["platform"] == "google_ads":
                from app.services.connectors.google_ads_connector import (
                    GoogleAdsConnector,
                )

                connector = GoogleAdsConnector(creds)
                campaigns = connector.sync_campaigns(row["account_id"])
            elif row["platform"] == "meta_ads":
                from app.services.connectors.meta_ads_connector import (
                    MetaAdsConnector,
                )

                connector = MetaAdsConnector(creds)
                campaigns = connector.sync_campaigns()
            else:
                continue

            # Upsert campaigns
            for camp in campaigns:
                cid = uuid.uuid4()
                await db.execute(
                    text(
                        """
                        INSERT INTO analytics_ad_campaigns
                            (id, ad_account_id, platform_campaign_id, name,
                             status, daily_budget, last_synced_at)
                        VALUES (:id, :acc, :pcid, :name, :status, :budget, NOW())
                        ON CONFLICT (ad_account_id, platform_campaign_id)
                        DO UPDATE SET name = EXCLUDED.name,
                                      status = EXCLUDED.status,
                                      daily_budget = EXCLUDED.daily_budget,
                                      last_synced_at = NOW()
                        """
                    ),
                    {
                        "id": cid,
                        "acc": row["id"],
                        "pcid": camp.get("platform_campaign_id"),
                        "name": camp.get("name"),
                        "status": camp.get("status"),
                        "budget": camp.get("daily_budget", 0),
                    },
                )

            await db.execute(
                text("UPDATE ad_accounts SET last_sync_at = NOW() WHERE id = :id"),
                {"id": row["id"]},
            )
            await db.commit()
            synced += 1
        except Exception as e:
            logger.error("[ad_sync] account %s failed: %s", row["id"], e)
            failed += 1

    return {"synced": synced, "failed": failed, "total": len(rows)}


async def run_decision_engine(db: AsyncSession) -> dict:
    """
    Analyze every active campaign and write recommendations to the DB.
    """
    rows = (
        await db.execute(
            text(
                """
                SELECT c.id, c.name, c.daily_budget, c.platform_campaign_id,
                       a.workspace_id, a.platform
                FROM analytics_ad_campaigns c
                JOIN ad_accounts a ON c.ad_account_id = a.id
                WHERE a.is_active = true AND c.status IN ('ENABLED', 'ACTIVE', 'PAUSED')
                """
            )
        )
    ).mappings().all()

    engine = DecisionEngine()
    created = 0
    end_d = date.today()
    start_d = end_d - timedelta(days=30)

    for camp in rows:
        cid = camp["id"]
        # Build signal from performance data
        perf = (
            await db.execute(
                text(
                    """
                    SELECT date, spend, revenue, conversions, clicks, impressions,
                           roas, cpa, ctr, frequency
                    FROM ad_performance_daily
                    WHERE campaign_id = :cid AND date BETWEEN :s AND :e
                    ORDER BY date
                    """
                ),
                {"cid": cid, "s": start_d, "e": end_d},
            )
        ).mappings().all()

        if not perf:
            continue

        days = list(perf)
        last_7 = days[-7:] if len(days) >= 7 else days
        prev_7 = days[-14:-7] if len(days) >= 14 else []
        spend_7 = sum(float(r["spend"] or 0) for r in last_7)
        rev_7 = sum(float(r["revenue"] or 0) for r in last_7)
        conv_7 = sum(float(r["conversions"] or 0) for r in last_7)
        prev_spend = sum(float(r["spend"] or 0) for r in prev_7)
        prev_rev = sum(float(r["revenue"] or 0) for r in prev_7)
        roas_7 = rev_7 / spend_7 if spend_7 > 0 else 0
        prev_roas = prev_rev / prev_spend if prev_spend > 0 else 0
        roas_trend = (roas_7 - prev_roas) / prev_roas if prev_roas > 0 else 0
        spend_30 = sum(float(r["spend"] or 0) for r in days)
        rev_30 = sum(float(r["revenue"] or 0) for r in days)
        roas_30 = rev_30 / spend_30 if spend_30 > 0 else 0
        cpa_7 = spend_7 / conv_7 if conv_7 > 0 else None

        ctr_avg = (
            sum(float(r["ctr"] or 0) for r in last_7) / len(last_7) if last_7 else 0
        )
        freq_avg = (
            sum(float(r["frequency"] or 0) for r in last_7) / len(last_7)
            if last_7
            else 0
        )
        impr_7 = sum(int(r["impressions"] or 0) for r in last_7)

        budget = float(camp["daily_budget"] or 0)
        budget_util = (spend_7 / 7) / budget if budget > 0 else 0

        signal = CampaignSignal(
            campaign_id=str(cid),
            campaign_name=camp["name"],
            platform=camp["platform"],
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

        recs = engine.analyze_campaign(signal)
        for rec in recs:
            rid = uuid.uuid4()
            await db.execute(
                text(
                    """
                    INSERT INTO ai_recommendations
                        (id, workspace_id, campaign_id, recommendation_type,
                         priority, title, description, expected_impact,
                         action_data, ai_reasoning, confidence_score, status)
                    VALUES (:id, :wid, :cid, :rtype, :pri, :title, :desc,
                            :impact, CAST(:action AS JSONB), :reasoning, :conf, 'pending')
                    """
                ),
                {
                    "id": rid,
                    "wid": camp["workspace_id"],
                    "cid": cid,
                    "rtype": rec.type,
                    "pri": rec.priority,
                    "title": rec.title,
                    "desc": rec.description,
                    "impact": rec.expected_impact,
                    "action": __import__("json").dumps(rec.action_data),
                    "reasoning": rec.reasoning,
                    "conf": rec.confidence,
                },
            )
            created += 1
    await db.commit()
    return {"campaigns_analyzed": len(rows), "recommendations_created": created}


async def refresh_forecasts(db: AsyncSession) -> dict:
    """
    Generate Prophet forecasts for every campaign with 14+ days of data.
    Stores into ad_forecasts.
    """
    rows = (
        await db.execute(
            text(
                """
                SELECT c.id
                FROM analytics_ad_campaigns c
                JOIN ad_accounts a ON c.ad_account_id = a.id
                WHERE a.is_active = true
                """
            )
        )
    ).all()

    fc = ForecastingEngine()
    refreshed = 0
    for (cid,) in rows:
        perf = (
            await db.execute(
                text(
                    """
                    SELECT date, roas FROM ad_performance_daily
                    WHERE campaign_id = :cid
                    ORDER BY date
                    """
                ),
                {"cid": cid},
            )
        ).mappings().all()

        if len(perf) < 14:
            continue

        historical = [
            {"date": r["date"].isoformat(), "roas": float(r["roas"] or 0)}
            for r in perf
        ]
        result = fc.forecast_roas(historical, forecast_days=30)

        # Wipe old forecasts for this campaign
        await db.execute(
            text("DELETE FROM ad_forecasts WHERE campaign_id = :cid AND metric = 'roas'"),
            {"cid": cid},
        )
        for daily in result.get("daily_forecasts", []):
            await db.execute(
                text(
                    """
                    INSERT INTO ad_forecasts
                        (id, campaign_id, forecast_date, metric, predicted_value,
                         lower_bound, upper_bound, model_type)
                    VALUES (:id, :cid, :fd, 'roas', :pv, :lb, :ub, :mt)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "cid": cid,
                    "fd": daily["date"],
                    "pv": daily["predicted_roas"],
                    "lb": daily["lower_bound"],
                    "ub": daily["upper_bound"],
                    "mt": result.get("model", "prophet"),
                },
            )
        refreshed += 1
    await db.commit()
    return {"forecasts_refreshed": refreshed}
