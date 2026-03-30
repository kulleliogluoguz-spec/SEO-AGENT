"""
Pinterest Ads API Adapter.

Official API: https://developers.pinterest.com/docs/api/v5/
Required OAuth2 scopes:
  - ads:read
  - ads:write

Pinterest campaign hierarchy:
  AdAccount → Campaign → AdGroup → Ad (Pin)
"""
from __future__ import annotations
import logging
from typing import Optional
from app.adapters.base import (
    AdapterCapabilityStage, AdapterCredentials, AdapterStatus,
    AudienceDraft, BaseAdsAdapter, CampaignDraft, CampaignMetrics, CreativeDraft,
)

logger = logging.getLogger(__name__)
PINTEREST_API_BASE = "https://api.pinterest.com/v5"
PINTEREST_AUTH_URL = "https://www.pinterest.com/oauth/"


class PinterestAdsAdapter(BaseAdsAdapter):
    """
    Pinterest Ads API adapter.
    Best for: discovery-mode shoppers, gift buyers, home/fashion/food/travel niches.
    High-intent audiences: Pinterest users are actively planning purchases.
    """

    PLATFORM = "pinterest"
    DOCS_URL = "https://developers.pinterest.com/docs/api/v5/"
    REQUIRED_SCOPES = ["ads:read", "ads:write"]

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        from urllib.parse import urlencode
        return f"{PINTEREST_AUTH_URL}?" + urlencode({
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.REQUIRED_SCOPES),
            "state": state,
        })

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        raise NotImplementedError("Implement: POST /v5/oauth/token with code")

    def refresh_access_token(self) -> AdapterCredentials:
        raise NotImplementedError("Implement: POST /v5/oauth/token with refresh_token")

    def verify_credentials(self) -> AdapterStatus:
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED
        return AdapterStatus.CREDENTIALS_SET

    def list_ad_accounts(self) -> list[dict]:
        """GET /ad_accounts — list all accessible ad accounts."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts")

    def get_account_info(self) -> dict:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{ad_account_id}")

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """GET /ad_accounts/{ad_account_id}/campaigns"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{id}/campaigns")

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        POST /ad_accounts/{ad_account_id}/campaigns
        Objectives: AWARENESS, CONSIDERATION, VIDEO_VIEW, WEB_CONVERSION, CATALOG_SALES, WEB_SESSIONS
        Status: PAUSED (always start paused)
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /ad_accounts/{id}/campaigns with status=PAUSED")

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        if status == "ACTIVE":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: PATCH /ad_accounts/{id}/campaigns")

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: PATCH /ad_accounts/{id}/campaigns budget")

    def list_audiences(self) -> list[dict]:
        """GET /ad_accounts/{ad_account_id}/audiences"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{id}/audiences")

    def create_audience(self, draft: AudienceDraft) -> dict:
        raise NotImplementedError("Implement: POST /ad_accounts/{id}/audiences")

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GET /ad_accounts/{ad_account_id}/ads — list promoted pins."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{id}/ads")

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        POST /ad_accounts/{ad_account_id}/ads
        Pin format: Standard, Video, Shopping, Collection, Idea Pin
        Requires: pin_id (existing pin) or create new pin first
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /ad_accounts/{id}/ads")

    def pull_campaign_metrics(
        self, campaign_ids: list[str], date_start: str, date_end: str, breakdown: Optional[str] = None,
    ) -> list[CampaignMetrics]:
        """
        GET /ad_accounts/{ad_account_id}/campaigns/analytics
        Metrics: IMPRESSION, CLICKTHROUGH, SPEND_IN_DOLLAR, TOTAL_CONVERSIONS, VIDEO_V50_WATCH_TIME
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{id}/campaigns/analytics")

    def pull_ad_metrics(self, ad_ids: list[str], date_start: str, date_end: str) -> list[CampaignMetrics]:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ad_accounts/{id}/ads/analytics")
