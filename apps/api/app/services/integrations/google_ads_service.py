"""
Google Ads Integration Service

Handles OAuth2 + data fetching from the Google Ads API. The
google-ads / google-auth-oauthlib SDKs are imported lazily so the
rest of the platform can boot without them installed.

Important: requires a Google Ads Developer Token, which is applied
for at ads.google.com → Tools → API Center.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.encryption import encrypt

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_DEVELOPER_TOKEN = os.getenv("GOOGLE_DEVELOPER_TOKEN", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/v1/integrations/google/callback",
)


class GoogleAdsOAuthService:
    def get_oauth_url(self, state: str) -> str:
        """Generate the Google OAuth2 authorization URL."""
        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError as e:
            raise RuntimeError(
                "google-auth-oauthlib is not installed. " "Run: pip install google-auth-oauthlib"
            ) from e

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=["https://www.googleapis.com/auth/adwords"],
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # force refresh token issuance
        )
        return auth_url

    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange the authorization code for access + refresh tokens."""
        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError as e:
            raise RuntimeError(
                "google-auth-oauthlib is not installed. " "Run: pip install google-auth-oauthlib"
            ) from e

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=["https://www.googleapis.com/auth/adwords"],
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "expiry": str(credentials.expiry) if credentials.expiry else None,
        }

    def get_accessible_customers(self, refresh_token: str) -> list[dict]:
        """List all Google Ads accounts accessible with this refresh token."""
        try:
            from google.ads.googleads.client import GoogleAdsClient
        except ImportError:
            logger.warning("google-ads SDK not installed; skipping accessible customer lookup")
            return []
        try:
            client = GoogleAdsClient.load_from_dict(
                {
                    "developer_token": GOOGLE_DEVELOPER_TOKEN,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "use_proto_plus": True,
                }
            )
            customer_service = client.get_service("CustomerService")
            response = customer_service.list_accessible_customers()
            customers: list[dict] = []
            for resource_name in response.resource_names:
                customer_id = resource_name.split("/")[-1]
                customers.append(
                    {
                        "customer_id": customer_id,
                        "account_name": f"Google Ads Account ({customer_id})",
                        "resource_name": resource_name,
                    }
                )
            return customers
        except Exception as e:
            logger.error("Google Ads accessible customers failed: %s", e)
            return []

    async def save_connection(
        self,
        db: AsyncSession,
        workspace_id: str,
        account_id: str,
        account_name: str,
        access_token: str,
        refresh_token: str,
    ) -> str:
        """Save a Google Ads connection with encrypted tokens."""
        result = await db.execute(
            text(
                """
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     access_token_enc, refresh_token_enc, is_active,
                     last_sync_status)
                VALUES (:wid, 'google', :aid, :aname, :atk, :rtk, true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    access_token_enc = EXCLUDED.access_token_enc,
                    refresh_token_enc = EXCLUDED.refresh_token_enc,
                    is_active = true,
                    connected_at = NOW()
                RETURNING id
                """
            ),
            {
                "wid": workspace_id,
                "aid": account_id,
                "aname": account_name,
                "atk": encrypt(access_token),
                "rtk": encrypt(refresh_token),
            },
        )
        conn_id = str(result.fetchone()[0])
        await db.commit()
        return conn_id


class GoogleAdsDataFetcher:
    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token

    def _get_client(self, customer_id: str | None = None):
        try:
            from google.ads.googleads.client import GoogleAdsClient
        except ImportError as e:
            raise RuntimeError(
                "google-ads SDK is not installed. Run: pip install google-ads"
            ) from e

        config = {
            "developer_token": GOOGLE_DEVELOPER_TOKEN,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": self.refresh_token,
            "use_proto_plus": True,
        }
        if customer_id:
            config["login_customer_id"] = customer_id
        return GoogleAdsClient.load_from_dict(config)

    def get_campaigns(self, customer_id: str) -> list[dict]:
        """Fetch all campaigns for a customer."""
        try:
            client = self._get_client(customer_id)
            ga_service = client.get_service("GoogleAdsService")
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.bidding_strategy_type,
                    campaign_budget.amount_micros
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                ORDER BY campaign.id
                LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            campaigns: list[dict] = []
            for row in response:
                camp = row.campaign
                budget = row.campaign_budget
                campaigns.append(
                    {
                        "id": str(camp.id),
                        "name": camp.name,
                        "status": camp.status.name,
                        "channel_type": camp.advertising_channel_type.name,
                        "daily_budget": (
                            budget.amount_micros / 1_000_000 if budget.amount_micros else 0
                        ),
                    }
                )
            return campaigns
        except Exception as e:
            logger.error("Google Ads campaigns fetch failed: %s", e)
            return []

    def get_campaign_performance(self, customer_id: str, days: int = 7) -> list[dict]:
        """Fetch campaign performance for the last N days."""
        try:
            client = self._get_client(customer_id)
            ga_service = client.get_service("GoogleAdsService")
            date_to = date.today()
            date_from = date_to - timedelta(days=days)

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_per_conversion
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                  AND segments.date BETWEEN '{date_from}' AND '{date_to}'
                ORDER BY metrics.cost_micros DESC
                LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            results: list[dict] = []
            for row in response:
                camp = row.campaign
                m = row.metrics
                spend = m.cost_micros / 1_000_000
                revenue = m.conversions_value
                roas = revenue / spend if spend > 0 else 0
                cpa = spend / m.conversions if m.conversions > 0 else 0

                results.append(
                    {
                        "campaign_id": str(camp.id),
                        "campaign_name": camp.name,
                        "spend": round(spend, 2),
                        "impressions": m.impressions,
                        "clicks": m.clicks,
                        "conversions": m.conversions,
                        "revenue": round(revenue, 2),
                        "roas": round(roas, 4),
                        "cpa": round(cpa, 2),
                        "ctr": round(m.ctr, 4),
                        "period_days": days,
                    }
                )
            return results
        except Exception as e:
            logger.error("Google Ads performance fetch failed: %s", e)
            return []
