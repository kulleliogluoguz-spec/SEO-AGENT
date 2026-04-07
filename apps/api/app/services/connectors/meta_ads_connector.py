"""
Meta (Facebook) Ads API Connector
Handles campaigns, ad sets, ads, and performance metrics via the Marketing API.
"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


class MetaAdsConnector:
    """
    Meta Ads API connector — syncs campaigns and fetches granular performance data.
    Imports SDK lazily so the module loads even when facebook-business is missing.
    """

    def __init__(self, credentials: dict):
        """
        credentials = {
            "app_id": "...",
            "app_secret": "...",
            "access_token": "...",
            "ad_account_id": "act_XXXXXXXXX",
        }
        """
        try:
            from facebook_business.adobjects.adaccount import AdAccount
            from facebook_business.api import FacebookAdsApi
        except ImportError as e:
            raise RuntimeError(
                "facebook-business SDK not installed. Run: pip install facebook-business"
            ) from e

        self.credentials = credentials
        FacebookAdsApi.init(
            credentials["app_id"],
            credentials["app_secret"],
            credentials["access_token"],
        )
        self.account = AdAccount(credentials["ad_account_id"])

    # ── Account info ──────────────────────────────────────────────────────────

    def get_account_info(self) -> dict:
        """Get ad account details (name, currency, balance, status)."""
        fields = ["id", "name", "currency", "account_status", "balance"]
        try:
            data = self.account.api_get(fields=fields)
            return dict(data)
        except Exception as e:
            logger.error("[meta_ads] get_account_info failed: %s", e)
            return {}

    # ── Campaign sync ─────────────────────────────────────────────────────────

    def sync_campaigns(self) -> list[dict]:
        """Fetch all active and paused campaigns."""
        from facebook_business.adobjects.campaign import Campaign

        fields = [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
            Campaign.Field.daily_budget,
            Campaign.Field.lifetime_budget,
            Campaign.Field.start_time,
            Campaign.Field.stop_time,
        ]
        params = {"effective_status": ["ACTIVE", "PAUSED"], "limit": 100}
        try:
            campaigns = self.account.get_campaigns(fields=fields, params=params)
        except Exception as e:
            logger.error("[meta_ads] sync_campaigns failed: %s", e)
            return []

        result = []
        for c in campaigns:
            result.append(
                {
                    "platform_campaign_id": c[Campaign.Field.id],
                    "name": c[Campaign.Field.name],
                    "status": c[Campaign.Field.status],
                    "objective": c.get(Campaign.Field.objective),
                    "daily_budget": float(c.get(Campaign.Field.daily_budget, 0)) / 100,
                    "lifetime_budget": float(c.get(Campaign.Field.lifetime_budget, 0))
                    / 100,
                    "start_time": c.get(Campaign.Field.start_time),
                    "stop_time": c.get(Campaign.Field.stop_time),
                }
            )
        return result

    # ── Performance metrics ───────────────────────────────────────────────────

    def get_performance_metrics(
        self,
        campaign_id: str,
        start_date: date,
        end_date: date,
        level: str = "campaign",
    ) -> list[dict]:
        """Fetch daily performance insights for a campaign."""
        from facebook_business.adobjects.adsinsights import AdsInsights

        insights_fields = [
            AdsInsights.Field.date_start,
            AdsInsights.Field.campaign_id,
            AdsInsights.Field.campaign_name,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
            AdsInsights.Field.spend,
            AdsInsights.Field.reach,
            AdsInsights.Field.frequency,
            AdsInsights.Field.ctr,
            AdsInsights.Field.cpc,
            AdsInsights.Field.cpm,
            AdsInsights.Field.actions,
            AdsInsights.Field.action_values,
        ]
        params = {
            "time_range": {
                "since": start_date.strftime("%Y-%m-%d"),
                "until": end_date.strftime("%Y-%m-%d"),
            },
            "time_increment": 1,
            "level": level,
            "filtering": [
                {"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}
            ],
        }
        try:
            insights = self.account.get_insights(fields=insights_fields, params=params)
        except Exception as e:
            logger.error("[meta_ads] get_performance_metrics failed: %s", e)
            return []

        result = []
        purchase_actions = {"purchase", "offsite_conversion.fb_pixel_purchase"}
        for raw in insights:
            row = dict(raw)
            spend = float(row.get("spend", 0))
            conversions = 0.0
            revenue = 0.0
            for action in row.get("actions") or []:
                if action.get("action_type") in purchase_actions:
                    conversions += float(action.get("value", 0))
            for av in row.get("action_values") or []:
                if av.get("action_type") in purchase_actions:
                    revenue += float(av.get("value", 0))
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            result.append(
                {
                    "date": row.get("date_start"),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "spend": spend,
                    "revenue": revenue,
                    "roas": revenue / spend if spend > 0 else 0,
                    "cpa": spend / conversions if conversions > 0 else None,
                    "ctr": float(row.get("ctr", 0)) / 100,
                    "cpc": float(row.get("cpc", 0)),
                    "cpm": float(row.get("cpm", 0)),
                    "reach": int(row.get("reach", 0)),
                    "frequency": float(row.get("frequency", 0)),
                }
            )
        return result

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> bool:
        """Update a campaign's daily budget. Returns True on success."""
        from facebook_business.adobjects.campaign import Campaign

        try:
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"daily_budget": int(daily_budget_usd * 100)})
            return True
        except Exception as e:
            logger.error("[meta_ads] update_campaign_budget failed: %s", e)
            return False
