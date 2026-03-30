"""
Google Ads API Adapter — Full Implementation using REST API.

Official API: https://developers.google.com/google-ads/api/docs/start
Uses the Google Ads REST API (no Python client library required).

Required:
  - OAuth2 client_id + client_secret (Google Cloud Console)
  - developer_token (apply at ads.google.com/home/tools/manager-accounts)
    Basic access: test accounts only
    Standard access: production accounts (1-2 week review)

OAuth2 scopes:
  - https://www.googleapis.com/auth/adwords

Campaign hierarchy:
  Customer → CampaignBudget → Campaign → AdGroup → AdGroupAd → Ad
  Budget uses micros: $10/day = 10_000_000 micros

GAQL (Google Ads Query Language):
  SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT ...
  Used for all reporting queries.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.adapters.base import (
    AdapterCapabilityStage,
    AdapterCredentials,
    AdapterStatus,
    AudienceDraft,
    BaseAdsAdapter,
    CampaignDraft,
    CampaignMetrics,
    CreativeDraft,
)

logger = logging.getLogger(__name__)

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_ADS_API_BASE = "https://googleads.googleapis.com"
GOOGLE_ADS_API_VERSION = "v17"

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class GoogleAdsAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class GoogleAdsAdapter(BaseAdsAdapter):
    """
    Google Ads API adapter using the REST interface.

    Supports:
      - Search ads (Responsive Search Ads)
      - Display ads
      - Video / YouTube ads
      - Performance Max campaigns
      - Demand Gen campaigns
    """

    PLATFORM = "google"
    DOCS_URL = "https://developers.google.com/google-ads/api/docs/start"
    REQUIRED_SCOPES = [GOOGLE_ADS_SCOPE]

    CAMPAIGN_TYPE_MAP = {
        "SEARCH": "SEARCH",
        "DISPLAY": "DISPLAY",
        "VIDEO": "VIDEO",
        "SHOPPING": "SHOPPING",
        "PERFORMANCE_MAX": "PERFORMANCE_MAX",
        "DEMAND_GEN": "DEMAND_GEN",
        # Normalize from our internal names
        "AWARENESS": "DISPLAY",
        "TRAFFIC": "SEARCH",
        "LEADS": "SEARCH",
        "SALES": "PERFORMANCE_MAX",
    }

    # ── Internal HTTP helpers ─────────────────────────────────────────────────

    def _headers(self) -> dict:
        """Build auth + developer token headers."""
        headers = {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "developer-token": self.credentials.developer_token or os.environ.get("GOOGLE_DEVELOPER_TOKEN", ""),
            "Content-Type": "application/json",
        }
        # If using a manager account, add login-customer-id
        login_cid = self.credentials.extra.get("login_customer_id")
        if login_cid:
            headers["login-customer-id"] = login_cid
        return headers

    def _api_url(self, path: str) -> str:
        return f"{GOOGLE_ADS_API_BASE}/{GOOGLE_ADS_API_VERSION}/{path.lstrip('/')}"

    def _gaql(self, customer_id: str, query: str) -> list[dict]:
        """Execute a GAQL query and return all rows."""
        url = self._api_url(f"customers/{customer_id}/googleAds:search")
        payload = {"query": query}

        all_rows = []
        next_page_token = None

        while True:
            if next_page_token:
                payload["pageToken"] = next_page_token

            try:
                resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
            except httpx.RequestError as e:
                raise GoogleAdsAPIError(f"Network error executing GAQL: {e}")

            if resp.status_code == 429:
                logger.warning("[google] Rate limited — waiting 60s")
                time.sleep(60)
                continue

            if resp.status_code not in (200, 201):
                try:
                    err = resp.json()
                    msg = err.get("error", {}).get("message", resp.text[:200])
                except Exception:
                    msg = resp.text[:200]
                raise GoogleAdsAPIError(f"Google Ads API error: {msg}", status_code=resp.status_code)

            data = resp.json()
            all_rows.extend(data.get("results", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return all_rows

    def _mutate(self, customer_id: str, resource: str, operations: list[dict]) -> dict:
        """Execute a mutate operation (create/update/remove)."""
        url = self._api_url(f"customers/{customer_id}/{resource}:mutate")
        payload = {"operations": operations}

        try:
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
        except httpx.RequestError as e:
            raise GoogleAdsAPIError(f"Network error on mutate {resource}: {e}")

        if resp.status_code not in (200, 201):
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", resp.text[:300])
                details = err.get("error", {}).get("details", [])
                # Extract Google Ads specific errors
                for detail in details:
                    for error in detail.get("errors", []):
                        msg += f" | {error.get('message', '')}"
            except Exception:
                msg = resp.text[:300]
            raise GoogleAdsAPIError(f"Mutate {resource} failed: {msg}", status_code=resp.status_code)

        return resp.json()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "scope": GOOGLE_ADS_SCOPE,
            "access_type": "offline",
            "response_type": "code",
            "state": state,
            "prompt": "consent",  # Required to receive refresh_token on every auth
        }
        return f"{GOOGLE_AUTH_BASE}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        """
        Exchange OAuth authorization code for access_token + refresh_token.
        Google tokens expire in 1 hour; refresh_token is permanent until revoked.
        """
        client_id = self.credentials.client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = self.credentials.client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")
        developer_token = os.environ.get("GOOGLE_DEVELOPER_TOKEN", "")

        if not client_id or not client_secret:
            raise GoogleAdsAPIError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set. "
                "Create credentials at console.cloud.google.com → APIs & Services → Credentials. "
                "Enable the Google Ads API. Apply for a developer token at "
                "ads.google.com/home/tools/manager-accounts."
            )

        try:
            resp = httpx.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }, timeout=_TIMEOUT)
            data = resp.json()
        except httpx.RequestError as e:
            raise GoogleAdsAPIError(f"Network error during token exchange: {e}")

        if "error" in data:
            raise GoogleAdsAPIError(
                f"Token exchange failed: {data.get('error_description', data.get('error'))}"
            )

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        if not access_token:
            raise GoogleAdsAPIError("No access_token in Google token exchange response")

        if not refresh_token:
            logger.warning(
                "[google] No refresh_token received — user may have already authorized this app. "
                "Add prompt=consent to auth URL to force a new grant."
            )

        self._log("exchange_code", status="success",
                  response_summary={"has_refresh_token": bool(refresh_token), "expires_in": expires_in})

        return AdapterCredentials(
            platform="google",
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            developer_token=developer_token,
            expires_at=expires_at,
        )

    def refresh_access_token(self) -> AdapterCredentials:
        """
        Use refresh_token to get a new access_token.
        Google access tokens expire after 1 hour.
        Schedule this job to run every 50 minutes.
        """
        client_id = self.credentials.client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = self.credentials.client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")

        if not self.credentials.refresh_token:
            raise GoogleAdsAPIError(
                "No refresh_token available. User must re-authorize to grant offline access."
            )

        try:
            resp = httpx.post(GOOGLE_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.credentials.refresh_token,
            }, timeout=_TIMEOUT)
            data = resp.json()
        except httpx.RequestError as e:
            raise GoogleAdsAPIError(f"Token refresh network error: {e}")

        if "error" in data:
            raise GoogleAdsAPIError(
                f"Token refresh failed: {data.get('error_description', data.get('error'))}"
            )

        access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        self._log("refresh_access_token", status="success",
                  response_summary={"expires_in": expires_in})

        return AdapterCredentials(
            platform="google",
            access_token=access_token,
            refresh_token=self.credentials.refresh_token,  # Refresh token doesn't change
            client_id=client_id,
            client_secret=client_secret,
            developer_token=self.credentials.developer_token,
            expires_at=expires_at,
        )

    def verify_credentials(self) -> AdapterStatus:
        """
        Call GET /customers:listAccessibleCustomers to verify the token is valid.
        Returns AUTH_VERIFIED if accessible customers are found.
        """
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED
        if not self.credentials.developer_token and not os.environ.get("GOOGLE_DEVELOPER_TOKEN"):
            return AdapterStatus.CREDENTIALS_SET  # Token present but no dev token

        if self.credentials.is_token_expired() and not self.credentials.refresh_token:
            return AdapterStatus.ERROR

        try:
            url = self._api_url("customers:listAccessibleCustomers")
            resp = httpx.get(url, headers=self._headers(), timeout=_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                self._log("verify_credentials", status="success",
                          response_summary={"customer_count": len(data.get("resourceNames", []))})
                return AdapterStatus.AUTH_VERIFIED
            return AdapterStatus.ERROR
        except Exception as e:
            logger.warning("[google] verify_credentials error: %s", e)
            return AdapterStatus.ERROR

    # ── Account ───────────────────────────────────────────────────────────────

    def list_ad_accounts(self) -> list[dict]:
        """
        GET /customers:listAccessibleCustomers
        Returns all customer IDs accessible with current credentials.
        Then fetches metadata for each customer.
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)

        url = self._api_url("customers:listAccessibleCustomers")
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=_TIMEOUT)
        except httpx.RequestError as e:
            raise GoogleAdsAPIError(f"Network error listing customers: {e}")

        if resp.status_code != 200:
            raise GoogleAdsAPIError(f"Failed to list customers: {resp.text[:200]}", resp.status_code)

        data = resp.json()
        resource_names = data.get("resourceNames", [])

        accounts = []
        for rn in resource_names[:20]:  # Limit to avoid quota exhaustion
            customer_id = rn.split("/")[-1]
            try:
                rows = self._gaql(customer_id,
                    "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
                    "customer.time_zone, customer.status, customer.manager "
                    "FROM customer LIMIT 1"
                )
                if rows:
                    c = rows[0].get("customer", {})
                    accounts.append({
                        "id": str(c.get("id", customer_id)),
                        "name": c.get("descriptiveName", f"Customer {customer_id}"),
                        "currency": c.get("currencyCode", "USD"),
                        "timezone": c.get("timeZone", "UTC"),
                        "status": c.get("status", "UNKNOWN"),
                        "is_manager": c.get("manager", False),
                    })
            except GoogleAdsAPIError as e:
                # Some accounts may not be accessible for GAQL
                accounts.append({
                    "id": customer_id,
                    "name": f"Customer {customer_id}",
                    "error": str(e),
                })

        self._log("list_ad_accounts", "account", None, "success",
                  response_summary={"count": len(accounts)})
        return accounts

    def get_account_info(self) -> dict:
        """Fetch customer details via GAQL."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account_id linked")

        rows = self._gaql(customer_id,
            "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
            "customer.time_zone, customer.status, customer.optimization_score "
            "FROM customer LIMIT 1"
        )
        if not rows:
            raise GoogleAdsAPIError(f"No data returned for customer {customer_id}")

        c = rows[0].get("customer", {})
        self._log("get_account_info", "account", customer_id, "success")
        return {
            "id": str(c.get("id")),
            "name": c.get("descriptiveName"),
            "currency": c.get("currencyCode"),
            "timezone": c.get("timeZone"),
            "status": c.get("status"),
            "optimization_score": c.get("optimizationScore"),
        }

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """GAQL SELECT from campaign table."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        where_clause = "WHERE campaign.status != 'REMOVED'"
        if status_filter:
            where_clause += f" AND campaign.status = '{status_filter}'"

        rows = self._gaql(customer_id, f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date
            FROM campaign
            {where_clause}
            ORDER BY campaign.name
            LIMIT 100
        """)

        campaigns = []
        for row in rows:
            c = row.get("campaign", {})
            b = row.get("campaignBudget", {})
            daily_micros = b.get("amountMicros", 0)
            campaigns.append({
                "id": str(c.get("id")),
                "name": c.get("name"),
                "status": c.get("status"),
                "type": c.get("advertisingChannelType"),
                "daily_budget_usd": round(int(daily_micros) / 1_000_000, 2),
                "start_date": c.get("startDate"),
                "end_date": c.get("endDate"),
                "platform": "google",
            })

        self._log("list_campaigns", "campaign", None, "success",
                  response_summary={"count": len(campaigns)})
        return campaigns

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        Create a campaign using CampaignBudget + Campaign mutate operations.
        Budget in micros: $10/day = 10_000_000 micros.
        Always creates with status=PAUSED.
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked — link a Google Ads customer first")

        # Step 1: Create campaign budget
        budget_micros = int(draft.budget_daily_usd * 1_000_000)
        budget_result = self._mutate(customer_id, "campaignBudgets", [{
            "create": {
                "name": f"{draft.name} Budget",
                "amountMicros": str(budget_micros),
                "deliveryMethod": "STANDARD",
            }
        }])

        budget_resource_name = budget_result.get("results", [{}])[0].get("resourceName", "")
        if not budget_resource_name:
            raise GoogleAdsAPIError("Failed to create campaign budget")

        # Step 2: Create campaign
        channel_type = self.CAMPAIGN_TYPE_MAP.get(draft.objective.upper(), "SEARCH")
        campaign_payload = {
            "name": draft.name,
            "status": "PAUSED",  # NEVER ACTIVE without approval
            "advertisingChannelType": channel_type,
            "campaignBudget": budget_resource_name,
            "startDate": (draft.start_date or datetime.utcnow().strftime("%Y%m%d")),
        }

        if draft.end_date:
            campaign_payload["endDate"] = draft.end_date

        # Add bidding strategy based on channel type
        if channel_type == "PERFORMANCE_MAX":
            campaign_payload["maximizeConversionValue"] = {}
        elif channel_type == "SEARCH":
            campaign_payload["targetCpa"] = {}
        else:
            campaign_payload["targetCpm"] = {}

        campaign_result = self._mutate(customer_id, "campaigns", [{"create": campaign_payload}])
        campaign_resource_name = campaign_result.get("results", [{}])[0].get("resourceName", "")
        campaign_id = campaign_resource_name.split("/")[-1] if campaign_resource_name else ""

        self._log("create_campaign", "campaign", campaign_id, "success",
                  request_summary={"name": draft.name, "channel": channel_type, "status": "PAUSED"},
                  response_summary={"resource_name": campaign_resource_name})

        return {
            "id": campaign_id,
            "resource_name": campaign_resource_name,
            "platform": "google",
            "status": "PAUSED",
            "channel_type": channel_type,
            "name": draft.name,
            "daily_budget_usd": draft.budget_daily_usd,
            "ads_manager_url": f"https://ads.google.com/aw/campaigns?campaignId={campaign_id}",
        }

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        """Update campaign status via mutate. ENABLED requires APPROVAL_GATE stage."""
        google_status = {"ACTIVE": "ENABLED", "PAUSED": "PAUSED", "DELETED": "REMOVED"}.get(status, status)
        if google_status == "ENABLED":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)

        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
        result = self._mutate(customer_id, "campaigns", [{
            "update": {"resourceName": resource_name, "status": google_status},
            "updateMask": "status",
        }])

        self._log("update_campaign_status", "campaign", campaign_id, "success",
                  request_summary={"status": google_status})
        return {"id": campaign_id, "status": google_status, "resource_name": resource_name}

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        """Update campaign budget via CampaignBudget mutate."""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        # First get the budget resource name from the campaign
        rows = self._gaql(customer_id,
            f"SELECT campaign.id, campaign_budget.resource_name FROM campaign "
            f"WHERE campaign.id = {campaign_id} LIMIT 1"
        )
        if not rows:
            raise GoogleAdsAPIError(f"Campaign {campaign_id} not found")

        budget_rn = rows[0].get("campaignBudget", {}).get("resourceName", "")
        if not budget_rn:
            raise GoogleAdsAPIError(f"No budget resource name found for campaign {campaign_id}")

        budget_micros = int(daily_budget_usd * 1_000_000)
        self._mutate(customer_id, "campaignBudgets", [{
            "update": {"resourceName": budget_rn, "amountMicros": str(budget_micros)},
            "updateMask": "amount_micros",
        }])

        self._log("update_campaign_budget", "campaign", campaign_id, "success",
                  request_summary={"daily_budget_usd": daily_budget_usd})
        return {"id": campaign_id, "daily_budget_usd": daily_budget_usd}

    # ── Audiences ─────────────────────────────────────────────────────────────

    def list_audiences(self) -> list[dict]:
        """GAQL SELECT from user_list."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        rows = self._gaql(customer_id,
            "SELECT user_list.id, user_list.name, user_list.membership_status, "
            "user_list.size_for_search, user_list.size_for_display, user_list.type "
            "FROM user_list WHERE user_list.membership_status = 'OPEN' LIMIT 100"
        )

        audiences = []
        for row in rows:
            ul = row.get("userList", {})
            audiences.append({
                "id": str(ul.get("id")),
                "name": ul.get("name"),
                "type": ul.get("type"),
                "size_search": ul.get("sizeForSearch"),
                "size_display": ul.get("sizeForDisplay"),
                "status": ul.get("membershipStatus"),
            })

        self._log("list_audiences", "audience", None, "success",
                  response_summary={"count": len(audiences)})
        return audiences

    def create_audience(self, draft: AudienceDraft) -> dict:
        """Create a UserList (Customer Match or Remarketing)."""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        payload = {
            "name": draft.name,
            "membershipLifeSpan": "30",
            "crmBasedUserList": {
                "uploadKeyType": "CONTACT_INFO",
                "dataSourceType": "FIRST_PARTY",
            },
        }

        result = self._mutate(customer_id, "userLists", [{"create": payload}])
        resource_name = result.get("results", [{}])[0].get("resourceName", "")
        list_id = resource_name.split("/")[-1] if resource_name else ""

        self._log("create_audience", "audience", list_id, "success",
                  request_summary={"name": draft.name})
        return {"id": list_id, "resource_name": resource_name, "name": draft.name}

    # ── Creatives ─────────────────────────────────────────────────────────────

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GAQL SELECT from ad_group_ad."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        where = "WHERE ad_group_ad.status != 'REMOVED'"
        if campaign_id:
            where += f" AND campaign.id = {campaign_id}"

        rows = self._gaql(customer_id, f"""
            SELECT ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.ad.type,
                   ad_group_ad.ad.final_urls, ad_group_ad.status
            FROM ad_group_ad {where} LIMIT 50
        """)

        creatives = []
        for row in rows:
            ad = row.get("adGroupAd", {}).get("ad", {})
            creatives.append({
                "id": str(ad.get("id")),
                "name": ad.get("name"),
                "type": ad.get("type"),
                "final_urls": ad.get("finalUrls", []),
                "status": row.get("adGroupAd", {}).get("status"),
            })

        self._log("list_creatives", "creative", None, "success",
                  response_summary={"count": len(creatives)})
        return creatives

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        Create a Responsive Search Ad (RSA) in a given ad group.
        Requires an existing ad_group_id in credentials.extra.
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        ad_group_id = draft.__dict__.get("ad_group_id") or self.credentials.extra.get("default_ad_group_id")
        if not ad_group_id:
            raise GoogleAdsAPIError(
                "ad_group_id required to create RSA. "
                "Create an AdGroup first and provide its ID."
            )

        ad_group_rn = f"customers/{customer_id}/adGroups/{ad_group_id}"

        # Build RSA with up to 15 headlines and 4 descriptions
        headlines = [{"text": draft.headline}]
        if hasattr(draft, "extra_headlines"):
            headlines.extend([{"text": h} for h in draft.extra_headlines[:14]])

        descriptions = [{"text": draft.body}]

        payload = {
            "adGroup": ad_group_rn,
            "status": "PAUSED",
            "ad": {
                "finalUrls": [draft.destination_url],
                "responsiveSearchAd": {
                    "headlines": headlines,
                    "descriptions": descriptions,
                    "path1": draft.name[:15] if draft.name else "",
                },
            },
        }

        result = self._mutate(customer_id, "adGroupAds", [{"create": payload}])
        resource_name = result.get("results", [{}])[0].get("resourceName", "")
        ad_id = resource_name.split("~")[-1] if resource_name else ""

        self._log("create_creative", "creative", ad_id, "success",
                  request_summary={"name": draft.name, "ad_group_id": ad_group_id})
        return {
            "id": ad_id,
            "resource_name": resource_name,
            "name": draft.name,
            "type": "RESPONSIVE_SEARCH_AD",
            "status": "PAUSED",
            "destination_url": draft.destination_url,
        }

    # ── Reporting ─────────────────────────────────────────────────────────────

    def pull_campaign_metrics(
        self,
        campaign_ids: list[str],
        date_start: str,
        date_end: str,
        breakdown: Optional[str] = None,
    ) -> list[CampaignMetrics]:
        """
        GAQL query for campaign-level metrics with date range filter.
        Dates must be in YYYY-MM-DD format.
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        id_list = ", ".join(campaign_ids)
        rows = self._gaql(customer_id, f"""
            SELECT
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversion_value,
                metrics.average_cpc,
                metrics.average_cpm,
                metrics.ctr,
                metrics.video_views,
                metrics.video_view_rate,
                metrics.average_frequency
            FROM campaign
            WHERE campaign.id IN ({id_list})
              AND segments.date BETWEEN '{date_start}' AND '{date_end}'
        """)

        metrics = []
        for row in rows:
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            cost_micros = int(m.get("costMicros", 0))
            spend = cost_micros / 1_000_000
            conversions = float(m.get("conversions", 0))
            revenue = float(m.get("conversionValue", 0))
            clicks = int(m.get("clicks", 0))
            impressions = int(m.get("impressions", 0))

            metrics.append(CampaignMetrics(
                campaign_id=str(c.get("id")),
                platform="google",
                date=date_start,
                impressions=impressions,
                clicks=clicks,
                spend_usd=round(spend, 4),
                conversions=int(conversions),
                revenue_usd=round(revenue, 2),
                cpm_usd=round(float(m.get("averageCpm", 0)) / 1_000_000, 4),
                cpc_usd=round(float(m.get("averageCpc", 0)) / 1_000_000, 4),
                ctr_pct=round(float(m.get("ctr", 0)) * 100, 4),
                roas=round(revenue / spend, 3) if spend > 0 else 0.0,
                cpa_usd=round(spend / conversions, 2) if conversions > 0 else 0.0,
                video_views=int(m.get("videoViews", 0)),
                video_completion_rate=round(float(m.get("videoViewRate", 0)), 4),
                raw=row,
            ))

        self._log("pull_campaign_metrics", "campaign", None, "success",
                  response_summary={"count": len(metrics), "date_range": f"{date_start}:{date_end}"})
        return metrics

    def pull_ad_metrics(
        self,
        ad_ids: list[str],
        date_start: str,
        date_end: str,
    ) -> list[CampaignMetrics]:
        """GAQL query for ad-level metrics."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        customer_id = self.credentials.account_id
        if not customer_id:
            raise GoogleAdsAPIError("No account linked")

        id_list = ", ".join(ad_ids)
        rows = self._gaql(customer_id, f"""
            SELECT ad_group_ad.ad.id, ad_group_ad.ad.name,
                   metrics.impressions, metrics.clicks, metrics.cost_micros,
                   metrics.conversions, metrics.conversion_value, metrics.ctr
            FROM ad_group_ad
            WHERE ad_group_ad.ad.id IN ({id_list})
              AND segments.date BETWEEN '{date_start}' AND '{date_end}'
        """)

        metrics = []
        for row in rows:
            ad = row.get("adGroupAd", {}).get("ad", {})
            m = row.get("metrics", {})
            cost_micros = int(m.get("costMicros", 0))
            spend = cost_micros / 1_000_000
            conversions = float(m.get("conversions", 0))
            revenue = float(m.get("conversionValue", 0))

            metrics.append(CampaignMetrics(
                campaign_id=str(ad.get("id", "")),
                platform="google",
                date=date_start,
                impressions=int(m.get("impressions", 0)),
                clicks=int(m.get("clicks", 0)),
                spend_usd=round(spend, 4),
                conversions=int(conversions),
                revenue_usd=round(revenue, 2),
                ctr_pct=round(float(m.get("ctr", 0)) * 100, 4),
                roas=round(revenue / spend, 3) if spend > 0 else 0.0,
                cpa_usd=round(spend / conversions, 2) if conversions > 0 else 0.0,
                raw=row,
            ))

        self._log("pull_ad_metrics", "ad", None, "success",
                  response_summary={"count": len(metrics)})
        return metrics
