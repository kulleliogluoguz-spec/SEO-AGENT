"""Ad Analytics Platform tables: ad_accounts, analytics_ad_campaigns, ad_performance_daily,
ai_recommendations, budget_optimizations, mmm_models, ad_forecasts.

Note: analytics_ad_campaigns is prefixed to avoid collision with the existing
ad_campaigns table from mktg_001 (which holds creative copy, not performance data).

Revision ID: 20260407_0004
Revises: 20260328_0003
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260407_0004"
down_revision = "20260328_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ad Accounts (Google + Meta connections)
    op.create_table(
        "ad_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("account_name", sa.String(500)),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("credentials", JSONB),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ad_accounts_workspace", "ad_accounts", ["workspace_id"])
    op.create_index("ix_ad_accounts_platform", "ad_accounts", ["platform"])

    # 2. Campaigns (synced from Google/Meta)
    op.create_table(
        "analytics_ad_campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ad_account_id", UUID(as_uuid=True), sa.ForeignKey("ad_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_campaign_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(500)),
        sa.Column("status", sa.String(50)),
        sa.Column("campaign_type", sa.String(100)),
        sa.Column("daily_budget", sa.Numeric(12, 2)),
        sa.Column("total_budget", sa.Numeric(12, 2)),
        sa.Column("objective", sa.String(100)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("platform_data", JSONB),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ad_account_id", "platform_campaign_id", name="uq_ad_campaign"),
    )
    op.create_index("ix_ad_campaigns_account", "analytics_ad_campaigns", ["ad_account_id"])
    op.create_index("ix_ad_campaigns_status", "analytics_ad_campaigns", ["status"])

    # 3. Daily Performance Metrics (time-series data)
    op.create_table(
        "ad_performance_daily",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("analytics_ad_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("impressions", sa.BigInteger, server_default="0"),
        sa.Column("clicks", sa.BigInteger, server_default="0"),
        sa.Column("conversions", sa.Numeric(10, 2), server_default="0"),
        sa.Column("spend", sa.Numeric(12, 4), server_default="0"),
        sa.Column("revenue", sa.Numeric(14, 4), server_default="0"),
        sa.Column("roas", sa.Numeric(10, 4)),
        sa.Column("cpa", sa.Numeric(12, 4)),
        sa.Column("ctr", sa.Numeric(8, 6)),
        sa.Column("cvr", sa.Numeric(8, 6)),
        sa.Column("cpm", sa.Numeric(12, 4)),
        sa.Column("cpc", sa.Numeric(12, 4)),
        sa.Column("frequency", sa.Numeric(8, 4)),
        sa.Column("reach", sa.BigInteger),
        sa.Column("raw_data", JSONB),
        sa.UniqueConstraint("campaign_id", "date", name="uq_campaign_date"),
    )
    op.create_index("ix_perf_campaign_date", "ad_performance_daily", ["campaign_id", "date"])

    # 4. AI Recommendations
    op.create_table(
        "ai_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("analytics_ad_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendation_type", sa.String(100)),
        sa.Column("priority", sa.String(20)),
        sa.Column("title", sa.String(500)),
        sa.Column("description", sa.Text),
        sa.Column("expected_impact", sa.String(200)),
        sa.Column("action_data", JSONB),
        sa.Column("ai_reasoning", sa.Text),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_recommendations_workspace_status", "ai_recommendations", ["workspace_id", "status"])
    op.create_index("ix_ai_recommendations_priority", "ai_recommendations", ["priority"])

    # 5. Budget Optimization Results (from MMM)
    op.create_table(
        "budget_optimizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("total_budget", sa.Numeric(14, 2)),
        sa.Column("optimization_date", sa.Date),
        sa.Column("current_allocation", JSONB),
        sa.Column("optimal_allocation", JSONB),
        sa.Column("expected_roas_current", sa.Numeric(10, 4)),
        sa.Column("expected_roas_optimal", sa.Numeric(10, 4)),
        sa.Column("expected_uplift_pct", sa.Numeric(8, 4)),
        sa.Column("model_params", JSONB),
        sa.Column("status", sa.String(50), server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_budget_opt_workspace", "budget_optimizations", ["workspace_id"])

    # 6. MMM Model Store
    op.create_table(
        "mmm_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("model_version", sa.String(50)),
        sa.Column("training_start_date", sa.Date),
        sa.Column("training_end_date", sa.Date),
        sa.Column("channels", JSONB),
        sa.Column("model_metrics", JSONB),
        sa.Column("channel_contributions", JSONB),
        sa.Column("saturation_params", JSONB),
        sa.Column("adstock_params", JSONB),
        sa.Column("model_path", sa.String(500)),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false")),
        sa.Column("trained_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mmm_workspace_active", "mmm_models", ["workspace_id", "is_active"])

    # 7. Forecasts
    op.create_table(
        "ad_forecasts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("analytics_ad_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("forecast_date", sa.Date),
        sa.Column("metric", sa.String(50)),
        sa.Column("predicted_value", sa.Numeric(14, 4)),
        sa.Column("lower_bound", sa.Numeric(14, 4)),
        sa.Column("upper_bound", sa.Numeric(14, 4)),
        sa.Column("confidence_level", sa.Numeric(5, 4), server_default="0.95"),
        sa.Column("model_type", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecasts_campaign_date", "ad_forecasts", ["campaign_id", "forecast_date"])
    op.create_index("ix_forecasts_metric", "ad_forecasts", ["metric"])


def downgrade() -> None:
    op.drop_table("ad_forecasts")
    op.drop_table("mmm_models")
    op.drop_table("budget_optimizations")
    op.drop_table("ai_recommendations")
    op.drop_table("ad_performance_daily")
    op.drop_table("analytics_ad_campaigns")
    op.drop_table("ad_accounts")
