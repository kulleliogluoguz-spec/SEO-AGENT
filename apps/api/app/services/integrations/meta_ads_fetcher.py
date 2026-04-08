"""
Meta Ads Data Fetcher

Fetches real campaign / adset / ad performance data from the Meta
Marketing API. Used by the integrations sync endpoint to upsert into
the analytics_ad_campaigns + ad_performance_daily tables.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)
META_GRAPH_URL = "https://graph.facebook.com/v19.0"


class MetaAdsFetcher:
    def __init__(self, access_token: str):
        self.token = access_token
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Authenticated GET against the Meta Graph API."""
        p = {"access_token": self.token}
        if params:
            p.update(params)
        try:
            r = self.session.get(f"{META_GRAPH_URL}/{endpoint}", params=p, timeout=60)
        except Exception as e:
            logger.error("Meta API request failed: %s", e)
            return {}
        if not r.ok:
            logger.error("Meta API error %s: %s", r.status_code, r.text[:200])
            return {}
        return r.json()

    def get_campaigns(self, account_id: str, limit: int = 100) -> list[dict]:
        """Fetch all campaigns for an ad account."""
        data = self._get(
            f"{account_id}/campaigns",
            {
                "fields": (
                    "id,name,status,objective,daily_budget,lifetime_budget,"
                    "created_time,updated_time"
                ),
                "limit": limit,
            },
        )
        campaigns = data.get("data", [])
        logger.info("Fetched %d campaigns from Meta account %s", len(campaigns), account_id)
        return campaigns

    def get_campaign_insights(
        self,
        campaign_id: str,
        date_from: date,
        date_to: date,
    ) -> dict:
        """
        Fetch performance metrics for a single campaign.

        Returns spend, impressions, clicks, conversions, revenue, ROAS,
        CPA, CTR, frequency.
        """
        data = self._get(
            f"{campaign_id}/insights",
            {
                "fields": (
                    "impressions,clicks,spend,reach,frequency,"
                    "actions,action_values,ctr,cpc,cpm,"
                    "cost_per_action_type,purchase_roas"
                ),
                "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
                "level": "campaign",
            },
        )
        rows = data.get("data", [])
        if not rows:
            return {}

        row = rows[0]
        spend = float(row.get("spend", 0) or 0)
        impressions = int(row.get("impressions", 0) or 0)
        clicks = int(row.get("clicks", 0) or 0)
        frequency = float(row.get("frequency", 0) or 0)
        ctr = float(row.get("ctr", 0) or 0)

        actions = row.get("actions", []) or []
        action_values = row.get("action_values", []) or []
        conversions = sum(
            float(a.get("value", 0) or 0)
            for a in actions
            if a.get("action_type") in ("purchase", "omni_purchase")
        )
        revenue = sum(
            float(a.get("value", 0) or 0)
            for a in action_values
            if a.get("action_type")
            in (
                "purchase",
                "omni_purchase",
                "offsite_conversion.fb_pixel_purchase",
            )
        )

        roas_data = row.get("purchase_roas", []) or []
        roas = (
            float(roas_data[0].get("value", 0) or 0)
            if roas_data
            else (revenue / spend if spend > 0 else 0)
        )
        cpa = spend / conversions if conversions > 0 else 0

        return {
            "campaign_id": campaign_id,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": revenue,
            "roas": round(roas, 4),
            "cpa": round(cpa, 2),
            "ctr": round(ctr, 4),
            "frequency": round(frequency, 2),
        }

    def get_account_summary(self, account_id: str, days: int = 7) -> dict:
        """Get account-level summary for the last N days."""
        date_to = date.today()
        date_from = date_to - timedelta(days=days)
        data = self._get(
            f"{account_id}/insights",
            {
                "fields": ("spend,impressions,clicks,actions,action_values,purchase_roas"),
                "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
                "level": "account",
            },
        )
        rows = data.get("data", [])
        if not rows:
            return {
                "account_id": account_id,
                "spend": 0,
                "revenue": 0,
                "roas": 0,
                "period_days": days,
            }

        row = rows[0]
        spend = float(row.get("spend", 0) or 0)
        action_values = row.get("action_values", []) or []
        revenue = sum(
            float(a.get("value", 0) or 0)
            for a in action_values
            if "purchase" in (a.get("action_type") or "")
        )
        roas_data = row.get("purchase_roas", []) or []
        roas = (
            float(roas_data[0].get("value", 0) or 0)
            if roas_data
            else (revenue / spend if spend > 0 else 0)
        )

        return {
            "account_id": account_id,
            "spend": spend,
            "revenue": revenue,
            "roas": round(roas, 4),
            "period_days": days,
        }

    def sync_all_campaigns(self, account_id: str, days: int = 7) -> list[dict]:
        """
        Full sync: fetch all campaigns + their insights for the last N days.
        Returns a list ready to upsert into analytics_ad_campaigns +
        ad_performance_daily.
        """
        campaigns = self.get_campaigns(account_id)
        date_to = date.today()
        date_from = date_to - timedelta(days=days)

        results: list[dict] = []
        for camp in campaigns:
            camp_id = camp.get("id")
            insights = self.get_campaign_insights(camp_id, date_from, date_to)
            results.append({"campaign": camp, "insights": insights})
        return results
