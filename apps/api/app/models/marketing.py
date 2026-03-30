"""
Marketing Execution Engine — SQLAlchemy Models
Covers: campaigns, content calendar, social posts, approvals,
        channel connectors, performance metrics, ad campaigns.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, DeclarativeBase


# ═══════════════════════════════════════════════════════════════════════════
#  INTEGRATION POINT: Replace this Base with your existing repo's Base.
#
#  Your repo likely has one of:
#    from app.core.database import Base
#    from app.models.base import Base
#
#  For standalone development/testing, this fallback works:
# ═══════════════════════════════════════════════════════════════════════════
try:
    from app.core.db.database import Base  # Your repo uses app.core.db.database
except ImportError:
    try:
        from app.core.database import Base  # Fallback path
    except ImportError:
        class Base(DeclarativeBase):
            """Fallback Base — only used when running outside the main repo."""
            pass


# ─── Enums ──────────────────────────────────────────────────────────────────

class ChannelType(str, enum.Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    META_ADS = "meta_ads"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CampaignStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ApprovalDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FunnelStage(str, enum.Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    RETENTION = "retention"
    ADVOCACY = "advocacy"


class AutomationLevel(int, enum.Enum):
    DRAFT_ONLY = 0
    APPROVAL_REQUIRED = 1
    LOW_RISK_AUTO = 2
    ADVANCED_AUTO = 3


# ─── Campaign ───────────────────────────────────────────────────────────────

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.PLANNING, nullable=False)
    objective = Column(String(255))
    funnel_stage = Column(Enum(FunnelStage))
    target_channels = Column(ARRAY(String), default=[])
    target_personas = Column(JSONB, default=[])
    budget = Column(Float, default=0.0)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    tags = Column(ARRAY(String), default=[])
    metadata_ = Column("metadata", JSONB, default={})
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    content_items = relationship("ContentItem", back_populates="campaign", cascade="all,delete-orphan")
    ad_campaigns = relationship("AdCampaign", back_populates="campaign", cascade="all,delete-orphan")

    __table_args__ = (
        Index("ix_campaigns_workspace_status", "workspace_id", "status"),
    )


# ─── Content Calendar / Content Items ───────────────────────────────────────

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    channel = Column(Enum(ChannelType), nullable=False)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)

    # Content
    title = Column(String(500))
    body = Column(Text, nullable=False)
    hook = Column(Text)
    cta = Column(Text)
    hashtags = Column(ARRAY(String), default=[])
    media_instructions = Column(Text)  # AI-generated visual/content instructions
    channel_metadata = Column(JSONB, default={})
    """
    Channel-specific data:
    Instagram: { carousel_slides: [...], aspect_ratio, location_tag }
    TikTok:    { script_sections: [...], music_suggestion, duration_target }
    Twitter:   { thread: [...], quote_tweet_ref }
    LinkedIn:  { article_mode: bool, document_carousel: bool }
    Meta Ads:  { headline, description, audience_angle, placement }
    """

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    timezone = Column(String(64), default="UTC")

    # Targeting
    funnel_stage = Column(Enum(FunnelStage))
    target_persona = Column(String(255))

    # Compliance
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    compliance_notes = Column(JSONB, default=[])
    policy_warnings = Column(JSONB, default=[])

    # Source linking (SEO insight → social post)
    source_type = Column(String(64))  # "seo_recommendation", "blog_post", "insight"
    source_id = Column(UUID(as_uuid=True))

    # Variants for A/B testing
    variant_group = Column(UUID(as_uuid=True))
    variant_label = Column(String(32))  # "A", "B", "C"

    # Tracking
    external_post_id = Column(String(255))  # ID from the platform after publishing
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="content_items")
    approval = relationship("ContentApproval", back_populates="content_item", uselist=False,
                            cascade="all,delete-orphan")
    performance = relationship("ContentPerformance", back_populates="content_item", uselist=False,
                               cascade="all,delete-orphan")

    __table_args__ = (
        Index("ix_content_workspace_status", "workspace_id", "status"),
        Index("ix_content_workspace_channel", "workspace_id", "channel"),
        Index("ix_content_scheduled", "scheduled_at"),
        Index("ix_content_variant_group", "variant_group"),
    )


# ─── Approval Queue ────────────────────────────────────────────────────────

class ContentApproval(Base):
    __tablename__ = "content_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), unique=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    decision = Column(Enum(ApprovalDecision), default=ApprovalDecision.PENDING, nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_notes = Column(Text)
    risk_score = Column(Float, default=0.0)
    compliance_check = Column(JSONB, default={})
    """
    {
        "platform_guidelines": true,
        "no_spam": true,
        "no_fake_engagement": true,
        "no_deceptive_claims": true,
        "tone_appropriate": true,
        "brand_safe": true
    }
    """
    auto_approved = Column(Boolean, default=False)
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    content_item = relationship("ContentItem", back_populates="approval")

    __table_args__ = (
        Index("ix_approvals_workspace_decision", "workspace_id", "decision"),
    )


# ─── Content Performance Metrics ────────────────────────────────────────────

class ContentPerformance(Base):
    __tablename__ = "content_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), unique=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    click_through_rate = Column(Float, default=0.0)
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    cost_per_click = Column(Float, default=0.0)
    cost_per_conversion = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)

    raw_metrics = Column(JSONB, default={})
    fetched_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    content_item = relationship("ContentItem", back_populates="performance")


# ─── Channel Connector Config ───────────────────────────────────────────────

class ChannelConnector(Base):
    __tablename__ = "channel_connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    channel = Column(Enum(ChannelType), nullable=False)
    is_connected = Column(Boolean, default=False)
    account_name = Column(String(255))
    account_id = Column(String(255))

    # Auth (encrypted at rest in production)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    scopes = Column(ARRAY(String), default=[])

    # Rate limiting state
    rate_limit_remaining = Column(Integer)
    rate_limit_reset_at = Column(DateTime(timezone=True))

    # Settings
    automation_level = Column(Integer, default=AutomationLevel.DRAFT_ONLY)
    settings = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "channel", name="uq_workspace_channel"),
    )


# ─── Ad Campaign (Meta Ads layer) ──────────────────────────────────────────

class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    channel = Column(Enum(ChannelType), default=ChannelType.META_ADS)
    name = Column(String(255), nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.PLANNING)
    objective = Column(String(128))  # traffic, conversions, awareness, engagement

    # Ad content
    primary_text = Column(Text)
    headline = Column(String(255))
    description = Column(Text)
    audience_angle = Column(Text)
    placement = Column(JSONB, default={})  # feed, stories, reels, etc.

    # Budget
    daily_budget = Column(Float, default=0.0)
    lifetime_budget = Column(Float, default=0.0)
    bid_strategy = Column(String(64))

    # Targeting
    audience_targeting = Column(JSONB, default={})
    """
    {
        "age_min": 25, "age_max": 55,
        "genders": ["all"],
        "interests": [...],
        "locations": [...],
        "custom_audiences": [...]
    }
    """

    # Tracking
    external_campaign_id = Column(String(255))
    performance = Column(JSONB, default={})

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="ad_campaigns")


# ─── Content Repurposing Log ────────────────────────────────────────────────

class RepurposeLog(Base):
    __tablename__ = "repurpose_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    source_type = Column(String(64), nullable=False)  # blog_post, seo_recommendation, insight
    source_id = Column(UUID(as_uuid=True))
    source_text = Column(Text)
    generated_items = Column(JSONB, default=[])  # list of content_item_ids
    channels_targeted = Column(ARRAY(String), default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())