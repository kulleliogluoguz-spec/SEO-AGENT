"""
Snap Marketing API Adapter.

Official API: https://marketingapi.snapchat.com/docs/
Required OAuth2 scopes:
  - snapchat-marketing-api

Snap campaign hierarchy:
  AdAccount → Campaign → AdSquad (AdSet) → Ad

Note: Snap API requires Business account + approved developer application.
"""
from __future__ import annotations
import logging
from typing import Optional
from app.adapters.base import (
    AdapterCapabilityStage, AdapterCredentials, AdapterStatus,
    AudienceDraft, BaseAdsAdapter, CampaignDraft, CampaignMetrics, CreativeDraft,
)

logger = logging.getLogger(__name__)
SNAP_API_BASE = "https://adsapi.snapchat.com/v1"
SNAP_AUTH_URL = "https://accounts.snapchat.com/login/oauth2/authorize"


class SnapAdsAdapter(BaseAdsAdapter):
    """
    Snap Marketing API adapter.
    Best for: Gen Z audiences, 13-34 demographic, AR lenses, story ads.
    """

    PLATFORM = "snap"
    DOCS_URL = "https://marketingapi.snapchat.com/docs/"
    REQUIRED_SCOPES = ["snapchat-marketing-api"]

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        from urllib.parse import urlencode
        return f"{SNAP_AUTH_URL}?" + urlencode({
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.REQUIRED_SCOPES),
            "state": state,
        })

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        raise NotImplementedError("Implement: POST /accounts/oauth2/token with code")

    def refresh_access_token(self) -> AdapterCredentials:
        raise NotImplementedError("Implement: POST /accounts/oauth2/token with refresh_token")

    def verify_credentials(self) -> AdapterStatus:
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED
        return AdapterStatus.CREDENTIALS_SET

    def list_ad_accounts(self) -> list[dict]:
        """GET /me/organizations → GET /organizations/{id}/adaccounts"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /me/organizations then /adaccounts")

    def get_account_info(self) -> dict:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adaccounts/{ad_account_id}")

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """GET /adaccounts/{ad_account_id}/campaigns"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adaccounts/{id}/campaigns")

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        POST /adaccounts/{ad_account_id}/campaigns
        Objectives: BRAND_AWARENESS, TRAFFIC, CONVERSIONS, APP_INSTALL, LEAD_GENERATION
        Status: PAUSED
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adaccounts/{id}/campaigns with status=PAUSED")

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        if status == "ACTIVE":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: PUT /campaigns/{campaign_id}")

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: PUT /campaigns/{campaign_id} budget")

    def list_audiences(self) -> list[dict]:
        """GET /adaccounts/{ad_account_id}/segments — Snap audience segments."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adaccounts/{id}/segments")

    def create_audience(self, draft: AudienceDraft) -> dict:
        raise NotImplementedError("Implement: POST /adaccounts/{id}/segments")

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GET /adaccounts/{ad_account_id}/creatives"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adaccounts/{id}/creatives")

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        POST /adaccounts/{ad_account_id}/creatives
        Types: SNAP_AD (single video), COLLECTION, STORY, AR_LENS, FILTER
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adaccounts/{id}/creatives")

    def pull_campaign_metrics(
        self, campaign_ids: list[str], date_start: str, date_end: str, breakdown: Optional[str] = None,
    ) -> list[CampaignMetrics]:
        """
        GET /adaccounts/{ad_account_id}/stats
        Fields: impressions, swipes, spend, conversions, video_views, screen_time_millis
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adaccounts/{id}/stats with campaign filter")

    def pull_ad_metrics(self, ad_ids: list[str], date_start: str, date_end: str) -> list[CampaignMetrics]:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /ads/{id}/stats")
