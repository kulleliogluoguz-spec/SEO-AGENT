"""
LinkedIn Marketing Solutions API Adapter.

Official API: https://learn.microsoft.com/en-us/linkedin/marketing/
Required OAuth2 scopes:
  - r_ads (read ads data)
  - w_ads (create/update ads)
  - r_ads_reporting (read reports)
  - r_organization_social (read organization page data)

Note: LinkedIn requires app review for Marketing Developer Platform (MDP) access.
Apply at: https://www.linkedin.com/developers/apps

Campaign hierarchy:
  AdAccount → Campaign Group → Campaign → Creative

Best for: B2B lead generation, thought leadership, ABM.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.adapters.base import (
    AdapterCapabilityStage, AdapterCredentials, AdapterStatus,
    AudienceDraft, BaseAdsAdapter, CampaignDraft, CampaignMetrics, CreativeDraft,
)

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


class LinkedInAdsAdapter(BaseAdsAdapter):
    """
    LinkedIn Marketing Solutions API adapter.

    Supports: Sponsored Content, Message Ads, Dynamic Ads, Lead Gen Forms.
    Note: MDP access requires LinkedIn application review.
    """

    PLATFORM = "linkedin"
    DOCS_URL = "https://learn.microsoft.com/en-us/linkedin/marketing/"
    REQUIRED_SCOPES = ["r_ads", "w_ads", "r_ads_reporting", "r_organization_social"]

    OBJECTIVE_MAP = {
        "AWARENESS": "BRAND_AWARENESS",
        "WEBSITE_VISITS": "WEBSITE_VISITS",
        "ENGAGEMENT": "ENGAGEMENT",
        "VIDEO_VIEWS": "VIDEO_VIEWS",
        "LEAD_GENERATION": "LEAD_GENERATION",
        "WEBSITE_CONVERSIONS": "WEBSITE_CONVERSIONS",
        "JOB_APPLICANTS": "JOB_APPLICANTS",
    }

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.REQUIRED_SCOPES),
            "state": state,
        }
        return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        raise NotImplementedError("Implement: POST to LINKEDIN_TOKEN_URL with grant_type=authorization_code")

    def refresh_access_token(self) -> AdapterCredentials:
        raise NotImplementedError("LinkedIn tokens are 60 days. Implement refresh flow.")

    def verify_credentials(self) -> AdapterStatus:
        if not self.credentials.access_token:
            return AdapterStatus.NOT_CONFIGURED
        return AdapterStatus.CREDENTIALS_SET

    def list_ad_accounts(self) -> list[dict]:
        """GET /adAccountsV2 — list accessible ad accounts."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adAccountsV2?q=search")

    def get_account_info(self) -> dict:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adAccountsV2/{account_id}")

    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """GET /adCampaignsV2?q=search&account={account_id}"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adCampaignsV2")

    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        POST /adCampaignsV2
        Required: account (URN), name, type, objectiveType, status=PAUSED
        Daily budget: dailyBudget { amount, currencyCode }
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adCampaignsV2 with status=PAUSED")

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        if status == "ACTIVE":
            self._require_stage(AdapterCapabilityStage.APPROVAL_GATE)
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adCampaignsV2/{id} status update")

    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adCampaignsV2/{id} budget update")

    def list_audiences(self) -> list[dict]:
        """GET /customAudiences — matched and lookalike audiences."""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /customAudiences")

    def create_audience(self, draft: AudienceDraft) -> dict:
        raise NotImplementedError("Implement: POST /customAudiences")

    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """GET /adCreativesV2?q=search&campaign={campaign_urn}"""
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adCreativesV2")

    def create_creative(self, draft: CreativeDraft) -> dict:
        """
        POST /adCreativesV2
        For Sponsored Content: reference to an organization post URN or direct media
        For Lead Gen: leadGenFormId reference
        """
        self._require_stage(AdapterCapabilityStage.DRAFT_CREATE)
        raise NotImplementedError("Implement: POST /adCreativesV2")

    def pull_campaign_metrics(
        self, campaign_ids: list[str], date_start: str, date_end: str, breakdown: Optional[str] = None,
    ) -> list[CampaignMetrics]:
        """
        GET /adAnalyticsV2?q=analytics&pivot=CAMPAIGN&dateRange=...
        Metrics: impressions, clicks, costInLocalCurrency, conversions, leads, videoViews
        """
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adAnalyticsV2 for campaigns")

    def pull_ad_metrics(self, ad_ids: list[str], date_start: str, date_end: str) -> list[CampaignMetrics]:
        self._require_stage(AdapterCapabilityStage.READ_REPORT)
        raise NotImplementedError("Implement: GET /adAnalyticsV2 for ads")
