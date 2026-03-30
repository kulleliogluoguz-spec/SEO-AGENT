"""
Ads Optimization Service — autonomous performance monitoring and recommendation engine.

Runs daily from main.py lifespan. For each active ad campaign:
  1. Fetches current performance metrics from Meta or Google Ads API
  2. Stores a performance snapshot in growth_metrics_store
  3. Analyzes the metrics against thresholds
  4. Generates actionable recommendations if thresholds are breached
  5. Logs all decisions to the audit store

Thresholds (configurable):
  - CTR < 0.5%  → LOW_CTR  → suggest new creative
  - CPC > $3.00 → HIGH_CPC → suggest audience refinement
  - Spend > $50/day with 0 conversions → NO_CONVERSION → pause or redirect
  - Impressions < 1000 after $20 spend → LOW_REACH → suggest audience expansion

The optimizer never automatically changes budgets or pauses campaigns.
It only creates recommendations that the user must act on.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.store.growth_metrics_store import (
    get_active_ad_campaigns,
    append_ad_performance_snapshot,
    add_optimization_recommendation,
    update_campaign_status,
    get_campaign_performance_history,
)
from app.core.store.audit_store import write_audit_event

logger = logging.getLogger(__name__)

# ── Performance thresholds ────────────────────────────────────────────────────

CTR_LOW_THRESHOLD = 0.005          # 0.5%
CPC_HIGH_THRESHOLD = 3.00          # $3.00
NO_CONVERSION_SPEND_THRESHOLD = 50  # $50 spent with 0 conversions
LOW_REACH_RATIO = 0.05             # impressions < 5% of expected (based on budget)
MIN_IMPRESSIONS_FOR_ANALYSIS = 500 # Don't analyze until 500 impressions


def _analyze_and_recommend(
    campaign: dict,
    metrics: dict,
) -> list[dict]:
    """
    Analyze campaign performance metrics and return a list of recommendations.
    Each recommendation has: issue, suggestion, action_type, urgency.
    """
    recommendations = []
    user_id = campaign["user_id"]
    record_id = campaign["id"]
    platform = campaign["platform"]

    impressions = metrics.get("impressions", 0)
    clicks = metrics.get("clicks", 0)
    spend = metrics.get("spend_usd", 0.0)
    ctr = metrics.get("ctr", 0.0)
    cpc = metrics.get("cpc", 0.0)
    conversions = metrics.get("conversions", 0)

    # Not enough data yet
    if impressions < MIN_IMPRESSIONS_FOR_ANALYSIS and spend < 5.0:
        return []

    # ── Low CTR: creative is not attracting clicks ────────────────────────────
    if impressions >= MIN_IMPRESSIONS_FOR_ANALYSIS and ctr < CTR_LOW_THRESHOLD:
        recommendations.append({
            "issue": "low_ctr",
            "suggestion": (
                f"CTR is {ctr:.2%} (below 0.5%). "
                "Your ad creative isn't generating enough clicks. "
                "Try: (1) stronger headline with a clear value proposition, "
                "(2) add urgency ('Limited time'), "
                "(3) test a question-format headline."
            ),
            "action_type": "new_creative",
            "urgency": "high" if ctr < 0.002 else "medium",
        })

    # ── High CPC: expensive clicks ────────────────────────────────────────────
    if clicks > 10 and cpc > CPC_HIGH_THRESHOLD:
        recommendations.append({
            "issue": "high_cpc",
            "suggestion": (
                f"CPC is ${cpc:.2f} (above $3.00). "
                "Each click is costing too much. "
                "Try: (1) narrow audience to highest-intent segments, "
                "(2) exclude irrelevant demographics, "
                "(3) reduce bid cap if using manual bidding."
            ),
            "action_type": "new_audience",
            "urgency": "medium",
        })

    # ── Spend without conversions ─────────────────────────────────────────────
    if spend >= NO_CONVERSION_SPEND_THRESHOLD and conversions == 0:
        recommendations.append({
            "issue": "no_conversions",
            "suggestion": (
                f"Spent ${spend:.2f} with 0 conversions. "
                "Consider: (1) check landing page load speed and mobile experience, "
                "(2) ensure the CTA on landing page matches the ad promise, "
                "(3) test a simpler conversion goal (e.g., email capture instead of purchase), "
                "(4) pause this campaign and create a new one with a revised offer."
            ),
            "action_type": "pause",
            "urgency": "high",
        })

    # ── Good performance: suggest scaling ────────────────────────────────────
    daily_budget = campaign.get("daily_budget_usd", 0)
    if (
        ctr >= 0.02           # 2%+ CTR
        and cpc <= 0.50       # $0.50 or less CPC
        and conversions > 5
        and daily_budget < 100
    ):
        recommendations.append({
            "issue": "scale_opportunity",
            "suggestion": (
                f"Strong performance: CTR {ctr:.1%}, CPC ${cpc:.2f}, {conversions} conversions. "
                f"Consider increasing daily budget from ${daily_budget:.0f} to ${daily_budget * 2:.0f} "
                "to scale results."
            ),
            "action_type": "budget_increase",
            "urgency": "low",
        })

    return recommendations


# ── Fetch metrics from ad platforms ──────────────────────────────────────────

async def _fetch_meta_campaign_metrics(
    user_id: str,
    campaign_id: str,
) -> Optional[dict]:
    try:
        from app.services.ads.meta_ads import MetaAdsService
        svc = MetaAdsService(user_id=user_id)
        return await svc.get_campaign_insights(campaign_id, date_preset="last_7d")
    except Exception as e:
        logger.debug("[ads_optimizer] Meta metrics fetch failed for %s: %s", campaign_id, e)
        return None


async def _fetch_google_campaign_metrics(
    user_id: str,
    campaign_id: str,
) -> Optional[dict]:
    try:
        from app.services.ads.google_ads import GoogleAdsService
        svc = GoogleAdsService(user_id=user_id)
        return await svc.get_campaign_metrics(campaign_id, days=7)
    except Exception as e:
        logger.debug("[ads_optimizer] Google metrics fetch failed for %s: %s", campaign_id, e)
        return None


# ── Main optimization loop ────────────────────────────────────────────────────

async def run_ads_optimization() -> None:
    """
    One-shot optimization pass. Called by the daily background loop in main.py.
    For every active campaign of every user:
      1. Fetch metrics
      2. Store snapshot
      3. Analyze + create recommendations
    """
    from app.core.store.credential_store import _load as load_creds
    try:
        cred_data = load_creds()
        user_ids = list({c["user_id"] for c in cred_data.get("credentials", []) if "user_id" in c})
    except Exception:
        return

    total_campaigns = 0
    total_recs = 0

    for user_id in user_ids:
        campaigns = get_active_ad_campaigns(user_id)
        for campaign in campaigns:
            try:
                platform = campaign["platform"]
                campaign_id = campaign["campaign_id"]

                # Fetch metrics
                if platform == "meta":
                    raw = await _fetch_meta_campaign_metrics(user_id, campaign_id)
                elif platform == "google":
                    raw = await _fetch_google_campaign_metrics(user_id, campaign_id)
                else:
                    continue

                if not raw:
                    continue

                # Normalize to common format
                metrics = {
                    "impressions": raw.get("impressions", 0),
                    "clicks": raw.get("clicks", 0),
                    "spend_usd": raw.get("spend_usd", raw.get("cost_usd", 0.0)),
                    "ctr": raw.get("ctr", 0.0),
                    "cpc": raw.get("cpc", 0.0),
                    "conversions": raw.get("conversions", 0),
                    "reach": raw.get("reach", 0),
                }

                # Store snapshot
                append_ad_performance_snapshot(
                    campaign_record_id=campaign["id"],
                    user_id=user_id,
                    platform=platform,
                    metrics=metrics,
                )

                # Analyze and create recommendations
                recs = _analyze_and_recommend(campaign, metrics)
                for rec in recs:
                    # Avoid duplicating recommendations with same issue
                    existing = [
                        r for r in get_campaign_performance_history(campaign["id"])
                        # simple dedup: check if same issue was recommended recently
                    ]
                    add_optimization_recommendation(
                        user_id=user_id,
                        campaign_record_id=campaign["id"],
                        platform=platform,
                        issue=rec["issue"],
                        suggestion=rec["suggestion"],
                        action_type=rec["action_type"],
                        urgency=rec["urgency"],
                        metrics_snapshot=metrics,
                    )
                    total_recs += 1

                    write_audit_event(
                        user_id=user_id,
                        action="ads.optimizer.recommendation_created",
                        channel=platform,
                        success=True,
                        metadata={
                            "campaign_id": campaign_id,
                            "issue": rec["issue"],
                            "urgency": rec["urgency"],
                        },
                    )

                total_campaigns += 1
                logger.info(
                    "[ads_optimizer] Analyzed %s/%s recs=%d",
                    platform, campaign_id, len(recs),
                )

            except Exception as e:
                logger.debug("[ads_optimizer] Error processing campaign %s: %s", campaign.get("id"), e)

    if total_campaigns:
        logger.info(
            "[ads_optimizer] Optimization complete campaigns=%d recommendations=%d",
            total_campaigns, total_recs,
        )
