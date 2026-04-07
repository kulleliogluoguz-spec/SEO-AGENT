"""
Google Ads API Connector
Fetches campaigns, ad groups, and performance metrics via the Google Ads API v17+.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class GoogleAdsConnector:
    """
    Google Ads API connector — handles OAuth, campaign sync, performance metrics,
    and budget mutations. Imports the SDK lazily so the module loads even if
    google-ads isn't installed.
    """

    def __init__(self, credentials: dict):
        """
        credentials = {
            "developer_token": "...",
            "client_id": "...",
            "client_secret": "...",
            "refresh_token": "...",
            "login_customer_id": "...",  # MCC account if applicable
        }
        """
        self.credentials = credentials
        self.client = self._build_client()

    def _build_client(self):
        try:
            from google.ads.googleads.client import GoogleAdsClient
        except ImportError as e:
            raise RuntimeError("google-ads SDK not installed. Run: pip install google-ads") from e

        config = {
            "developer_token": self.credentials["developer_token"],
            "client_id": self.credentials["client_id"],
            "client_secret": self.credentials["client_secret"],
            "refresh_token": self.credentials["refresh_token"],
            "use_proto_plus": True,
        }
        if self.credentials.get("login_customer_id"):
            config["login_customer_id"] = str(self.credentials["login_customer_id"])
        return GoogleAdsClient.load_from_dict(config)

    # ── Account discovery ─────────────────────────────────────────────────────

    def get_accessible_accounts(self) -> list[dict]:
        """List all ad accounts accessible with this credential."""
        customer_service = self.client.get_service("CustomerService")
        try:
            accessible = customer_service.list_accessible_customers()
        except Exception as e:
            logger.error("[google_ads] list_accessible_customers failed: %s", e)
            return []

        accounts = []
        for resource_name in accessible.resource_names:
            customer_id = resource_name.split("/")[-1]
            accounts.append({"account_id": customer_id, "resource_name": resource_name})
        return accounts

    # ── Campaign sync ─────────────────────────────────────────────────────────

    def sync_campaigns(self, customer_id: str) -> list[dict]:
        """Fetch all non-removed campaigns for an account."""
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.campaign_budget,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """
        try:
            response = ga_service.search(customer_id=customer_id, query=query)
        except Exception as e:
            logger.error("[google_ads] sync_campaigns failed for %s: %s", customer_id, e)
            return []

        campaigns = []
        for row in response:
            campaigns.append(
                {
                    "platform_campaign_id": str(row.campaign.id),
                    "name": row.campaign.name,
                    "status": row.campaign.status.name,
                    "campaign_type": row.campaign.advertising_channel_type.name,
                    "daily_budget": (row.campaign_budget.amount_micros or 0) / 1_000_000,
                    "start_date": row.campaign.start_date or None,
                    "end_date": row.campaign.end_date or None,
                }
            )
        return campaigns

    # ── Performance metrics ───────────────────────────────────────────────────

    def get_performance_metrics(
        self,
        customer_id: str,
        campaign_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch daily performance metrics for a campaign in [start_date, end_date]."""
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                segments.date,
                campaign.id,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc,
                metrics.average_cpm
            FROM campaign
            WHERE
                campaign.id = {int(campaign_id)}
                AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}'
                    AND '{end_date.strftime('%Y-%m-%d')}'
            ORDER BY segments.date
        """
        try:
            response = ga_service.search(customer_id=customer_id, query=query)
        except Exception as e:
            logger.error("[google_ads] get_performance_metrics failed: %s", e)
            return []

        metrics = []
        for row in response:
            spend = (row.metrics.cost_micros or 0) / 1_000_000
            revenue = float(row.metrics.conversions_value or 0)
            conversions = float(row.metrics.conversions or 0)
            metrics.append(
                {
                    "date": row.segments.date,
                    "impressions": int(row.metrics.impressions or 0),
                    "clicks": int(row.metrics.clicks or 0),
                    "conversions": conversions,
                    "spend": spend,
                    "revenue": revenue,
                    "roas": revenue / spend if spend > 0 else 0,
                    "cpa": spend / conversions if conversions > 0 else None,
                    "ctr": float(row.metrics.ctr or 0),
                    "cpc": (row.metrics.average_cpc or 0) / 1_000_000,
                    "cpm": (row.metrics.average_cpm or 0) / 1_000_000,
                }
            )
        return metrics

    def get_last_30_days_summary(self, customer_id: str) -> dict:
        """Account-level summary for last 30 days."""
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=30)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.conversions_value
            FROM customer
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """
        total = {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0.0,
            "spend": 0.0,
            "revenue": 0.0,
        }
        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            for row in response:
                total["impressions"] += int(row.metrics.impressions or 0)
                total["clicks"] += int(row.metrics.clicks or 0)
                total["conversions"] += float(row.metrics.conversions or 0)
                total["spend"] += (row.metrics.cost_micros or 0) / 1_000_000
                total["revenue"] += float(row.metrics.conversions_value or 0)
        except Exception as e:
            logger.error("[google_ads] summary failed: %s", e)

        total["roas"] = total["revenue"] / total["spend"] if total["spend"] > 0 else 0
        total["cpa"] = total["spend"] / total["conversions"] if total["conversions"] > 0 else None
        return total

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_campaign_budget(
        self, customer_id: str, campaign_budget_id: str, new_budget_usd: float
    ) -> bool:
        """Update a campaign's daily budget. Returns True on success."""
        try:
            from google.ads.googleads.errors import GoogleAdsException
        except ImportError:
            return False

        budget_service = self.client.get_service("CampaignBudgetService")
        op = self.client.get_type("CampaignBudgetOperation")
        budget = op.update
        budget.resource_name = f"customers/{customer_id}/campaignBudgets/{campaign_budget_id}"
        budget.amount_micros = int(new_budget_usd * 1_000_000)
        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        op.update_mask.CopyFrom(field_mask)

        try:
            budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[op])
            return True
        except GoogleAdsException as e:
            logger.error("[google_ads] update_campaign_budget failed: %s", e)
            return False
