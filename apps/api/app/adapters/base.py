"""
Base adapter interface for all official ads platform integrations.

Every platform adapter must implement this interface.
Capability stages control what operations are allowed without extra risk/permissions.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AdapterCapabilityStage(str, Enum):
    """Operational capability stage for an adapter instance."""
    PLANNING = "planning"          # No API calls — intelligence and planning only
    READ_REPORT = "read_report"    # Pull metrics, account structure, audiences
    DRAFT_CREATE = "draft_create"  # Create campaigns/ads in paused/draft state
    APPROVAL_GATE = "approval_gate"  # Requires human approval before publishing
    LIVE_OPTIMIZE = "live_optimize"  # Automated optimization loops on live campaigns


class AdapterStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    CREDENTIALS_SET = "credentials_set"
    AUTH_VERIFIED = "auth_verified"
    ACCOUNT_LINKED = "account_linked"
    READY = "ready"
    ERROR = "error"


@dataclass
class AdapterCredentials:
    """Credentials container. Never log or serialize sensitive fields."""
    platform: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    account_id: Optional[str] = None
    developer_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    extra: dict[str, str] = field(default_factory=dict)

    def is_token_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def safe_repr(self) -> dict:
        """Return a non-sensitive representation safe for logging."""
        return {
            "platform": self.platform,
            "account_id": self.account_id,
            "has_access_token": bool(self.access_token),
            "has_refresh_token": bool(self.refresh_token),
            "token_expired": self.is_token_expired(),
        }


@dataclass
class CampaignDraft:
    """Minimal campaign specification for draft creation."""
    name: str
    objective: str           # e.g. AWARENESS, TRAFFIC, CONVERSIONS, LEAD_GENERATION
    budget_daily_usd: float
    budget_lifetime_usd: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "PAUSED"  # Always start paused — requires approval to publish
    targeting: dict = field(default_factory=dict)
    placements: list[str] = field(default_factory=list)
    special_ad_categories: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AudienceDraft:
    """Audience targeting specification."""
    name: str
    audience_type: str       # CUSTOM, LOOKALIKE, SAVED, INTEREST
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    genders: list[str] = field(default_factory=list)
    geo_locations: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    behaviors: list[str] = field(default_factory=list)
    custom_audience_source: Optional[str] = None  # pixel, list, engagement
    lookalike_source_id: Optional[str] = None
    lookalike_ratio: float = 0.01  # 1%


@dataclass
class CreativeDraft:
    """Ad creative specification."""
    name: str
    format: str              # IMAGE, VIDEO, CAROUSEL, STORY, COLLECTION
    headline: str
    body: str
    cta: str                 # LEARN_MORE, SHOP_NOW, SIGN_UP, DOWNLOAD
    destination_url: str
    media_urls: list[str] = field(default_factory=list)
    overlay_text: Optional[str] = None


@dataclass
class CampaignMetrics:
    """Normalized metric snapshot from any platform."""
    campaign_id: str
    platform: str
    date: str
    impressions: int = 0
    clicks: int = 0
    spend_usd: float = 0.0
    conversions: int = 0
    revenue_usd: float = 0.0
    cpm_usd: float = 0.0
    cpc_usd: float = 0.0
    ctr_pct: float = 0.0
    roas: float = 0.0
    cpa_usd: float = 0.0
    reach: int = 0
    frequency: float = 0.0
    video_views: int = 0
    video_completion_rate: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class AdapterAuditLog:
    """Immutable audit record for every adapter operation."""
    platform: str
    operation: str
    account_id: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[str]
    status: str              # success | error | blocked_pending_approval
    request_summary: dict
    response_summary: dict
    error: Optional[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None


class BaseAdsAdapter(abc.ABC):
    """
    Abstract base class for all official ads platform adapters.

    Subclass this for each platform and implement all abstract methods.
    Approval gating is enforced at this layer — no campaign will be published
    without explicit approval when stage < LIVE_OPTIMIZE.
    """

    PLATFORM: str = ""
    DOCS_URL: str = ""
    REQUIRED_SCOPES: list[str] = []

    def __init__(self, credentials: AdapterCredentials, stage: AdapterCapabilityStage = AdapterCapabilityStage.PLANNING):
        self.credentials = credentials
        self.stage = stage
        self._audit_log: list[AdapterAuditLog] = []

    # ── Auth ──────────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Return the OAuth2 authorization URL for this platform."""

    @abc.abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> AdapterCredentials:
        """Exchange an auth code for access/refresh tokens."""

    @abc.abstractmethod
    def refresh_access_token(self) -> AdapterCredentials:
        """Refresh the access token using the refresh token."""

    @abc.abstractmethod
    def verify_credentials(self) -> AdapterStatus:
        """Test credentials and return current status."""

    # ── Account ───────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def list_ad_accounts(self) -> list[dict]:
        """Return all ad accounts accessible with current credentials."""

    @abc.abstractmethod
    def get_account_info(self) -> dict:
        """Return structured account metadata."""

    # ── Campaigns ─────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def list_campaigns(self, status_filter: Optional[str] = None) -> list[dict]:
        """List campaigns in the linked ad account."""

    @abc.abstractmethod
    def create_campaign(self, draft: CampaignDraft) -> dict:
        """
        Create a campaign in PAUSED/DRAFT state.
        Will raise PermissionError if stage < DRAFT_CREATE.
        """

    @abc.abstractmethod
    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        """
        Update campaign status. Publishing to ACTIVE requires stage >= APPROVAL_GATE
        with an approval record attached.
        """

    @abc.abstractmethod
    def update_campaign_budget(self, campaign_id: str, daily_budget_usd: float) -> dict:
        """Update campaign daily budget."""

    # ── Audiences ─────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def list_audiences(self) -> list[dict]:
        """List saved/custom audiences in the ad account."""

    @abc.abstractmethod
    def create_audience(self, draft: AudienceDraft) -> dict:
        """Create a targeting audience definition."""

    # ── Creatives ─────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def list_creatives(self, campaign_id: Optional[str] = None) -> list[dict]:
        """List ad creatives."""

    @abc.abstractmethod
    def create_creative(self, draft: CreativeDraft) -> dict:
        """Upload ad creative assets and create the creative object."""

    # ── Reporting ─────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def pull_campaign_metrics(
        self,
        campaign_ids: list[str],
        date_start: str,
        date_end: str,
        breakdown: Optional[str] = None,
    ) -> list[CampaignMetrics]:
        """Pull normalized campaign performance metrics."""

    @abc.abstractmethod
    def pull_ad_metrics(
        self,
        ad_ids: list[str],
        date_start: str,
        date_end: str,
    ) -> list[CampaignMetrics]:
        """Pull normalized ad-level performance metrics."""

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _require_stage(self, minimum: AdapterCapabilityStage) -> None:
        """Raise PermissionError if current stage is below the required minimum."""
        stage_order = [
            AdapterCapabilityStage.PLANNING,
            AdapterCapabilityStage.READ_REPORT,
            AdapterCapabilityStage.DRAFT_CREATE,
            AdapterCapabilityStage.APPROVAL_GATE,
            AdapterCapabilityStage.LIVE_OPTIMIZE,
        ]
        if stage_order.index(self.stage) < stage_order.index(minimum):
            raise PermissionError(
                f"{self.PLATFORM} adapter is at stage={self.stage.value}. "
                f"Operation requires stage={minimum.value}. "
                f"Connect credentials and complete auth verification to unlock."
            )

    def _log(
        self,
        operation: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: str = "success",
        request_summary: Optional[dict] = None,
        response_summary: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> AdapterAuditLog:
        record = AdapterAuditLog(
            platform=self.PLATFORM,
            operation=operation,
            account_id=self.credentials.account_id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            request_summary=request_summary or {},
            response_summary=response_summary or {},
            error=error,
        )
        self._audit_log.append(record)
        log_method = logger.error if status == "error" else logger.info
        log_method(
            "[%s] %s entity=%s/%s status=%s error=%s",
            self.PLATFORM, operation, entity_type, entity_id, status, error
        )
        return record

    def get_audit_log(self) -> list[AdapterAuditLog]:
        return list(self._audit_log)

    def capability_summary(self) -> dict:
        """Return a human-readable summary of current adapter capabilities."""
        return {
            "platform": self.PLATFORM,
            "stage": self.stage.value,
            "can_read": self.stage != AdapterCapabilityStage.PLANNING,
            "can_create_drafts": self.stage in [
                AdapterCapabilityStage.DRAFT_CREATE,
                AdapterCapabilityStage.APPROVAL_GATE,
                AdapterCapabilityStage.LIVE_OPTIMIZE,
            ],
            "can_publish": self.stage in [
                AdapterCapabilityStage.APPROVAL_GATE,
                AdapterCapabilityStage.LIVE_OPTIMIZE,
            ],
            "can_auto_optimize": self.stage == AdapterCapabilityStage.LIVE_OPTIMIZE,
            "requires_approval_to_publish": self.stage == AdapterCapabilityStage.APPROVAL_GATE,
            "docs_url": self.DOCS_URL,
            "required_scopes": self.REQUIRED_SCOPES,
        }

    def planning_summary(self) -> dict:
        """Return channel-level intelligence without making API calls."""
        return {
            "platform": self.PLATFORM,
            "stage": self.stage.value,
            "status": "planning_only" if self.stage == AdapterCapabilityStage.PLANNING else "connected",
            "next_step": self._next_step(),
        }

    def _next_step(self) -> str:
        steps = {
            AdapterCapabilityStage.PLANNING: f"Connect {self.PLATFORM} credentials to enable read access",
            AdapterCapabilityStage.READ_REPORT: "Verify credentials and link an ad account to enable draft creation",
            AdapterCapabilityStage.DRAFT_CREATE: "Enable approval workflow to allow campaign publishing",
            AdapterCapabilityStage.APPROVAL_GATE: "All campaigns require human approval before going live",
            AdapterCapabilityStage.LIVE_OPTIMIZE: "Full automation enabled — optimization loops are active",
        }
        return steps.get(self.stage, "Unknown stage")
