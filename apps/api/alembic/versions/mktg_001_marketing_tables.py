"""Add marketing execution engine tables

Revision ID: mktg_001
Revises: (initial migration)
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = 'mktg_001'
down_revision = None  # Chain to your existing initial migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Campaigns ────────────────────────────────────────────────────────────
    op.create_table(
        'campaigns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(32), server_default='planning', nullable=False),
        sa.Column('objective', sa.String(255)),
        sa.Column('funnel_stage', sa.String(32)),
        sa.Column('target_channels', ARRAY(sa.String), server_default='{}'),
        sa.Column('target_personas', JSONB, server_default='[]'),
        sa.Column('budget', sa.Float, server_default='0'),
        sa.Column('start_date', sa.DateTime(timezone=True)),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('tags', ARRAY(sa.String), server_default='{}'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_campaigns_workspace_status', 'campaigns', ['workspace_id', 'status'])

    # ── Content Items ────────────────────────────────────────────────────────
    op.create_table(
        'content_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id')),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), server_default='draft', nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('hook', sa.Text),
        sa.Column('cta', sa.Text),
        sa.Column('hashtags', ARRAY(sa.String), server_default='{}'),
        sa.Column('media_instructions', sa.Text),
        sa.Column('channel_metadata', JSONB, server_default='{}'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('timezone', sa.String(64), server_default="'UTC'"),
        sa.Column('funnel_stage', sa.String(32)),
        sa.Column('target_persona', sa.String(255)),
        sa.Column('risk_level', sa.String(16), server_default="'low'"),
        sa.Column('compliance_notes', JSONB, server_default='[]'),
        sa.Column('policy_warnings', JSONB, server_default='[]'),
        sa.Column('source_type', sa.String(64)),
        sa.Column('source_id', UUID(as_uuid=True)),
        sa.Column('variant_group', UUID(as_uuid=True)),
        sa.Column('variant_label', sa.String(32)),
        sa.Column('external_post_id', sa.String(255)),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_content_workspace_status', 'content_items', ['workspace_id', 'status'])
    op.create_index('ix_content_workspace_channel', 'content_items', ['workspace_id', 'channel'])
    op.create_index('ix_content_scheduled', 'content_items', ['scheduled_at'])
    op.create_index('ix_content_variant_group', 'content_items', ['variant_group'])

    # ── Content Approvals ────────────────────────────────────────────────────
    op.create_table(
        'content_approvals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('content_item_id', UUID(as_uuid=True), sa.ForeignKey('content_items.id'), unique=True, nullable=False),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('decision', sa.String(32), server_default='pending', nullable=False),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('review_notes', sa.Text),
        sa.Column('risk_score', sa.Float, server_default='0'),
        sa.Column('compliance_check', JSONB, server_default='{}'),
        sa.Column('auto_approved', sa.Boolean, server_default='false'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_approvals_workspace_decision', 'content_approvals', ['workspace_id', 'decision'])

    # ── Content Performance ──────────────────────────────────────────────────
    op.create_table(
        'content_performance',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('content_item_id', UUID(as_uuid=True), sa.ForeignKey('content_items.id'), unique=True, nullable=False),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('impressions', sa.Integer, server_default='0'),
        sa.Column('reach', sa.Integer, server_default='0'),
        sa.Column('clicks', sa.Integer, server_default='0'),
        sa.Column('likes', sa.Integer, server_default='0'),
        sa.Column('comments', sa.Integer, server_default='0'),
        sa.Column('shares', sa.Integer, server_default='0'),
        sa.Column('saves', sa.Integer, server_default='0'),
        sa.Column('engagement_rate', sa.Float, server_default='0'),
        sa.Column('click_through_rate', sa.Float, server_default='0'),
        sa.Column('conversions', sa.Integer, server_default='0'),
        sa.Column('conversion_rate', sa.Float, server_default='0'),
        sa.Column('cost', sa.Float, server_default='0'),
        sa.Column('cost_per_click', sa.Float, server_default='0'),
        sa.Column('cost_per_conversion', sa.Float, server_default='0'),
        sa.Column('revenue', sa.Float, server_default='0'),
        sa.Column('roas', sa.Float, server_default='0'),
        sa.Column('raw_metrics', JSONB, server_default='{}'),
        sa.Column('fetched_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Channel Connectors ───────────────────────────────────────────────────
    op.create_table(
        'channel_connectors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('is_connected', sa.Boolean, server_default='false'),
        sa.Column('account_name', sa.String(255)),
        sa.Column('account_id', sa.String(255)),
        sa.Column('access_token', sa.Text),
        sa.Column('refresh_token', sa.Text),
        sa.Column('token_expires_at', sa.DateTime(timezone=True)),
        sa.Column('scopes', ARRAY(sa.String), server_default='{}'),
        sa.Column('rate_limit_remaining', sa.Integer),
        sa.Column('rate_limit_reset_at', sa.DateTime(timezone=True)),
        sa.Column('automation_level', sa.Integer, server_default='0'),
        sa.Column('settings', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_workspace_channel', 'channel_connectors', ['workspace_id', 'channel'])

    # ── Ad Campaigns ─────────────────────────────────────────────────────────
    op.create_table(
        'ad_campaigns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id')),
        sa.Column('channel', sa.String(32), server_default="'meta_ads'"),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(32), server_default='planning'),
        sa.Column('objective', sa.String(128)),
        sa.Column('primary_text', sa.Text),
        sa.Column('headline', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('audience_angle', sa.Text),
        sa.Column('placement', JSONB, server_default='{}'),
        sa.Column('daily_budget', sa.Float, server_default='0'),
        sa.Column('lifetime_budget', sa.Float, server_default='0'),
        sa.Column('bid_strategy', sa.String(64)),
        sa.Column('audience_targeting', JSONB, server_default='{}'),
        sa.Column('external_campaign_id', sa.String(255)),
        sa.Column('performance', JSONB, server_default='{}'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Repurpose Logs ───────────────────────────────────────────────────────
    op.create_table(
        'repurpose_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('source_type', sa.String(64), nullable=False),
        sa.Column('source_id', UUID(as_uuid=True)),
        sa.Column('source_text', sa.Text),
        sa.Column('generated_items', JSONB, server_default='[]'),
        sa.Column('channels_targeted', ARRAY(sa.String), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('repurpose_logs')
    op.drop_table('ad_campaigns')
    op.drop_table('channel_connectors')
    op.drop_table('content_performance')
    op.drop_table('content_approvals')
    op.drop_table('content_items')
    op.drop_table('campaigns')
