"""
TikTok for Business API Adapter — Full Implementation.

Official API: https://ads.tiktok.com/marketing_api/docs
API Base: https://business-api.tiktok.com/open_api/v1.3/

Auth flow:
  1. Redirect to TIKTOK_AUTH_URL with app_id + redirect_uri + state
  2. TikTok redirects back with auth_code
  3. POST /oauth2/access_token/ to get access_token + advertiser_ids
  4. Access tokens do not expire but can be revoked

Required scopes in App settings:
  ad.read, ad.write, adgroup.read, adgroup.write,
  campaign.read, campaign.write, report.read

Campaign hierarchy:
  Advertiser → Campaign → AdGroup → Ad

Key differences from Meta:
  - No OAuth refresh token — access tokens are permanent until revoked
  - Budget is in local currency (not cents or micros)
  - Minimum budget: $50/day at campaign, $20/day at ad group
  - Ad status uses DISABLE (not PAUSED)
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.adapters.base import (
    AdapterCapabilityStage, AdapterCredentials, AdapterStatus,
    AudienceDraft, BaseAdsAdapter, CampaignDraft, CampaignMetrics, CreativeDraft,
)

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://business-api.tiktok.com/open_api/v1.3"
TIKTOK_AUTH_URL = "https://business-api.tiktok.com/portal/auth"

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

OBJECTIVE_MAP = {
    "AWARENESS": "REACH",
    "TRAFFIC": "TRAFFIC",
    "ENGAGEMENT": "VIDEO_VIEWS",
    "LEADS": "LEAD_GENERATION",
    "SALES": "CONVERSIONS",
    "APP_PROMOTION": "APP_INSTALL",
    # Direct TikTok objectives pass through
    "REACH": "REACH",
    "VIDEO_VIEWS": "VIDEO_VIEWS",
    "LEAD_GENERATION": "LEAD_GENERATION",
    "CONVERSIONS": "CONVERSIONS",
    "APP_INSTALL": "APP_INSTALL",
}


class TikTokAPIError(Exception):
    def __init__(self, message: str, code: int = 0):
        self.api_code = code
        super().__init__(message)


class TikTokAdsAdapter(BaseAdsAdapter):
    """
    TikTok for Business API adapter.

    Supports: In-Feed Video, Spark Ads, TopView, Branded Hashtag Challenge.
    Note: Spark Ads require creator authorization via TikTok Creator Marketplace.
    """

    PLATFORM = "tiktok"
    DOCS_URL = "https://ads.tiktok.com/marketing_api/docs"
    REQUIRED_SCOPES = [
        "ad.read", "ad.write",
        "adgroup.read", "adgroup.write",
        "campaign.read", "campaign.write",
        "report.read",
        "audience.read", "audience.write",
    ]

    # ── Internal HTTP helpers ─────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Access-Token": self.credentials.access_token or "",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None, retries: int = 2) -> dict:
        url = f"{TIKTOK_API_BASE}/{path.lstrip('/')}"
        for attempt in range(retries + 1):
            try:
                resp = httpx.get(url, params=params, headers=self._headers(), timeout=_TIMEOUT)
            except httpx.RequestError as e:
                raise TikTokAPIError(f"Network error: {e}")

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                if attempt < retries:
                    time.sleep(min(wait, 120))
                    continue
                raise TikTokAPIError("Rate limit exceeded", code=429)

            data = resp.json()
            code = data.get("code", 0)
            if code != 0:
                raise TikTokAPIError(
                    data.get("message", f"TikTok API error code {code}"),
                    code=code,
                )
            return data.get("data", {})

        raise TikTokAPIError(f"GET {path} failed after {retries} retries")

    def _post(self, path: str, payload: dict, retries: int = 1) -> dict:
        url = f"{TIKTOK_API_BASE}/{path.lstrip('/')}"
        for attempt in range(retries + 1):
            try:
                resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
            except httpx.RequestError as e:
                raise TikTokAPIError(f"Network error: {e}")

            if resp.status_code == 429:
                if attempt < retries:
                    time.sleep(60)
                    continue
                raise TikTokAPIError("Rate limit exceeded", code=429)

            data = resp.json()
            code = data.get("code", 0)
            if code != 0:
                raise TikTokAPIError(
                    data.get("message", f"TikTok API error code {code}"),
                    code=code,
                )
            return data.get("data", {})

        raise TikTokAPIError(f"POST {path} failed after {retries} retries")

    def _advertiser_id(self) -> str:
        aid = self.credentials.account_id
        if not aid:
            raise TikTokAPIError("No advertiser_id linked — link an ad account first")
        return aid

    # ── Auth ──────────────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "app_id": self.credentials.client_id or os.environ.get("TIKTOK_CLIENT_ID", ""),
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{TIKTOK_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        """
        POST /oauth2/access_token/
        Returns access_token + list of advertiser_ids.
        TikTok tokens don't expire — they're valid until revoked.
        """
        app_id = self.credentials.client_id or os.environ.get("TIKTOK_CLIENT_ID", "")
        app_secret = self.credentials.client_secret or os.environ.get("TIKTOK_CLIENT_SECRET", "")

        if not app_id or not app_secret:
            raise TikTokAPIError(
                "TIKTOK_CLIENT_ID and TIKTOK_CLIENT_SECRET must be set. "
                "Create an app at ads.tiktok.com/marketing_api/apps, "
                "complete the Marketing API review, then set scopes: "
                "ad.read, ad.write, campaign.read, campaign.write, report.read"
            )

        try:
            resp = httpx.post(f"{TIKTOK_API_BASE}/oauth2/access_token/", json={
                "app_id": app_id,
                "secret": app_secret,
                "auth_code": code,
            }, timeout=_TIMEOUT)
            data = resp.json()
        except httpx.RequestError as e:
            raise TikTokAPIError(f"Network error during token exchange: {e}")

        code_val = data.get("code", 0)
        if code_val != 0:
            raise TikTokAPIError(
                data.get("message", f"Token exchange failed with code {code_val}"),
                code=code_val,
            )

        token_data = data.get("data", {})
        access_token = token_data.get("access_token")
        if not access_token:
            raise TikTokAPIError("No access_token in TikTok token exchange response")

        advertiser_ids = token_data.get("advertiser_ids", [])
        self._log("exchange_code", status="success",
                  response_summary={"advertiser_count": len(advertiser_ids)})

        return AdapterCredentials(
            platform="tiktok",
            access_token=access_token,
            client_id=app_id,
            client_secret=app_secret,
            extra={
                "advertiser_ids": advertiser_ids,
                "scope": token_data.get("scope", ""),
            },
        )

    def refresh_access_token(self) -> AdapterCredentials:
        """
        TikTok access tokens don't expire.
        This method is a no-op — return current credentials unchanged.
        """
        self._log("refresh_access_token", status="success",
                  response_summary={"note": "TikTok tokens do not expire"})
        return self.credentials

    def verify_credentials(self) -> AdapterStatus:
        """Call /oauth2/advertiser/get/ to verify the token is valid."""
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED

        app_id = self.credentials.client_id or os.environ.get("TIKTOK_CLIENT_ID", "")
        try:
            data = self._get("oauth2/advertiser/get/", {
                "app_id": app_id,
                "secret": self.credentials.client_secret or os.environ.get("TIKTOK_CLIENT_SECRET", ""),
            })
            self._log("verify_credentials", status="success",
                      response_summary={"advertiser_count": len(data.get("list", []))})
            return AdapterStatus.AUTH_VERIFIED
        except TikTokAPIError as e:
            logger.warning("[tiktok] verify_credentials failed: %s", e)
            return AdapterStatus.ERROR

    # ── Account ───────────────────────────────────────────────────────────────

    def list_ad_accounts(self) -> list[dict]:
        """GET /oauth2/advertiser/get/ — list accessible advertiser accounts."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        app_id = self.credentials.client_id or os.environ.get("TIKTOK_CLIENT_ID", "")
        app_secret = self.credentials.client_secret or os.environ.get("TIKTOK_CLIENT_SECRET", "")

        data = self._get("oauth2/advertiser/get/", {
            "app_id": app_id,
            "secret": app_secret,
        })

        accounts = []
        for raw in data.get("list", []):
            accounts.append({
                "id": str(raw.get("advertiser_id")),
                "name": raw.get("advertiser_name", "Unnamed"),
                "currency": raw.get("currency", "USD"),
                "timezone": raw.get("timezone", "UTC"),
                "status": raw.get("status", "UNKNOWN"),
            })

        self._log("list_ad_accounts", "account", None, "success",
                  response_summary={"count": len(accounts)})
        return accounts

    def get_account_info(self) -> dict:
        """GET /advertiser/info/ — account details."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        data = self._get("advertiser/info/", {
            "advertiser_ids": json.dumps([advertiser_id]),
        })

        info_list = data.get("list", [])
        if not info_list:
            raise TikTokAPIError(f"No info returned for advertiser {advertiser_id}")

        raw = info_list[0]
        self._log("get_account_info", "account", advertiser_id, "success")
        return {
            "id": str(raw.get("advertiser_id")),
            "name": raw.get("name"),
            "currency": raw.get("currency"),
            "timezone": raw.get("timezone"),
            "status": raw.get("status"),
            "balance": raw.get("balance"),
        }

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """GET /campaign/get/"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        params = {
            "advertiser_id": advertiser_id,
            "page_size": 100,
        }
        if status_filter:
            params["primary_status"] = status_filter

        data = self._get("campaign/get/", params)
        campaigns = []
        for raw in data.get("list", []):
            campaigns.append({
                "id": str(raw.get("campaign_id")),
                "name": raw.get("campaign_name"),
                "status": raw.get("primary_status"),
                "objective": raw.get("objective_type"),
                "daily_budget_usd": float(raw.get("budget", 0)),
                "budget_mode": raw.get("budget_mode"),
                "created_time": raw.get("create_time"),
                "platform": "tiktok",
            })

        self._log("list_campaigns", "campaign", None, "success",
                  response_summary={"count": len(campaigns)})
        return campaigns

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        POST /campaign/create/
        Always creates with operation_status=DISABLE (TikTok equivalent of PAUSED).
        Minimum budget: $50/day at campaign level.
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        advertiser_id = self._advertiser_id()

        objective = OBJECTIVE_MAP.get(draft.objective.upper(), "REACH")
        budget = max(draft.budget_daily_usd, 50.0)  # TikTok minimum $50/day

        payload = {
            "advertiser_id": advertiser_id,
            "campaign_name": draft.name,
            "objective_type": objective,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": budget,
            "operation_status": "DISABLE",  # Never ENABLE without approval
        }

        data = self._post("campaign/create/", payload)
        campaign_id = str(data.get("campaign_id", ""))

        self._log("create_campaign", "campaign", campaign_id, "success",
                  request_summary={"name": draft.name, "objective": objective, "status": "DISABLE"},
                  response_summary={"campaign_id": campaign_id})

        return {
            "id": campaign_id,
            "platform": "tiktok",
            "status": "DISABLE",
            "objective": objective,
            "name": draft.name,
            "daily_budget_usd": budget,
            "ads_manager_url": f"https://ads.tiktok.com/i18n/perf/campaign?aadvid={advertiser_id}",
        }

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        """POST /campaign/status/update/ — ENABLE requires APPROVAL_GATE stage."""
        tiktok_status = {"ACTIVE": "ENABLE", "PAUSED": "DISABLE"}.get(status, status)
        if tiktok_status == "ENABLE":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)

        advertiser_id = self._advertiser_id()
        data = self._post("campaign/status/update/", {
            "advertiser_id": advertiser_id,
            "campaign_ids": [campaign_id],
            "operation_status": tiktok_status,
        })

        self._log("update_campaign_status", "campaign", campaign_id, "success",
                  request_summary={"status": tiktok_status})
        return {"id": campaign_id, "status": tiktok_status}

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        """POST /campaign/update/ with budget."""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        advertiser_id = self._advertiser_id()

        budget = max(daily_budget_usd, 50.0)
        self._post("campaign/update/", {
            "advertiser_id": advertiser_id,
            "campaign_id": campaign_id,
            "budget": budget,
            "budget_mode": "BUDGET_MODE_DAY",
        })

        self._log("update_campaign_budget", "campaign", campaign_id, "success",
                  request_summary={"daily_budget_usd": budget})
        return {"id": campaign_id, "daily_budget_usd": budget}

    # ── Audiences ─────────────────────────────────────────────────────────────

    def list_audiences(self) -> list[dict]:
        """GET /dmp/custom_audience/list/"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        data = self._get("dmp/custom_audience/list/", {
            "advertiser_id": advertiser_id,
            "page_size": 100,
        })

        audiences = []
        for raw in data.get("list", []):
            audiences.append({
                "id": str(raw.get("custom_audience_id")),
                "name": raw.get("name"),
                "type": raw.get("audience_type"),
                "size": raw.get("audience_size"),
                "status": raw.get("status"),
            })

        self._log("list_audiences", "audience", None, "success",
                  response_summary={"count": len(audiences)})
        return audiences

    def create_audience(self, draft: AudienceDraft) -> dict:
        """POST /dmp/custom_audience/create/"""
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        advertiser_id = self._advertiser_id()

        audience_type = "ENGAGEMENT" if draft.audience_type in ("CUSTOM", "ENGAGEMENT") else "CUSTOMER_FILE"
        payload = {
            "advertiser_id": advertiser_id,
            "custom_audience_name": draft.name,
            "audience_type": audience_type,
        }

        if audience_type == "LOOKALIKE" and draft.lookalike_source_id:
            payload["audience_type"] = "LOOKALIKE"
            payload["source_audience_ids"] = [draft.lookalike_source_id]
            payload["lookalike_spec"] = {
                "location_ids": draft.geo_locations[:3] if draft.geo_locations else [],
                "similarity_type": "REACH",
            }

        data = self._post("dmp/custom_audience/create/", payload)
        audience_id = str(data.get("custom_audience_id", ""))

        self._log("create_audience", "audience", audience_id, "success",
                  request_summary={"name": draft.name, "type": audience_type})
        return {"id": audience_id, "name": draft.name, "type": audience_type}

    # ── Creatives ─────────────────────────────────────────────────────────────

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GET /ad/get/"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        params = {"advertiser_id": advertiser_id, "page_size": 50}
        if campaign_id:
            params["campaign_ids"] = json.dumps([campaign_id])

        data = self._get("ad/get/", params)
        creatives = []
        for raw in data.get("list", []):
            creatives.append({
                "id": str(raw.get("ad_id")),
                "name": raw.get("ad_name"),
                "format": raw.get("ad_format"),
                "status": raw.get("primary_status"),
                "video_id": raw.get("video_id"),
                "thumbnail_url": raw.get("image_ids", [None])[0],
            })

        self._log("list_creatives", "creative", None, "success",
                  response_summary={"count": len(creatives)})
        return creatives

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        POST /ad/create/ — requires an existing ad_group_id.
        For Spark Ads: video_id from creator authorization.
        For standard: video_id from /file/video/ad/upload/.
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        advertiser_id = self._advertiser_id()
        ad_group_id = self.credentials.extra.get("default_ad_group_id")
        if not ad_group_id:
            raise TikTokAPIError(
                "ad_group_id required to create TikTok ad. "
                "Create an AdGroup first and provide its ID in credentials.extra."
            )

        payload = {
            "advertiser_id": advertiser_id,
            "adgroup_id": ad_group_id,
            "ad_name": draft.name,
            "ad_format": "SINGLE_VIDEO",
            "landing_page_url": draft.destination_url,
            "call_to_action": draft.cta.upper().replace(" ", "_"),
            "ad_text": draft.body[:100],  # TikTok max 100 chars
            "operation_status": "DISABLE",  # Never ENABLE without approval
        }

        if draft.media_urls:
            # Assuming video_id has been pre-uploaded
            payload["video_id"] = draft.media_urls[0]
        if draft.headline:
            payload["app_name"] = draft.headline[:40]

        data = self._post("ad/create/", payload)
        ad_id = str(data.get("ad_id", ""))

        self._log("create_creative", "creative", ad_id, "success",
                  request_summary={"name": draft.name, "ad_group_id": ad_group_id})
        return {
            "id": ad_id,
            "name": draft.name,
            "status": "DISABLE",
            "destination_url": draft.destination_url,
            "cta": draft.cta,
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
        GET /report/integrated/get/ — campaign-level report.
        Dates: YYYY-MM-DD format.
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        metrics_fields = [
            "spend", "impressions", "clicks", "ctr", "cpm", "cpc",
            "conversion", "cost_per_conversion", "real_time_conversion",
            "reach", "frequency", "video_play_actions", "video_watched_2s",
            "video_watched_6s", "video_views_p100",
        ]

        params = {
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_CAMPAIGN",
            "dimensions": json.dumps(["campaign_id", "stat_time_day"]),
            "metrics": json.dumps(metrics_fields),
            "start_date": date_start,
            "end_date": date_end,
            "filters": json.dumps([{
                "field_name": "campaign_id",
                "filter_type": "IN",
                "filter_value": json.dumps(campaign_ids),
            }]),
            "page_size": 200,
        }

        data = self._get("report/integrated/get/", params)
        result_list = data.get("list", [])

        metrics = []
        for row in result_list:
            dims = row.get("dimensions", {})
            m = row.get("metrics", {})

            spend = float(m.get("spend", 0))
            conversions = int(float(m.get("conversion", 0)))
            revenue = float(m.get("real_time_conversion_rate_v2", 0))
            impressions = int(m.get("impressions", 0))

            metrics.append(CampaignMetrics(
                campaign_id=str(dims.get("campaign_id", "")),
                platform="tiktok",
                date=dims.get("stat_time_day", date_start)[:10],
                impressions=impressions,
                clicks=int(m.get("clicks", 0)),
                spend_usd=round(spend, 4),
                conversions=conversions,
                revenue_usd=round(revenue, 2),
                cpm_usd=round(float(m.get("cpm", 0)), 4),
                cpc_usd=round(float(m.get("cpc", 0)), 4),
                ctr_pct=round(float(m.get("ctr", 0)), 4),
                roas=round(revenue / spend, 3) if spend > 0 else 0.0,
                cpa_usd=round(float(m.get("cost_per_conversion", 0)), 4),
                reach=int(m.get("reach", 0)),
                frequency=round(float(m.get("frequency", 0)), 2),
                video_views=int(m.get("video_play_actions", 0)),
                video_completion_rate=round(float(m.get("video_views_p100", 0)) / max(impressions, 1), 4),
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
        """GET /report/integrated/get/ at ad level."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        advertiser_id = self._advertiser_id()

        params = {
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_AD",
            "dimensions": json.dumps(["ad_id", "stat_time_day"]),
            "metrics": json.dumps(["spend", "impressions", "clicks", "ctr", "cpm", "cpc", "conversion"]),
            "start_date": date_start,
            "end_date": date_end,
            "filters": json.dumps([{
                "field_name": "ad_id",
                "filter_type": "IN",
                "filter_value": json.dumps(ad_ids),
            }]),
            "page_size": 200,
        }

        data = self._get("report/integrated/get/", params)
        metrics = []
        for row in data.get("list", []):
            dims = row.get("dimensions", {})
            m = row.get("metrics", {})
            spend = float(m.get("spend", 0))
            conversions = int(float(m.get("conversion", 0)))

            metrics.append(CampaignMetrics(
                campaign_id=str(dims.get("ad_id", "")),
                platform="tiktok",
                date=dims.get("stat_time_day", date_start)[:10],
                impressions=int(m.get("impressions", 0)),
                clicks=int(m.get("clicks", 0)),
                spend_usd=round(spend, 4),
                conversions=conversions,
                cpm_usd=round(float(m.get("cpm", 0)), 4),
                cpc_usd=round(float(m.get("cpc", 0)), 4),
                ctr_pct=round(float(m.get("ctr", 0)), 4),
                cpa_usd=round(spend / conversions, 2) if conversions > 0 else 0.0,
                raw=row,
            ))

        self._log("pull_ad_metrics", "ad", None, "success",
                  response_summary={"count": len(metrics)})
        return metrics
