"""
Marketing Execution Engine — Pydantic Schemas
Request / Response models for campaigns, content, approvals, ads, performance.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


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
    description: Optional[str] = None
    objective: Optional[str] = None
    funnel_stage: Optional[FunnelStage] = None
    target_channels: list[ChannelType] = []
    target_personas: list[dict] = []
    budget: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: list[str] = []


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CampaignStatus] = None
    objective: Optional[str] = None
    funnel_stage: Optional[FunnelStage] = None
    target_channels: Optional[list[ChannelType]] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str]
    status: CampaignStatus
    objective: Optional[str]
    funnel_stage: Optional[FunnelStage]
    target_channels: list[str]
    target_personas: list[dict]
    budget: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


# ─── Content Item ────────────────────────────────────────────────────────────

class ContentItemCreate(BaseModel):
    campaign_id: Optional[uuid.UUID] = None
    channel: ChannelType
    title: Optional[str] = None
    body: str
    hook: Optional[str] = None
    cta: Optional[str] = None
    hashtags: list[str] = []
    media_instructions: Optional[str] = None
    channel_metadata: dict = {}
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    funnel_stage: Optional[FunnelStage] = None
    target_persona: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[uuid.UUID] = None
    variant_group: Optional[uuid.UUID] = None
    variant_label: Optional[str] = None


class ContentItemUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    hook: Optional[str] = None
    cta: Optional[str] = None
    hashtags: Optional[list[str]] = None
    channel_metadata: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[ContentStatus] = None


class ContentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    campaign_id: Optional[uuid.UUID]
    channel: ChannelType
    status: ContentStatus
    title: Optional[str]
    body: str
    hook: Optional[str]
    cta: Optional[str]
    hashtags: list[str]
    media_instructions: Optional[str]
    channel_metadata: dict
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    timezone: str
    funnel_stage: Optional[FunnelStage]
    target_persona: Optional[str]
    risk_level: RiskLevel
    compliance_notes: list
    policy_warnings: list
    source_type: Optional[str]
    source_id: Optional[uuid.UUID]
    variant_group: Optional[uuid.UUID]
    variant_label: Optional[str]
    external_post_id: Optional[str]
    created_at: datetime
    updated_at: datetime


# ─── Approval ────────────────────────────────────────────────────────────────

class ApprovalSubmit(BaseModel):
    decision: ApprovalDecision
    review_notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_item_id: uuid.UUID
    workspace_id: uuid.UUID
    decision: ApprovalDecision
    reviewed_by: Optional[uuid.UUID]
    review_notes: Optional[str]
    risk_score: float
    compliance_check: dict
    auto_approved: bool
    reviewed_at: Optional[datetime]
    created_at: datetime


class ApprovalQueueItem(BaseModel):
    content: ContentItemResponse
    approval: ApprovalResponse


# ─── Content Generation Requests ─────────────────────────────────────────────

class GenerateContentRequest(BaseModel):
    """Generate content for one or more channels from a topic / brief."""
    topic: str
    channels: list[ChannelType]
    campaign_id: Optional[uuid.UUID] = None
    funnel_stage: Optional[FunnelStage] = FunnelStage.AWARENESS
    target_persona: Optional[str] = None
    tone: Optional[str] = "professional"
    key_points: list[str] = []
    source_type: Optional[str] = None
    source_id: Optional[uuid.UUID] = None
    generate_variants: bool = False
    num_variants: int = Field(default=1, ge=1, le=5)


class RepurposeContentRequest(BaseModel):
    """Take one piece of content and generate multi-channel variants."""
    source_text: str
    source_type: str = "blog_post"
    source_id: Optional[uuid.UUID] = None
    target_channels: list[ChannelType] = [
        ChannelType.INSTAGRAM,
        ChannelType.TWITTER,
        ChannelType.LINKEDIN,
        ChannelType.TIKTOK,
    ]
    funnel_stage: Optional[FunnelStage] = None
    target_persona: Optional[str] = None


class GeneratedContentResponse(BaseModel):
    items: list[ContentItemResponse]
    repurpose_log_id: Optional[uuid.UUID] = None
    total_generated: int


# ─── Ad Campaign ─────────────────────────────────────────────────────────────

class AdCampaignCreate(BaseModel):
    campaign_id: Optional[uuid.UUID] = None
    name: str
    objective: Optional[str] = "traffic"
    primary_text: str
    headline: str
    description: Optional[str] = None
    audience_angle: Optional[str] = None
    daily_budget: float = 0.0
    lifetime_budget: float = 0.0
    audience_targeting: dict = {}


class AdCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    campaign_id: Optional[uuid.UUID]
    channel: ChannelType
    name: str
    status: CampaignStatus
    objective: Optional[str]
    primary_text: Optional[str]
    headline: Optional[str]
    description: Optional[str]
    audience_angle: Optional[str]
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
    fetched_at: Optional[datetime]


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
    account_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    scopes: list[str] = []
    automation_level: int = Field(default=0, ge=0, le=3)


class ConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    channel: ChannelType
    is_connected: bool
    account_name: Optional[str]
    account_id: Optional[str]
    automation_level: int
    rate_limit_remaining: Optional[int]
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
