"""Add growth intelligence tables: source_connections, source_documents, trends,
   audience_segments, brand_profiles, geo_audits, seo_audits, personas, topics,
   competitor_profiles.

Revision ID: 20260328_0003
Revises: mktg_001
Create Date: 2026-03-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260328_0003"
down_revision = "mktg_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── source_connections ─────────────────────────────────────────────────────
    # Stores connector configurations per workspace.
    op.create_table(
        "source_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_type", sa.String(64), nullable=False),           # "rss", "reddit", "ga4", etc.
        sa.Column("compliance_mode", sa.String(32), nullable=False),       # "official_api" | "public_web" | "user_upload"
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("credentials_ref", sa.String(512)),                      # Reference to encrypted secret, NOT stored here
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("fetch_interval_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("max_documents_per_run", sa.Integer, nullable=False, server_default="500"),
        sa.Column("last_fetch_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── source_documents ────────────────────────────────────────────────────────
    # Raw normalized documents ingested from any source connector.
    op.create_table(
        "source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_connections.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.String(64), nullable=False, index=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, index=True),  # SHA-256, for dedup
        sa.Column("title", sa.Text, server_default=""),
        sa.Column("author", sa.String(255), server_default=""),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("compliance_mode", sa.String(32), nullable=False),
        sa.Column("embedding_id", sa.String(255)),                         # Qdrant point ID
        sa.Column("embedding_model", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_source_documents_workspace_source", "source_documents", ["workspace_id", "source_type"])
    op.create_index("ix_source_documents_content_hash", "source_documents", ["content_hash"])

    # ── topics ─────────────────────────────────────────────────────────────────
    # Canonical topic/keyword entities extracted from documents.
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True),  # NULL = global topic
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, index=True),
        sa.Column("category", sa.String(64), server_default="general"),    # "pain_point" | "solution" | "competitor" | "trend" | etc.
        sa.Column("aliases", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── trends ─────────────────────────────────────────────────────────────────
    # Detected trend records with scoring, evidence, and workspace relevance.
    op.create_table(
        "trends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("keywords", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("category", sa.String(64), server_default="general"),
        sa.Column("momentum_score", sa.Float, server_default="0.0"),       # Rising = high
        sa.Column("relevance_score", sa.Float, server_default="0.0"),      # Relevance to this workspace's brand
        sa.Column("volume_7d", sa.Integer, server_default="0"),            # Document count in last 7 days
        sa.Column("sentiment", sa.Float, server_default="0.0"),            # -1 to 1
        sa.Column("source_types", postgresql.ARRAY(sa.Text), server_default="{}"),  # Which sources contributed
        sa.Column("evidence", postgresql.JSONB, server_default="[]"),      # Sample posts/excerpts
        sa.Column("source_document_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default="{}"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),               # Trend decay
        sa.Column("status", sa.String(32), server_default="active"),       # "active" | "declining" | "expired"
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_trends_workspace_momentum", "trends", ["workspace_id", "momentum_score"])
    op.create_index("ix_trends_workspace_relevance", "trends", ["workspace_id", "relevance_score"])

    # ── brand_profiles ─────────────────────────────────────────────────────────
    # Structured intelligence extracted from a brand's website and connected data.
    op.create_table(
        "brand_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="SET NULL")),
        sa.Column("brand_name", sa.String(255), server_default=""),
        sa.Column("value_proposition", sa.Text, server_default=""),
        sa.Column("target_audience", sa.Text, server_default=""),
        sa.Column("icp_description", sa.Text, server_default=""),
        sa.Column("product_features", postgresql.JSONB, server_default="[]"),
        sa.Column("positioning_keywords", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("use_cases", postgresql.JSONB, server_default="[]"),
        sa.Column("pricing_model", sa.String(64), server_default="unknown"),
        sa.Column("trust_signals", postgresql.JSONB, server_default="[]"),
        sa.Column("content_topics", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("competitors", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("social_handles", postgresql.JSONB, server_default="{}"),
        sa.Column("conversion_goals", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("built_from_crawl_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ai_model_used", sa.String(128), server_default=""),
        sa.Column("confidence_score", sa.Float, server_default="0.0"),
        sa.Column("last_rebuilt_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── personas ───────────────────────────────────────────────────────────────
    # Buyer persona definitions derived from brand + audience analysis.
    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("job_titles", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("pain_points", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("goals", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("channels", postgresql.ARRAY(sa.Text), server_default="{}"),        # Where they hang out
        sa.Column("keywords", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("demographics", postgresql.JSONB, server_default="{}"),
        sa.Column("intent_signals", postgresql.JSONB, server_default="{}"),
        sa.Column("fit_score", sa.Float, server_default="0.0"),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── audience_segments ──────────────────────────────────────────────────────
    # Defined audience clusters derived from signal analysis.
    op.create_table(
        "audience_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("defining_signals", postgresql.JSONB, server_default="{}"),  # keywords, communities, behaviors
        sa.Column("estimated_size", sa.Integer, server_default="0"),
        sa.Column("intent_score", sa.Float, server_default="0.0"),              # Purchase intent (0-1)
        sa.Column("fit_score", sa.Float, server_default="0.0"),                 # Brand fit (0-1)
        sa.Column("channel_distribution", postgresql.JSONB, server_default="{}"),  # e.g. {reddit: 0.4, twitter: 0.3}
        sa.Column("persona_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default="{}"),
        sa.Column("trend_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default="{}"),
        sa.Column("community_sources", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── geo_audits ─────────────────────────────────────────────────────────────
    # GEO (Generative Engine Optimization) audit results.
    op.create_table(
        "geo_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),      # "pending" | "running" | "complete" | "failed"
        sa.Column("overall_score", sa.Float, server_default="0.0"),        # 0-100
        sa.Column("citability_score", sa.Float, server_default="0.0"),
        sa.Column("ai_crawler_score", sa.Float, server_default="0.0"),
        sa.Column("schema_score", sa.Float, server_default="0.0"),
        sa.Column("entity_score", sa.Float, server_default="0.0"),
        sa.Column("content_clarity_score", sa.Float, server_default="0.0"),
        sa.Column("llms_txt_present", sa.Boolean, server_default="false"),
        sa.Column("llms_txt_quality", sa.Float, server_default="0.0"),
        sa.Column("robots_txt_allows_ai", sa.Boolean, server_default="true"),
        sa.Column("structured_data_types", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("issues", postgresql.JSONB, server_default="[]"),        # List of issue objects
        sa.Column("recommendations", postgresql.JSONB, server_default="[]"),
        sa.Column("evidence", postgresql.JSONB, server_default="{}"),
        sa.Column("ai_model_used", sa.String(128), server_default=""),
        sa.Column("audit_duration_seconds", sa.Integer, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── seo_audits ─────────────────────────────────────────────────────────────
    # Technical SEO audit results.
    op.create_table(
        "seo_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crawl_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crawls.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("overall_score", sa.Float, server_default="0.0"),
        sa.Column("technical_score", sa.Float, server_default="0.0"),
        sa.Column("content_score", sa.Float, server_default="0.0"),
        sa.Column("performance_score", sa.Float, server_default="0.0"),
        sa.Column("indexability_score", sa.Float, server_default="0.0"),
        sa.Column("pages_audited", sa.Integer, server_default="0"),
        sa.Column("issues", postgresql.JSONB, server_default="[]"),
        sa.Column("recommendations", postgresql.JSONB, server_default="[]"),
        sa.Column("core_web_vitals", postgresql.JSONB, server_default="{}"),
        sa.Column("canonical_issues", postgresql.JSONB, server_default="[]"),
        sa.Column("metadata_issues", postgresql.JSONB, server_default="[]"),
        sa.Column("link_issues", postgresql.JSONB, server_default="[]"),
        sa.Column("ai_model_used", sa.String(128), server_default=""),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── competitor_profiles ────────────────────────────────────────────────────
    # Tracked competitor intelligence.
    op.create_table(
        "competitor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("positioning", sa.Text, server_default=""),
        sa.Column("strengths", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("weaknesses", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("keywords", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("competitor_profiles")
    op.drop_table("seo_audits")
    op.drop_table("geo_audits")
    op.drop_table("audience_segments")
    op.drop_table("personas")
    op.drop_table("brand_profiles")
    op.drop_table("trends")
    op.drop_table("topics")
    op.drop_table("source_documents")
    op.drop_table("source_connections")
