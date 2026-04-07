"""
Marketing Execution Engine — Pydantic Schemas
Request / Response models for campaigns, content, approvals, ads, performance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ─── Shared Enums (mirror SQLAlchemy enums) ─────────────────────────────────


class ChannelType(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    META_ADS = "meta_ads"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CampaignStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FunnelStage(str, Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    RETENTION = "retention"
    ADVOCACY = "advocacy"


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


# ─── Campaign ───────────────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    objective: str | None = None
    funnel_stage: FunnelStage | None = None
    target_channels: list[ChannelType] = []
    target_personas: list[dict] = []
    budget: float = 0.0
    start_date: datetime | None = None
    end_date: datetime | None = None
    tags: list[str] = []


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: CampaignStatus | None = None
    objective: str | None = None
    funnel_stage: FunnelStage | None = None
    target_channels: list[ChannelType] | None = None
    budget: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    status: CampaignStatus
    objective: str | None
    funnel_stage: FunnelStage | None
    target_channels: list[str]
    target_personas: list[dict]
    budget: float
    start_date: datetime | None
    end_date: datetime | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


# ─── Content Item ────────────────────────────────────────────────────────────


class ContentItemCreate(BaseModel):
    campaign_id: uuid.UUID | None = None
    channel: ChannelType
    title: str | None = None
    body: str
    hook: str | None = None
    cta: str | None = None
    hashtags: list[str] = []
    media_instructions: str | None = None
    channel_metadata: dict = {}
    scheduled_at: datetime | None = None
    timezone: str = "UTC"
    funnel_stage: FunnelStage | None = None
    target_persona: str | None = None
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    variant_group: uuid.UUID | None = None
    variant_label: str | None = None


class ContentItemUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    hook: str | None = None
    cta: str | None = None
    hashtags: list[str] | None = None
    channel_metadata: dict | None = None
    scheduled_at: datetime | None = None
    status: ContentStatus | None = None


class ContentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    campaign_id: uuid.UUID | None
    channel: ChannelType
    status: ContentStatus
    title: str | None
    body: str
    hook: str | None
    cta: str | None
    hashtags: list[str]
    media_instructions: str | None
    channel_metadata: dict
    scheduled_at: datetime | None
    published_at: datetime | None
    timezone: str
    funnel_stage: FunnelStage | None
    target_persona: str | None
    risk_level: RiskLevel
    compliance_notes: list
    policy_warnings: list
    source_type: str | None
    source_id: uuid.UUID | None
    variant_group: uuid.UUID | None
    variant_label: str | None
    external_post_id: str | None
    created_at: datetime
    updated_at: datetime


# ─── Approval ────────────────────────────────────────────────────────────────


class ApprovalSubmit(BaseModel):
    decision: ApprovalDecision
    review_notes: str | None = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_item_id: uuid.UUID
    workspace_id: uuid.UUID
    decision: ApprovalDecision
    reviewed_by: uuid.UUID | None
    review_notes: str | None
    risk_score: float
    compliance_check: dict
    auto_approved: bool
    reviewed_at: datetime | None
    created_at: datetime


class ApprovalQueueItem(BaseModel):
    content: ContentItemResponse
    approval: ApprovalResponse


# ─── Content Generation Requests ─────────────────────────────────────────────


class GenerateContentRequest(BaseModel):
    """Generate content for one or more channels from a topic / brief."""

    topic: str
    channels: list[ChannelType]
    campaign_id: uuid.UUID | None = None
    funnel_stage: FunnelStage | None = FunnelStage.AWARENESS
    target_persona: str | None = None
    tone: str | None = "professional"
    key_points: list[str] = []
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    generate_variants: bool = False
    num_variants: int = Field(default=1, ge=1, le=5)


class RepurposeContentRequest(BaseModel):
    """Take one piece of content and generate multi-channel variants."""

    source_text: str
    source_type: str = "blog_post"
    source_id: uuid.UUID | None = None
    target_channels: list[ChannelType] = [
        ChannelType.INSTAGRAM,
        ChannelType.TWITTER,
        ChannelType.LINKEDIN,
        ChannelType.TIKTOK,
    ]
    funnel_stage: FunnelStage | None = None
    target_persona: str | None = None


class GeneratedContentResponse(BaseModel):
    items: list[ContentItemResponse]
    repurpose_log_id: uuid.UUID | None = None
    total_generated: int


# ─── Ad Campaign ─────────────────────────────────────────────────────────────


class AdCampaignCreate(BaseModel):
    campaign_id: uuid.UUID | None = None
    name: str
    objective: str | None = "traffic"
    primary_text: str
    headline: str
    description: str | None = None
    audience_angle: str | None = None
    daily_budget: float = 0.0
    lifetime_budget: float = 0.0
    audience_targeting: dict = {}


class AdCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    campaign_id: uuid.UUID | None
    channel: ChannelType
    name: str
    status: CampaignStatus
    objective: str | None
    primary_text: str | None
    headline: str | None
    description: str | None
    audience_angle: str | None
    daily_budget: float
    lifetime_budget: float
    audience_targeting: dict
    performance: dict
    created_at: datetime
    updated_at: datetime


# ─── Performance ─────────────────────────────────────────────────────────────


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_item_id: uuid.UUID
    impressions: int
    reach: int
    clicks: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    click_through_rate: float
    conversions: int
    conversion_rate: float
    cost: float
    cost_per_click: float
    cost_per_conversion: float
    revenue: float
    roas: float
    fetched_at: datetime | None


class PerformanceSummary(BaseModel):
    total_impressions: int = 0
    total_clicks: int = 0
    total_engagement: int = 0
    total_conversions: int = 0
    avg_engagement_rate: float = 0.0
    avg_ctr: float = 0.0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    overall_roas: float = 0.0
    by_channel: dict[str, dict] = {}
    top_performing: list[dict] = []


# ─── Channel Connector ──────────────────────────────────────────────────────


class ConnectorCreate(BaseModel):
    channel: ChannelType
    account_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    scopes: list[str] = []
    automation_level: int = Field(default=0, ge=0, le=3)


class ConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    channel: ChannelType
    is_connected: bool
    account_name: str | None
    account_id: str | None
    automation_level: int
    rate_limit_remaining: int | None
    created_at: datetime
    updated_at: datetime


# ─── Calendar ────────────────────────────────────────────────────────────────


class CalendarDay(BaseModel):
    date: str  # YYYY-MM-DD
    items: list[ContentItemResponse] = []


class CalendarResponse(BaseModel):
    days: list[CalendarDay]
    total_scheduled: int
    total_published: int
    total_draft: int


# ─── Batch Scheduling ───────────────────────────────────────────────────────


class BatchScheduleRequest(BaseModel):
    content_item_ids: list[uuid.UUID]
    schedule_times: list[datetime]  # must be same length as content_item_ids
    timezone: str = "UTC"


class BatchScheduleResponse(BaseModel):
    scheduled: int
    failed: int
    errors: list[dict] = []
