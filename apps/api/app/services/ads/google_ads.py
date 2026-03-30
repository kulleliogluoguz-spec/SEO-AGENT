"""
Google Ads Service — Google Ads API v17

Uses httpx directly (avoids the heavy google-ads-python library dependency).
Implements OAuth 2.0 token refresh internally.

Supports:
  - Campaign creation (SEARCH, DISPLAY, PERFORMANCE_MAX)
  - Budget creation
  - Ad Group creation
  - Responsive Search Ad creation
  - Campaign metrics ingestion
  - Campaign pause / resume
  - Budget updates

Reference: https://developers.google.com/google-ads/api/docs/get-started/introduction

Environment:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET — OAuth app credentials
  GOOGLE_ADS_DEVELOPER_TOKEN — from Google Ads API Center
  Tokens stored in credential_store under platform="google_ads"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.config.settings import get_settings
from app.core.store.credential_store import get_credential, get_linked_accounts, store_credential
from app.core.store.audit_store import write_audit_event

logger = logging.getLogger(__name__)
settings = get_settings()

GOOGLE_ADS_API_BASE = "https://googleads.googleapis.com/v17"
GOOGLE_TOKEN_REFRESH_URL = "https://oauth2.googleapis.com/token"


@dataclass
class GoogleAdsResult:
    success: bool
    campaign_id: Optional[str] = None
    budget_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    ad_id: Optional[str] = None
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)


class GoogleAdsService:
    """
    Google Ads API client using REST/JSON interface.

    Usage:
        service = GoogleAdsService(user_id="user-123")
        result = await service.create_search_campaign(
            customer_id="1234567890",
            name="Brand Traffic",
            daily_budget_usd=20.0,
            landing_page_url="https://example.com",
            headlines=["Try Our Product", "Sign Up Today", "Free Trial"],
            descriptions=["Award-winning software", "Start for free today"],
            keywords=["brand software", "project management tool"],
        )
    """

    def __init__(self, user_id: str):
        self.user_id = user_id

    def _load_credentials(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (access_token, refresh_token, customer_id)."""
        cred = get_credential(self.user_id, "google_ads")
        if not cred:
            return None, None, None

        access_token = cred.get("access_token", "")
        refresh_token = cred.get("refresh_token", "")

        accounts = get_linked_accounts(self.user_id, "google_ads")
        if accounts:
            customer_id = accounts[0]["account_id"]
        else:
            extra_accounts = cred.get("extra", {}).get("ad_accounts", [])
            customer_id = extra_accounts[0]["customer_id"] if extra_accounts else None

        return access_token, refresh_token, customer_id

    async def _refresh_token_if_needed(self, refresh_token: str) -> Optional[str]:
        """Exchange refresh token for new access token."""
        if not refresh_token or not settings.google_client_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    GOOGLE_TOKEN_REFRESH_URL,
                    data={
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                if resp.status_code == 200:
                    new_token = resp.json().get("access_token")
                    # Update stored credential
                    if new_token:
                        cred = get_credential(self.user_id, "google_ads")
                        if cred:
                            store_credential(
                                user_id=self.user_id,
                                platform="google_ads",
                                access_token=new_token,
                                refresh_token=refresh_token,
                                scope=cred.get("scope", ""),
                                extra=cred.get("extra", {}),
                            )
                    return new_token
        except Exception as e:
            logger.debug("[google_ads] token refresh failed: %s", e)
        return None

    def _headers(self, access_token: str, customer_id: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "developer-token": settings.google_ads_developer_token,
            "login-customer-id": customer_id,
        }

    async def _api(self, method: str, path: str, access_token: str, customer_id: str, **kwargs) -> dict:
        url = f"{GOOGLE_ADS_API_BASE}/{path.lstrip('/')}"
        headers = self._headers(access_token, customer_id)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await getattr(client, method.lower())(url, headers=headers, **kwargs)

        if resp.status_code == 401:
            # Try to refresh token and retry once
            _, refresh_token, _ = self._load_credentials()
            new_token = await self._refresh_token_if_needed(refresh_token or "")
            if new_token:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await getattr(client, method.lower())(
                        url, headers=self._headers(new_token, customer_id), **kwargs
                    )

        if resp.status_code not in (200, 201):
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            raise RuntimeError(
                f"Google Ads API {resp.status_code}: "
                f"{error_data.get('error', {}).get('message', resp.text[:300])}"
            )

        return resp.json()

    async def check_connection(self) -> dict:
        """Validate Google Ads credentials."""
        access_token, refresh_token, customer_id = self._load_credentials()
        if not access_token:
            return {"connected": False, "reason": "No Google Ads credentials. Connect via Settings → Connections."}
        if not customer_id:
            return {"connected": False, "reason": "No Google Ads account linked. Complete Google connection flow."}
        if not settings.google_ads_developer_token:
            return {"connected": False, "reason": "GOOGLE_ADS_DEVELOPER_TOKEN not set in .env"}

        try:
            data = await self._api(
                "GET",
                f"customers/{customer_id}",
                access_token,
                customer_id,
            )
            return {
                "connected": True,
                "customer_id": customer_id,
                "account_name": data.get("descriptiveName", ""),
                "currency": data.get("currencyCode", "USD"),
            }
        except Exception as e:
            return {"connected": False, "reason": str(e)}

    async def create_search_campaign(
        self,
        *,
        name: str,
        daily_budget_usd: float,
        landing_page_url: str,
        headlines: list[str],
        descriptions: list[str],
        keywords: list[str],
        geo_target_names: Optional[list[str]] = None,
        customer_id: Optional[str] = None,
        start_paused: bool = True,
    ) -> GoogleAdsResult:
        """
        Create a full Google Search campaign.
        Campaign starts PAUSED for safety; call activate_campaign() to start spending.

        headlines: 3-15 strings, max 30 chars each
        descriptions: 2-4 strings, max 90 chars each
        keywords: list of keyword phrases (broad match by default)
        """
        access_token, refresh_token, default_customer_id = self._load_credentials()
        if not access_token:
            result = GoogleAdsResult(
                success=False,
                error="Google Ads not connected. Go to Connections and link your Google Ads account."
            )
            write_audit_event(
                user_id=self.user_id, action="ads.google.create_campaign",
                channel="google_ads", success=False,
                metadata={"error": result.error, "campaign_name": name},
            )
            return result

        cid = customer_id or default_customer_id
        if not cid:
            return GoogleAdsResult(success=False, error="No Google Ads customer ID found.")

        if not settings.google_ads_developer_token:
            return GoogleAdsResult(success=False, error="GOOGLE_ADS_DEVELOPER_TOKEN not configured.")

        budget_id = campaign_id = ad_group_id = ad_id = None

        try:
            # Step 1: Create Campaign Budget
            start_date = date.today().strftime("%Y%m%d")
            budget_payload = {
                "campaignBudgets": [{
                    "resourceName": f"customers/{cid}/campaignBudgets/-1",
                    "name": f"{name} Budget",
                    "amountMicros": str(int(daily_budget_usd * 1_000_000)),
                    "deliveryMethod": "STANDARD",
                }]
            }
            budget_resp = await self._api(
                "POST",
                f"customers/{cid}/campaignBudgets:mutate",
                access_token, cid,
                json=budget_payload,
            )
            budget_resource = budget_resp.get("results", [{}])[0].get("resourceName", "")
            budget_id = budget_resource.split("/")[-1]
            logger.info("[google_ads] budget created: %s", budget_resource)

            # Step 2: Create Campaign
            campaign_payload = {
                "campaigns": [{
                    "resourceName": f"customers/{cid}/campaigns/-1",
                    "name": name,
                    "advertisingChannelType": "SEARCH",
                    "campaignBudget": budget_resource,
                    "status": "PAUSED" if start_paused else "ENABLED",
                    "startDate": start_date,
                    "endDate": (date.today() + timedelta(days=30)).strftime("%Y%m%d"),
                    "manualCpc": {"enhancedCpcEnabled": True},
                    "targetSpend": {},
                    "networkSettings": {
                        "targetGoogleSearch": True,
                        "targetSearchNetwork": True,
                        "targetContentNetwork": False,
                    },
                    "urlExpansionOptOut": False,
                }]
            }
            camp_resp = await self._api(
                "POST",
                f"customers/{cid}/campaigns:mutate",
                access_token, cid,
                json=campaign_payload,
            )
            campaign_resource = camp_resp.get("results", [{}])[0].get("resourceName", "")
            campaign_id = campaign_resource.split("/")[-1]
            logger.info("[google_ads] campaign created: %s", campaign_resource)

            # Step 3: Create Ad Group
            ad_group_payload = {
                "adGroups": [{
                    "resourceName": f"customers/{cid}/adGroups/-1",
                    "name": f"{name} — Ad Group",
                    "campaign": campaign_resource,
                    "type": "SEARCH_STANDARD",
                    "status": "ENABLED",
                    "cpcBidMicros": str(int(2.0 * 1_000_000)),  # Default $2 CPC bid
                }]
            }
            ag_resp = await self._api(
                "POST",
                f"customers/{cid}/adGroups:mutate",
                access_token, cid,
                json=ad_group_payload,
            )
            ag_resource = ag_resp.get("results", [{}])[0].get("resourceName", "")
            ad_group_id = ag_resource.split("/")[-1]
            logger.info("[google_ads] ad group created: %s", ag_resource)

            # Step 4: Add keywords to ad group
            if keywords:
                kw_entries = []
                for kw in keywords[:20]:  # max 20 keywords per ad group
                    kw_entries.append({
                        "resourceName": f"customers/{cid}/adGroupCriteria/-1~-1",
                        "adGroup": ag_resource,
                        "status": "ENABLED",
                        "keyword": {
                            "text": kw[:80],  # Max 80 chars
                            "matchType": "BROAD",
                        },
                    })
                await self._api(
                    "POST",
                    f"customers/{cid}/adGroupCriteria:mutate",
                    access_token, cid,
                    json={"adGroupCriteria": kw_entries},
                )
                logger.info("[google_ads] %d keywords added", len(kw_entries))

            # Step 5: Create Responsive Search Ad
            # Headlines: 3–15 items, max 30 chars; Descriptions: 2–4, max 90 chars
            rsa_headlines = [
                {"text": h[:30], "pinnedField": None}
                for h in headlines[:15]
            ]
            rsa_descriptions = [
                {"text": d[:90], "pinnedField": None}
                for d in descriptions[:4]
            ]
            # Ensure minimum counts
            while len(rsa_headlines) < 3:
                rsa_headlines.append({"text": name[:30], "pinnedField": None})
            while len(rsa_descriptions) < 2:
                rsa_descriptions.append({"text": f"Learn more at {landing_page_url[:40]}", "pinnedField": None})

            ad_payload = {
                "adGroupAds": [{
                    "resourceName": f"customers/{cid}/adGroupAds/-1~-1",
                    "adGroup": ag_resource,
                    "status": "ENABLED",
                    "ad": {
                        "resourceName": f"customers/{cid}/ads/-1",
                        "responsiveSearchAd": {
                            "headlines": rsa_headlines,
                            "descriptions": rsa_descriptions,
                            "path1": "",
                            "path2": "",
                        },
                        "finalUrls": [landing_page_url],
                    },
                }]
            }
            ad_resp = await self._api(
                "POST",
                f"customers/{cid}/adGroupAds:mutate",
                access_token, cid,
                json=ad_payload,
            )
            ad_resource = ad_resp.get("results", [{}])[0].get("resourceName", "")
            ad_id = ad_resource.split("~")[-1] if "~" in ad_resource else ad_resource.split("/")[-1]
            logger.info("[google_ads] responsive search ad created: %s", ad_resource)

        except Exception as e:
            logger.error("[google_ads] create_search_campaign failed: %s", e)
            write_audit_event(
                user_id=self.user_id, action="ads.google.create_campaign",
                channel="google_ads", success=False,
                metadata={"error": str(e), "campaign_id": campaign_id, "customer_id": cid},
            )
            return GoogleAdsResult(success=False, error=str(e), campaign_id=campaign_id)

        write_audit_event(
            user_id=self.user_id, action="ads.google.create_campaign",
            channel="google_ads", success=True,
            metadata={
                "campaign_id": campaign_id,
                "budget_id": budget_id,
                "ad_group_id": ad_group_id,
                "ad_id": ad_id,
                "budget_usd": daily_budget_usd,
                "customer_id": cid,
            },
        )

        return GoogleAdsResult(
            success=True,
            campaign_id=campaign_id,
            budget_id=budget_id,
            ad_group_id=ad_group_id,
            ad_id=ad_id,
        )

    async def activate_campaign(self, campaign_id: str, customer_id: Optional[str] = None) -> bool:
        """Enable a paused campaign (starts spending)."""
        access_token, _, default_cid = self._load_credentials()
        cid = customer_id or default_cid
        if not access_token or not cid:
            return False
        try:
            await self._api(
                "POST",
                f"customers/{cid}/campaigns:mutate",
                access_token, cid,
                json={
                    "campaigns": [{
                        "resourceName": f"customers/{cid}/campaigns/{campaign_id}",
                        "status": "ENABLED",
                    }],
                    "updateMask": "status",
                },
            )
            write_audit_event(
                user_id=self.user_id, action="ads.google.activate_campaign",
                channel="google_ads", success=True,
                metadata={"campaign_id": campaign_id, "customer_id": cid},
            )
            return True
        except Exception as e:
            logger.error("[google_ads] activate_campaign failed: %s", e)
            return False

    async def pause_campaign(self, campaign_id: str, customer_id: Optional[str] = None) -> bool:
        """Pause a running campaign."""
        access_token, _, default_cid = self._load_credentials()
        cid = customer_id or default_cid
        if not access_token or not cid:
            return False
        try:
            await self._api(
                "POST",
                f"customers/{cid}/campaigns:mutate",
                access_token, cid,
                json={
                    "campaigns": [{
                        "resourceName": f"customers/{cid}/campaigns/{campaign_id}",
                        "status": "PAUSED",
                    }],
                    "updateMask": "status",
                },
            )
            write_audit_event(
                user_id=self.user_id, action="ads.google.pause_campaign",
                channel="google_ads", success=True,
                metadata={"campaign_id": campaign_id},
            )
            return True
        except Exception as e:
            logger.error("[google_ads] pause_campaign failed: %s", e)
            return False

    async def get_campaign_metrics(
        self,
        campaign_id: str,
        days: int = 7,
        customer_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Fetch campaign performance via Google Ads Query Language (GAQL)."""
        access_token, _, default_cid = self._load_credentials()
        cid = customer_id or default_cid
        if not access_token or not cid:
            return None

        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              campaign.status,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.ctr,
              metrics.average_cpc,
              metrics.conversions,
              metrics.all_conversions
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
              AND segments.date DURING LAST_{days}_DAYS
        """
        try:
            data = await self._api(
                "POST",
                f"customers/{cid}/googleAds:search",
                access_token, cid,
                json={"query": query.strip()},
            )
            rows = data.get("results", [])
            if not rows:
                return None

            row = rows[0]
            metrics = row.get("metrics", {})
            spend_usd = int(metrics.get("costMicros", 0)) / 1_000_000

            return {
                "campaign_id": campaign_id,
                "impressions": int(metrics.get("impressions", 0)),
                "clicks": int(metrics.get("clicks", 0)),
                "spend_usd": round(spend_usd, 2),
                "ctr": float(metrics.get("ctr", 0)),
                "avg_cpc": int(metrics.get("averageCpc", 0)) / 1_000_000,
                "conversions": float(metrics.get("conversions", 0)),
                "all_conversions": float(metrics.get("allConversions", 0)),
                "period_days": days,
            }
        except Exception as e:
            logger.debug("[google_ads] get_metrics failed: %s", e)
            return None

    async def update_daily_budget(
        self,
        budget_id: str,
        new_budget_usd: float,
        customer_id: Optional[str] = None,
    ) -> bool:
        """Update campaign daily budget."""
        access_token, _, default_cid = self._load_credentials()
        cid = customer_id or default_cid
        if not access_token or not cid:
            return False
        try:
            await self._api(
                "POST",
                f"customers/{cid}/campaignBudgets:mutate",
                access_token, cid,
                json={
                    "campaignBudgets": [{
                        "resourceName": f"customers/{cid}/campaignBudgets/{budget_id}",
                        "amountMicros": str(int(new_budget_usd * 1_000_000)),
                    }],
                    "updateMask": "amount_micros",
                },
            )
            write_audit_event(
                user_id=self.user_id, action="ads.google.update_budget",
                channel="google_ads", success=True,
                metadata={"budget_id": budget_id, "new_budget_usd": new_budget_usd},
            )
            return True
        except Exception as e:
            logger.error("[google_ads] update_budget failed: %s", e)
            return False
