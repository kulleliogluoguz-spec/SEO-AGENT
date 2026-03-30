"""
PolicyGateAgent — Layer 0

Evaluates proposed actions against workspace autonomy policy.
Blocks actions that exceed the configured autonomy level.
Every consequential agent should call the PolicyGateAgent before executing.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, BaseAgent


class PolicyCheckInput(BaseModel):
    action_type: str          # e.g. "publish_content", "send_notification", "update_meta"
    action_description: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    risk_level: str = "medium"  # low | medium | high | critical
    proposed_autonomy_level: int = 1


class PolicyCheckOutput(BaseModel):
    allowed: bool
    reason: str
    required_autonomy_level: int
    actual_autonomy_level: int
    approval_required: bool
    policy_flags: list[str]


# Actions requiring at least these autonomy levels
ACTION_AUTONOMY_REQUIREMENTS: dict[str, int] = {
    # Level 0 — always allowed (read only)
    "analyze_site": 0,
    "generate_recommendations": 0,
    "crawl_site": 0,

    # Level 1 — draft generation (default)
    "generate_content_draft": 1,
    "generate_report": 1,
    "create_brief": 1,

    # Level 2 — approval required for execution
    "update_meta_tags": 2,
    "send_notification": 2,
    "submit_for_review": 2,

    # Level 3 — low-risk auto execution
    "publish_meta_update": 3,
    "send_approved_notification": 3,

    # Level 4 — advanced automation (disabled by default)
    "publish_content": 4,
    "post_social": 4,
    "send_email_campaign": 4,
}

# Actions that always require human approval regardless of autonomy level
ALWAYS_APPROVAL_REQUIRED = {
    "post_social",
    "post_reddit",
    "post_hackernews",
    "send_email_campaign",
    "publish_content",
    "update_pricing_page",
}

# Prohibited actions — never execute, ever
PROHIBITED_ACTIONS = {
    "send_spam",
    "generate_fake_review",
    "generate_fake_testimonial",
    "fabricate_customer_story",
    "post_deceptive_content",
    "bypass_platform_rules",
}


class PolicyGateAgent(BaseAgent[PolicyCheckInput, PolicyCheckOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="PolicyGateAgent",
        layer=0,
        description="Evaluates actions against workspace autonomy policy",
        requires_llm=False,
        timeout_seconds=5,
    )

    async def _execute(
        self,
        input_data: PolicyCheckInput,
        context: AgentRunContext,
    ) -> PolicyCheckOutput:
        action = input_data.action_type
        flags: list[str] = []

        # Check prohibited actions first
        if action in PROHIBITED_ACTIONS:
            return PolicyCheckOutput(
                allowed=False,
                reason=f"Action '{action}' is explicitly prohibited by platform policy. "
                       "AI CMO OS does not support spam, fake reviews, or deceptive content.",
                required_autonomy_level=5,  # Never allowed
                actual_autonomy_level=context.autonomy_level,
                approval_required=True,
                policy_flags=[f"PROHIBITED: {action}"],
            )

        # Look up required autonomy level
        required = ACTION_AUTONOMY_REQUIREMENTS.get(action, 2)  # Default: require level 2

        # Check autonomy level gate
        if context.autonomy_level < required:
            return PolicyCheckOutput(
                allowed=False,
                reason=(
                    f"Action '{action}' requires autonomy level {required}, "
                    f"but workspace is configured at level {context.autonomy_level}. "
                    f"Upgrade the workspace autonomy level to proceed."
                ),
                required_autonomy_level=required,
                actual_autonomy_level=context.autonomy_level,
                approval_required=True,
                policy_flags=[f"AUTONOMY_LEVEL_INSUFFICIENT: requires {required}, have {context.autonomy_level}"],
            )

        # Check risk level gating
        if input_data.risk_level == "critical" and context.autonomy_level < 4:
            flags.append("HIGH_RISK_ACTION: requires manual review")

        # Check if approval is always required for this action type
        approval_required = (
            action in ALWAYS_APPROVAL_REQUIRED
            or input_data.risk_level in ("high", "critical")
            or context.autonomy_level < 3
        )

        if approval_required:
            flags.append("APPROVAL_REQUIRED: item will be queued for human review")

        return PolicyCheckOutput(
            allowed=True,
            reason="Action permitted under current autonomy policy.",
            required_autonomy_level=required,
            actual_autonomy_level=context.autonomy_level,
            approval_required=approval_required,
            policy_flags=flags,
        )
