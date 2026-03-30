"""
Pydantic v2 schemas for API request/response validation.
Strict typing, no silent coercion for security-sensitive fields.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


# ─── Base Schemas ─────────────────────────────────────────────────────────────

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseSchema):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ─── Users ────────────────────────────────────────────────────────────────────

class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime
    workspace_id: uuid.UUID | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    avatar_url: str | None = None


# ─── Organizations ────────────────────────────────────────────────────────────

class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrgResponse(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: datetime


# ─── Workspaces ───────────────────────────────────────────────────────────────

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    autonomy_level: int = Field(default=1, ge=0, le=3)


class WorkspaceResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    autonomy_level: int
    is_active: bool
    created_at: datetime


# ─── Sites ────────────────────────────────────────────────────────────────────

class SiteOnboardRequest(BaseModel):
    url: str = Field(description="The website URL to onboard")
    name: str | None = Field(None, max_length=255)
    max_pages: int = Field(default=100, ge=1, le=1000)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")


class SiteResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    url: str
    domain: str
    name: str | None
    status: str
    product_summary: str | None
    category: str | None
    icp_summary: str | None
    last_crawled_at: datetime | None
    created_at: datetime


# ─── Crawls ───────────────────────────────────────────────────────────────────

class CrawlResponse(BaseSchema):
    id: uuid.UUID
    site_id: uuid.UUID
    status: str
    max_pages: int
    pages_crawled: int
    pages_failed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class CrawlPageResponse(BaseSchema):
    id: uuid.UUID
    crawl_id: uuid.UUID
    url: str
    status_code: int | None
    title: str | None
    meta_description: str | None
    h1: str | None
    word_count: int
    issues: list[dict]
    crawled_at: datetime


# ─── Recommendations ──────────────────────────────────────────────────────────

class RecommendationResponse(BaseSchema):
    id: uuid.UUID
    site_id: uuid.UUID
    title: str
    category: str
    subcategory: str | None
    summary: str
    rationale: str
    evidence: list[dict]
    affected_urls: list[str]
    proposed_action: str | None
    impact_score: float
    effort_score: float
    confidence_score: float
    urgency_score: float
    priority_score: float
    target_metric: str | None
    risk_flags: list[str]
    status: str
    approval_required: bool
    generated_by_agent: str | None
    created_at: datetime


class RecommendationUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


# ─── Content ──────────────────────────────────────────────────────────────────

class ContentBriefRequest(BaseModel):
    site_id: uuid.UUID
    content_type: str = Field(description="blog|landing_page|comparison|faq|social_post")
    topic: str = Field(min_length=1, max_length=512)
    target_keyword: str | None = None
    tone: str = Field(default="professional")
    word_count_target: int | None = None
    notes: str | None = None


class ContentAssetResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    asset_type: str
    status: str
    content: str | None
    brief: dict
    compliance_flags: list
    risk_score: float
    created_at: datetime


class ContentGenerateRequest(BaseModel):
    brief_id: uuid.UUID
    model: str | None = None


# ─── Approvals ────────────────────────────────────────────────────────────────

class ApprovalResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    title: str
    description: str | None
    risk_level: str
    policy_flags: list
    status: str
    created_at: datetime


class ApprovalActionRequest(BaseModel):
    action: str = Field(description="approve|reject")
    note: str | None = None


# ─── Reports ─────────────────────────────────────────────────────────────────

class ReportResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    report_type: str
    title: str
    summary: str | None
    kpis: dict
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime


class ReportDetailResponse(ReportResponse):
    content_md: str | None
    sections: list[dict]


# ─── Error Responses ──────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: str
    details: list[ErrorDetail] = []
    request_id: str | None = None
