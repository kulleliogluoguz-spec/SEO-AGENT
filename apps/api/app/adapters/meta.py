"""
Meta Marketing API Adapter — Full Implementation.

Official API: https://developers.facebook.com/docs/marketing-apis
Required app review scopes:
  - ads_management
  - ads_read
  - business_management
  - instagram_basic
  - pages_read_engagement

OAuth2 flow:
  1. Direct user to get_auth_url()
  2. User approves scopes in Meta Login dialog
  3. Exchange code via exchange_code()
  4. Immediately exchange for long-lived token (60-day expiry)
  5. Store access_token + account_id in credential_store

Rate limits:
  - Marketing API: 200 calls/hour per user token
  - Use httpx with retry on 429 (Retry-After header)

Campaign object hierarchy:
  AdAccount → Campaign → AdSet → Ad → Creative
"""
from __future__ import annotations

import json
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

META_GRAPH_BASE = "https://graph.facebook.com/v20.0"
META_AUTH_BASE = "https://www.facebook.com/v20.0/dialog/oauth"
META_TOKEN_URL = f"{META_GRAPH_BASE}/oauth/access_token"

# Timeout for API calls (seconds)
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class MetaAPIError(Exception):
    """Raised when the Meta Graph API returns an error response."""
    def __init__(self, message: str, code: int = 0, subcode: int = 0):
        self.api_code = code
        self.api_subcode = subcode
        super().__init__(message)


class MetaAdsAdapter(BaseAdsAdapter):
    """
    Meta Marketing API adapter (Facebook + Instagram ads).

    Supports:
      - Facebook Feed, Stories, Reels ads
      - Instagram Feed, Stories, Reels ads
      - Audience Network
      - Dynamic Product Ads (catalog required)
      - Lead Generation forms
      - Advantage+ shopping campaigns
    """

    PLATFORM = "meta"
    DOCS_URL = "https://developers.facebook.com/docs/marketing-apis"
    REQUIRED_SCOPES = [
        "ads_management",
        "ads_read",
        "business_management",
        "instagram_basic",
        "pages_read_engagement",
    ]

    OBJECTIVE_MAP = {
        "AWARENESS": "OUTCOME_AWARENESS",
        "TRAFFIC": "OUTCOME_TRAFFIC",
        "ENGAGEMENT": "OUTCOME_ENGAGEMENT",
        "LEADS": "OUTCOME_LEADS",
        "APP_PROMOTION": "OUTCOME_APP_PROMOTION",
        "SALES": "OUTCOME_SALES",
    }

    # ── Internal HTTP helpers ─────────────────────────────────────────────────

    def _token_params(self) -> dict:
        """Return base params dict with access_token for Graph API calls."""
        return {"access_token": self.credentials.access_token}

    def _get(self, path: str, params: Optional[dict] = None, retries: int = 2) -> dict:
        """
        Perform a GET request to the Graph API.
        Handles rate-limit (429) with exponential backoff.
        Raises MetaAPIError on Graph-level error responses.
        """
        url = f"{META_GRAPH_BASE}/{path.lstrip('/')}"
        request_params = {**self._token_params(), **(params or {})}

        for attempt in range(retries + 1):
            try:
                response = httpx.get(url, params=request_params, timeout=_TIMEOUT)
            except httpx.RequestError as e:
                raise MetaAPIError(f"Network error calling {path}: {e}")

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                logger.warning("[meta] Rate limited on %s — waiting %ss", path, wait)
                if attempt < retries:
                    time.sleep(min(wait, 120))
                    continue
                raise MetaAPIError(f"Rate limit exceeded on {path}", code=429)

            data = response.json()
            if "error" in data:
                err = data["error"]
                raise MetaAPIError(
                    err.get("message", "Unknown Meta API error"),
                    code=err.get("code", 0),
                    subcode=err.get("error_subcode", 0),
                )
            return data

        raise MetaAPIError(f"Failed after {retries} retries: {path}")

    def _post(self, path: str, data: Optional[dict] = None, retries: int = 1) -> dict:
        """
        Perform a POST request to the Graph API.
        """
        url = f"{META_GRAPH_BASE}/{path.lstrip('/')}"
        post_data = {**self._token_params(), **(data or {})}

        for attempt in range(retries + 1):
            try:
                response = httpx.post(url, data=post_data, timeout=_TIMEOUT)
            except httpx.RequestError as e:
                raise MetaAPIError(f"Network error posting to {path}: {e}")

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                if attempt < retries:
                    time.sleep(min(wait, 120))
                    continue
                raise MetaAPIError(f"Rate limit on POST {path}", code=429)

            data_resp = response.json()
            if "error" in data_resp:
                err = data_resp["error"]
                raise MetaAPIError(
                    err.get("message", "Unknown Meta API error"),
                    code=err.get("code", 0),
                    subcode=err.get("error_subcode", 0),
                )
            return data_resp

        raise MetaAPIError(f"POST failed after {retries} retries: {path}")

    # ── Auth ──────────────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(self.REQUIRED_SCOPES),
            "state": state,
            "response_type": "code",
        }
        return f"{META_AUTH_BASE}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        """
        Exchange OAuth authorization code for a short-lived token,
        then immediately extend to a long-lived token (60 days).

        Meta two-step token flow:
          Step 1: POST /oauth/access_token with code → short-lived token
          Step 2: POST /oauth/access_token?grant_type=fb_exchange_token → long-lived token
        """
        client_id = self.credentials.client_id or os.environ.get("META_CLIENT_ID", "")
        client_secret = self.credentials.client_secret or os.environ.get("META_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            raise MetaAPIError(
                "META_CLIENT_ID and META_CLIENT_SECRET must be set in environment. "
                "Create a Meta app at developers.facebook.com, add Marketing API product, "
                "and apply for ads_management scope."
            )

        # Step 1: Short-lived token
        try:
            r1 = httpx.post(META_TOKEN_URL, params={
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            }, timeout=_TIMEOUT)
            r1_data = r1.json()
        except httpx.RequestError as e:
            raise MetaAPIError(f"Network error during token exchange: {e}")

        if "error" in r1_data:
            raise MetaAPIError(
                r1_data["error"].get("message", "Token exchange failed"),
                code=r1_data["error"].get("code", 0),
            )

        short_lived_token = r1_data.get("access_token")
        if not short_lived_token:
            raise MetaAPIError("No access_token in Meta token exchange response")

        # Step 2: Long-lived token (60-day expiry)
        try:
            r2 = httpx.get(META_TOKEN_URL, params={
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "fb_exchange_token": short_lived_token,
            }, timeout=_TIMEOUT)
            r2_data = r2.json()
        except httpx.RequestError as e:
            # Fall back to short-lived token if extension fails
            logger.warning("[meta] Could not extend token to long-lived: %s", e)
            r2_data = r1_data

        if "error" in r2_data:
            # Use short-lived token as fallback
            logger.warning("[meta] Token extension failed: %s", r2_data["error"])
            r2_data = r1_data

        access_token = r2_data.get("access_token", short_lived_token)
        expires_in = r2_data.get("expires_in", 5184000)  # Default 60 days
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        self._log("exchange_code", status="success",
                  response_summary={"token_type": r2_data.get("token_type"), "expires_in": expires_in})

        return AdapterCredentials(
            platform="meta",
            access_token=access_token,
            client_id=client_id,
            client_secret=client_secret,
            expires_at=expires_at,
        )

    def refresh_access_token(self) -> AdapterCredentials:
        """
        Meta long-lived tokens are valid for 60 days.
        Refresh by calling fb_exchange_token with the current long-lived token.
        Schedule this job to run every 30 days.
        """
        client_id = self.credentials.client_id or os.environ.get("META_CLIENT_ID", "")
        client_secret = self.credentials.client_secret or os.environ.get("META_CLIENT_SECRET", "")

        if not self.credentials.access_token:
            raise MetaAPIError("No access token to refresh")

        try:
            r = httpx.get(META_TOKEN_URL, params={
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "fb_exchange_token": self.credentials.access_token,
            }, timeout=_TIMEOUT)
            data = r.json()
        except httpx.RequestError as e:
            raise MetaAPIError(f"Token refresh network error: {e}")

        if "error" in data:
            raise MetaAPIError(
                data["error"].get("message", "Token refresh failed"),
                code=data["error"].get("code", 0),
            )

        access_token = data["access_token"]
        expires_in = data.get("expires_in", 5184000)
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        self._log("refresh_access_token", status="success",
                  response_summary={"expires_in": expires_in})

        return AdapterCredentials(
            platform="meta",
            access_token=access_token,
            client_id=client_id,
            client_secret=client_secret,
            expires_at=expires_at,
        )

    def verify_credentials(self) -> AdapterStatus:
        """
        Call GET /me?fields=id,name to verify the access token is valid.
        Returns AUTH_VERIFIED on success, ERROR on invalid/expired token.
        """
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED

        if self.credentials.is_token_expired():
            return AdapterStatus.ERROR

        try:
            data = self._get("me", {"fields": "id,name"})
            self._log("verify_credentials", status="success",
                      response_summary={"user_id": data.get("id"), "name": data.get("name")})
            return AdapterStatus.AUTH_VERIFIED
        except MetaAPIError as e:
            if e.api_code in (190, 102, 2500):  # Token invalid/expired codes
                return AdapterStatus.ERROR
            logger.warning("[meta] verify_credentials unexpected error: %s", e)
            return AdapterStatus.ERROR

    # ── Account ───────────────────────────────────────────────────────────────

    def list_ad_accounts(self) -> list[dict]:
        """
        GET /me/adaccounts?fields=id,name,account_status,currency,timezone_name,spend_cap
        Returns all ad accounts accessible with the current user token.
        account_status: 1=ACTIVE, 2=DISABLED, 3=UNSETTLED, 7=PENDING_RISK_REVIEW
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        data = self._get("me/adaccounts", {
            "fields": "id,name,account_status,currency,timezone_name,spend_cap,balance",
            "limit": 50,
        })

        accounts = []
        for raw in data.get("data", []):
            accounts.append({
                "id": raw.get("id", "").replace("act_", ""),
                "raw_id": raw.get("id"),
                "name": raw.get("name", "Unnamed Account"),
                "currency": raw.get("currency", "USD"),
                "timezone": raw.get("timezone_name", "UTC"),
                "status": self._account_status_label(raw.get("account_status", 0)),
                "spend_cap": raw.get("spend_cap"),
                "balance": raw.get("balance"),
            })

        self._log("list_ad_accounts", "account", None, "success",
                  response_summary={"count": len(accounts)})
        return accounts

    def _account_status_label(self, status_code: int) -> str:
        return {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW",
                8: "PENDING_SETTLEMENT", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE",
                101: "CLOSED", 201: "ANY_ACTIVE", 202: "ANY_CLOSED"}.get(status_code, f"STATUS_{status_code}")

    def get_account_info(self) -> dict:
        """GET /act_{account_id}?fields=id,name,account_status,currency,spend_cap,balance"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account_id linked — call link_account first")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        data = self._get(act_id, {
            "fields": "id,name,account_status,currency,timezone_name,spend_cap,balance,funding_source_details"
        })

        self._log("get_account_info", "account", account_id, "success")
        return {
            "id": data.get("id", "").replace("act_", ""),
            "name": data.get("name"),
            "status": self._account_status_label(data.get("account_status", 0)),
            "currency": data.get("currency"),
            "timezone": data.get("timezone_name"),
            "spend_cap": data.get("spend_cap"),
            "balance": data.get("balance"),
            "funding_source": data.get("funding_source_details", {}).get("type"),
        }

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """
        GET /act_{account_id}/campaigns
        Fields: id, name, status, objective, daily_budget, lifetime_budget, start_time, stop_time
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        params = {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time,created_time",
            "limit": 100,
        }
        if status_filter:
            params["effective_status"] = f'["{status_filter}"]'

        data = self._get(f"{act_id}/campaigns", params)
        campaigns = []
        for raw in data.get("data", []):
            campaigns.append({
                "id": raw.get("id"),
                "name": raw.get("name"),
                "status": raw.get("status"),
                "objective": raw.get("objective"),
                "daily_budget_usd": round(int(raw.get("daily_budget", 0)) / 100, 2),
                "lifetime_budget_usd": round(int(raw.get("lifetime_budget", 0)) / 100, 2) if raw.get("lifetime_budget") else None,
                "start_time": raw.get("start_time"),
                "stop_time": raw.get("stop_time"),
                "created_time": raw.get("created_time"),
                "platform": "meta",
            })

        self._log("list_campaigns", "campaign", None, "success",
                  response_summary={"count": len(campaigns)})
        return campaigns

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        POST /act_{account_id}/campaigns
        Always creates with status=PAUSED. Never publishes without approval gate.

        Returns the created campaign ID and a link to the Ads Manager.
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked — link an ad account first")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        objective = self.OBJECTIVE_MAP.get(draft.objective.upper(), "OUTCOME_AWARENESS")

        payload = {
            "name": draft.name,
            "objective": objective,
            "status": "PAUSED",  # NEVER set to ACTIVE without approval
            "special_ad_categories": json.dumps(draft.special_ad_categories or []),
            "daily_budget": str(int(draft.budget_daily_usd * 100)),  # Cents
        }

        if draft.budget_lifetime_usd:
            # Remove daily_budget when using lifetime
            del payload["daily_budget"]
            payload["lifetime_budget"] = str(int(draft.budget_lifetime_usd * 100))

        if draft.start_date:
            payload["start_time"] = draft.start_date

        if draft.end_date:
            payload["stop_time"] = draft.end_date

        data = self._post(f"{act_id}/campaigns", payload)
        campaign_id = data.get("id")

        self._log("create_campaign", "campaign", campaign_id, "success",
                  request_summary={"name": draft.name, "objective": objective, "status": "PAUSED"},
                  response_summary={"campaign_id": campaign_id})

        return {
            "id": campaign_id,
            "platform": "meta",
            "status": "PAUSED",
            "objective": objective,
            "name": draft.name,
            "daily_budget_usd": draft.budget_daily_usd,
            "ads_manager_url": f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={account_id}&selected_campaign_ids={campaign_id}",
        }

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        """
        POST /{campaign_id} with status field.
        Publishing to ACTIVE requires stage >= APPROVAL_GATE.
        """
        if status == "ACTIVE":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)

        valid_statuses = {"ACTIVE", "PAUSED", "DELETED", "ARCHIVED"}
        if status not in valid_statuses:
            raise MetaAPIError(f"Invalid status '{status}'. Must be one of: {valid_statuses}")

        data = self._post(campaign_id, {"status": status})
        self._log("update_campaign_status", "campaign", campaign_id, "success",
                  request_summary={"status": status})
        return {"id": campaign_id, "status": status, "success": data.get("success", True)}

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        """POST /{campaign_id} with daily_budget in cents."""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        daily_budget_cents = str(int(daily_budget_usd * 100))
        data = self._post(campaign_id, {"daily_budget": daily_budget_cents})
        self._log("update_campaign_budget", "campaign", campaign_id, "success",
                  request_summary={"daily_budget_usd": daily_budget_usd})
        return {"id": campaign_id, "daily_budget_usd": daily_budget_usd, "success": data.get("success", True)}

    # ── Ad Sets ───────────────────────────────────────────────────────────────

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget_usd: float,
        targeting: dict,
        optimization_goal: str = "REACH",
        billing_event: str = "IMPRESSIONS",
        bid_amount_cents: Optional[int] = None,
    ) -> dict:
        """
        POST /act_{account_id}/adsets

        targeting dict format:
          {
            "age_min": 18, "age_max": 65,
            "genders": [1, 2],  # 1=male, 2=female
            "geo_locations": {"countries": ["US"]},
            "interests": [{"id": "6003139266461", "name": "Fashion"}]
          }
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id

        payload = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": str(int(daily_budget_usd * 100)),
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "targeting": json.dumps(targeting),
            "status": "PAUSED",
        }
        if bid_amount_cents:
            payload["bid_amount"] = str(bid_amount_cents)

        data = self._post(f"{act_id}/adsets", payload)
        ad_set_id = data.get("id")

        self._log("create_ad_set", "ad_set", ad_set_id, "success",
                  request_summary={"name": name, "campaign_id": campaign_id})
        return {"id": ad_set_id, "status": "PAUSED", "name": name}

    # ── Audiences ─────────────────────────────────────────────────────────────

    def list_audiences(self) -> list[dict]:
        """GET /act_{account_id}/customaudiences"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        data = self._get(f"{act_id}/customaudiences", {
            "fields": "id,name,subtype,approximate_count_lower_bound,approximate_count_upper_bound,description",
            "limit": 100,
        })

        audiences = []
        for raw in data.get("data", []):
            audiences.append({
                "id": raw.get("id"),
                "name": raw.get("name"),
                "type": raw.get("subtype"),
                "size_min": raw.get("approximate_count_lower_bound"),
                "size_max": raw.get("approximate_count_upper_bound"),
                "description": raw.get("description"),
            })

        self._log("list_audiences", "audience", None, "success",
                  response_summary={"count": len(audiences)})
        return audiences

    def create_audience(self, draft: AudienceDraft) -> dict:
        """POST /act_{account_id}/customaudiences"""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id

        if draft.audience_type == "LOOKALIKE":
            payload = {
                "name": draft.name,
                "subtype": "LOOKALIKE",
                "origin_audience_id": draft.lookalike_source_id,
                "lookalike_spec": json.dumps({
                    "type": "similarity",
                    "starting_ratio": 0,
                    "ratio": draft.lookalike_ratio,
                    "country": draft.geo_locations[0] if draft.geo_locations else "US",
                }),
            }
        else:
            # Saved audience / interest-based
            targeting = {}
            if draft.age_min:
                targeting["age_min"] = draft.age_min
            if draft.age_max:
                targeting["age_max"] = draft.age_max
            if draft.genders:
                gender_map = {"male": 1, "female": 2}
                targeting["genders"] = [gender_map.get(g, g) for g in draft.genders]
            if draft.geo_locations:
                targeting["geo_locations"] = {"countries": draft.geo_locations}
            if draft.interests:
                targeting["interests"] = [{"name": i} for i in draft.interests]

            payload = {
                "name": draft.name,
                "subtype": "CUSTOM",
                "description": f"Created via AI Growth OS — {draft.audience_type}",
                "targeting_spec": json.dumps(targeting),
            }

        data = self._post(f"{act_id}/customaudiences", payload)
        audience_id = data.get("id")

        self._log("create_audience", "audience", audience_id, "success",
                  request_summary={"name": draft.name, "type": draft.audience_type})
        return {"id": audience_id, "name": draft.name, "type": draft.audience_type}

    # ── Creatives ─────────────────────────────────────────────────────────────

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GET /act_{account_id}/adcreatives"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        data = self._get(f"{act_id}/adcreatives", {
            "fields": "id,name,title,body,image_url,thumbnail_url,effective_object_story_id",
            "limit": 50,
        })

        creatives = []
        for raw in data.get("data", []):
            creatives.append({
                "id": raw.get("id"),
                "name": raw.get("name"),
                "title": raw.get("title"),
                "body": raw.get("body"),
                "image_url": raw.get("image_url"),
                "thumbnail_url": raw.get("thumbnail_url"),
            })

        self._log("list_creatives", "creative", None, "success",
                  response_summary={"count": len(creatives)})
        return creatives

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        POST /act_{account_id}/adcreatives

        For link ads (most common):
          object_story_spec → link_data with message, link, image_hash, call_to_action

        For video ads:
          object_story_spec → video_data with video_id, title, image_hash, call_to_action
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id

        # Build object_story_spec for link ad
        link_data = {
            "message": draft.body,
            "link": draft.destination_url,
            "name": draft.headline,
            "call_to_action": {
                "type": draft.cta.upper().replace(" ", "_"),
                "value": {"link": draft.destination_url},
            },
        }
        if draft.media_urls:
            link_data["picture"] = draft.media_urls[0]

        # Use page_id from credentials extra if available
        page_id = self.credentials.extra.get("page_id", "")
        if not page_id:
            raise MetaAPIError(
                "page_id required to create ad creative. "
                "Set page_id in credentials.extra during account linking."
            )

        object_story_spec = {
            "page_id": page_id,
            "link_data": link_data,
        }

        payload = {
            "name": draft.name,
            "object_story_spec": json.dumps(object_story_spec),
        }

        data = self._post(f"{act_id}/adcreatives", payload)
        creative_id = data.get("id")

        self._log("create_creative", "creative", creative_id, "success",
                  request_summary={"name": draft.name, "cta": draft.cta})
        return {
            "id": creative_id,
            "name": draft.name,
            "headline": draft.headline,
            "cta": draft.cta,
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
        GET /act_{account_id}/insights with campaign_id filter.

        Fields pulled:
          impressions, clicks, spend, actions (conversions), action_values (revenue),
          reach, frequency, cpm, cpc, ctr, video_play_actions, video_p100_watched_actions
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id

        params = {
            "fields": ",".join([
                "campaign_id", "campaign_name", "impressions", "clicks", "spend",
                "reach", "frequency", "cpm", "cpc", "ctr",
                "actions", "action_values",
                "video_play_actions", "video_p100_watched_actions",
            ]),
            "time_range": json.dumps({"since": date_start, "until": date_end}),
            "level": "campaign",
            "filtering": json.dumps([{
                "field": "campaign.id",
                "operator": "IN",
                "value": campaign_ids,
            }]),
            "limit": 500,
        }
        if breakdown:
            params["breakdowns"] = breakdown

        data = self._get(f"{act_id}/insights", params)
        metrics = []
        for raw in data.get("data", []):
            # Extract conversion actions
            actions = {a["action_type"]: int(a.get("value", 0))
                       for a in raw.get("actions", [])}
            action_values = {a["action_type"]: float(a.get("value", 0))
                             for a in raw.get("action_values", [])}

            conversions = actions.get("offsite_conversion.fb_pixel_purchase", 0) or \
                          actions.get("lead", 0) or \
                          actions.get("complete_registration", 0)
            revenue = action_values.get("offsite_conversion.fb_pixel_purchase", 0.0)
            spend = float(raw.get("spend", 0))
            roas = round(revenue / spend, 3) if spend > 0 else 0.0
            cpa = round(spend / conversions, 2) if conversions > 0 else 0.0

            video_views = 0
            for va in raw.get("video_play_actions", []):
                if va.get("action_type") == "video_view":
                    video_views = int(va.get("value", 0))
            video_complete = 0
            for va in raw.get("video_p100_watched_actions", []):
                if va.get("action_type") == "video_view":
                    video_complete = int(va.get("value", 0))
            impressions = int(raw.get("impressions", 0))
            video_completion_rate = round(video_complete / impressions, 4) if impressions > 0 else 0.0

            metrics.append(CampaignMetrics(
                campaign_id=raw.get("campaign_id", ""),
                platform="meta",
                date=date_start,
                impressions=impressions,
                clicks=int(raw.get("clicks", 0)),
                spend_usd=spend,
                conversions=conversions,
                revenue_usd=revenue,
                cpm_usd=float(raw.get("cpm", 0)),
                cpc_usd=float(raw.get("cpc", 0)),
                ctr_pct=float(raw.get("ctr", 0)),
                roas=roas,
                cpa_usd=cpa,
                reach=int(raw.get("reach", 0)),
                frequency=float(raw.get("frequency", 0)),
                video_views=video_views,
                video_completion_rate=video_completion_rate,
                raw=raw,
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
        """Pull ad-level metrics from insights at 'ad' level."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        params = {
            "fields": "ad_id,ad_name,impressions,clicks,spend,reach,cpm,cpc,ctr,actions,action_values",
            "time_range": json.dumps({"since": date_start, "until": date_end}),
            "level": "ad",
            "filtering": json.dumps([{
                "field": "ad.id", "operator": "IN", "value": ad_ids,
            }]),
            "limit": 500,
        }
        data = self._get(f"{act_id}/insights", params)

        metrics = []
        for raw in data.get("data", []):
            actions = {a["action_type"]: int(a.get("value", 0)) for a in raw.get("actions", [])}
            action_values = {a["action_type"]: float(a.get("value", 0)) for a in raw.get("action_values", [])}
            conversions = actions.get("offsite_conversion.fb_pixel_purchase", 0) or actions.get("lead", 0)
            revenue = action_values.get("offsite_conversion.fb_pixel_purchase", 0.0)
            spend = float(raw.get("spend", 0))

            metrics.append(CampaignMetrics(
                campaign_id=raw.get("ad_id", ""),
                platform="meta",
                date=date_start,
                impressions=int(raw.get("impressions", 0)),
                clicks=int(raw.get("clicks", 0)),
                spend_usd=spend,
                conversions=conversions,
                revenue_usd=revenue,
                cpm_usd=float(raw.get("cpm", 0)),
                cpc_usd=float(raw.get("cpc", 0)),
                ctr_pct=float(raw.get("ctr", 0)),
                roas=round(revenue / spend, 3) if spend > 0 else 0.0,
                cpa_usd=round(spend / conversions, 2) if conversions > 0 else 0.0,
                reach=int(raw.get("reach", 0)),
                raw=raw,
            ))

        self._log("pull_ad_metrics", "ad", None, "success",
                  response_summary={"count": len(metrics)})
        return metrics

    # ── Meta-specific helpers ─────────────────────────────────────────────────

    def get_instagram_account(self) -> dict:
        """
        Resolve the Instagram Business/Creator account linked to the user's Pages.
        Flow: GET /me/accounts → for each Page, GET /{page_id}/instagram_accounts
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        pages = self._get("me/accounts", {"fields": "id,name,instagram_business_account"})

        for page in pages.get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                ig_detail = self._get(ig["id"], {"fields": "id,name,username,followers_count,media_count"})
                self._log("get_instagram_account", "instagram_account", ig["id"], "success")
                return {
                    "id": ig_detail.get("id"),
                    "username": ig_detail.get("username"),
                    "name": ig_detail.get("name"),
                    "followers_count": ig_detail.get("followers_count"),
                    "media_count": ig_detail.get("media_count"),
                    "page_id": page.get("id"),
                    "page_name": page.get("name"),
                }

        self._log("get_instagram_account", "instagram_account", None, "error",
                  error="No Instagram Business account found on any linked Page")
        return {}

    def get_pixel_list(self) -> list[dict]:
        """GET /act_{account_id}/adspixels — list Meta Pixels for conversion tracking."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        account_id = self.credentials.account_id
        if not account_id:
            raise MetaAPIError("No account linked")

        act_id = f"act_{account_id}" if not account_id.startswith("act_") else account_id
        data = self._get(f"{act_id}/adspixels", {
            "fields": "id,name,last_fired_time,is_unavailable",
            "limit": 20,
        })

        pixels = []
        for raw in data.get("data", []):
            pixels.append({
                "id": raw.get("id"),
                "name": raw.get("name"),
                "last_fired": raw.get("last_fired_time"),
                "active": not raw.get("is_unavailable", False),
            })

        self._log("get_pixel_list", "pixel", None, "success",
                  response_summary={"count": len(pixels)})
        return pixels
