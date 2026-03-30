"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates all core tables for AI CMO OS.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enable extensions ────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── organizations ────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # ── memberships ──────────────────────────────────────────────────────────
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    # ── workspaces ───────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("autonomy_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )

    # ── sites ────────────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("product_summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("icp_summary", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sites_domain", "sites", ["domain"])
    op.create_index("ix_sites_workspace_id", "sites", ["workspace_id"])

    # ── crawls ───────────────────────────────────────────────────────────────
    op.create_table(
        "crawls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("pages_crawled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("crawl_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_crawls_site_id_status", "crawls", ["site_id", "status"])

    # ── crawl_pages ──────────────────────────────────────────────────────────
    op.create_table(
        "crawl_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("crawl_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("h1", sa.String(512), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("structured_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("meta_tags", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("internal_links", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("external_links", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("issues", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("screenshot_path", sa.String(512), nullable=True),
        sa.Column("rendered_fallback", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("crawl_id", "url", name="uq_crawl_page_url"),
    )
    op.create_index("ix_crawl_pages_crawl_id", "crawl_pages", ["crawl_id"])

    # ── recommendations ──────────────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("affected_urls", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("proposed_action", sa.Text(), nullable=True),
        sa.Column("rollback_plan", sa.Text(), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("effort_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("urgency_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("target_metric", sa.String(100), nullable=True),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("generated_by_agent", sa.String(100), nullable=True),
        sa.Column("generated_by_workflow", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendations_site_status", "recommendations", ["site_id", "status"])
    op.create_index("ix_recommendations_priority", "recommendations", ["priority_score"])
    op.create_index("ix_recommendations_category", "recommendations", ["category"])

    # ── content_assets ───────────────────────────────────────────────────────
    op.create_table(
        "content_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("brief", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("compliance_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("generated_by_agent", sa.String(100), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_content_assets_workspace_type", "content_assets", ["workspace_id", "asset_type"])
    op.create_index("ix_content_assets_status", "content_assets", ["status"])

    # ── approvals ────────────────────────────────────────────────────────────
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("policy_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_approvals_workspace_status", "approvals", ["workspace_id", "status"])
    op.create_index("ix_approvals_entity", "approvals", ["entity_type", "entity_id"])

    # ── reports ──────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("kpis", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by_agent", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reports_workspace_type", "reports", ["workspace_id", "report_type"])

    # ── agent_runs ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("input_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_name", "agent_runs", ["agent_name"])
    op.create_index("ix_agent_runs_workspace", "agent_runs", ["workspace_id"])

    # ── activity_logs ────────────────────────────────────────────────────────
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_activity_workspace_created", "activity_logs", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_table("activity_logs")
    op.drop_table("agent_runs")
    op.drop_table("reports")
    op.drop_table("approvals")
    op.drop_table("content_assets")
    op.drop_table("recommendations")
    op.drop_table("crawl_pages")
    op.drop_table("crawls")
    op.drop_table("sites")
    op.drop_table("workspaces")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")
