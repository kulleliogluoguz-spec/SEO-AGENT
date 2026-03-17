"""
Marketing Execution Service
Orchestrates: content generation → compliance check → approval queue → scheduling → publishing → tracking.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.agents.marketing.agents import (
    AgentInput, SocialPostGeneratorAgent, ContentRepurposingAgent,
    CampaignPlannerAgent, ContentCalendarAgent, HookOptimizationAgent,
    HashtagStrategyAgent, ABVariantGeneratorAgent, PerformanceFeedbackAgent,
    AdCampaignGeneratorAgent, PostTimingAgent, ChannelStrategyAgent,
    AudienceTargetingAgent, EngagementOptimizationAgent,
)
from app.connectors.social import ConnectorRegistry, PublishResult
from app.services.marketing.compliance import compliance_service, ComplianceResult

logger = logging.getLogger(__name__)


class MarketingService:
    """
    High-level service layer for the marketing execution engine.
    All content goes through: generate → check → approve → schedule → publish → track.
    
    Agents are initialized once and reused (they are stateless).
    """

    def __init__(self):
        # Initialize agents once — they are stateless, safe to reuse
        self._post_gen = SocialPostGeneratorAgent()
        self._repurpose = ContentRepurposingAgent()
        self._campaign_planner = CampaignPlannerAgent()
        self._calendar = ContentCalendarAgent()
        self._hooks = HookOptimizationAgent()
        self._hashtags = HashtagStrategyAgent()
        self._ab = ABVariantGeneratorAgent()
        self._perf_feedback = PerformanceFeedbackAgent()
        self._ad_gen = AdCampaignGeneratorAgent()
        self._timing = PostTimingAgent()
        self._channel_strategy = ChannelStrategyAgent()

    # ── Content Generation ───────────────────────────────────────────────────

    async def generate_content(
        self,
        workspace_id: str,
        topic: str,
        channels: list[str],
        funnel_stage: str = "awareness",
        target_persona: str = None,
        tone: str = "professional",
        key_points: list[str] = None,
        generate_variants: bool = False,
        num_variants: int = 1,
    ) -> list[dict]:
        """Generate content for multiple channels with compliance checking."""
        generated = []
        post_gen = self._post_gen

        for channel in channels:
            for variant_idx in range(num_variants if generate_variants else 1):
                agent_input = AgentInput(
                    workspace_id=workspace_id,
                    payload={
                        "topic": topic,
                        "channel": channel,
                        "tone": tone,
                        "key_points": key_points or [],
                        "funnel_stage": funnel_stage,
                        "persona": target_persona,
                    },
                )
                result = await post_gen.execute(agent_input)

                if result.success:
                    post = result.data.get("post", {})

                    # Run compliance check
                    compliance = compliance_service.check_content(
                        body=post.get("body", ""),
                        channel=channel,
                        hashtags=post.get("hashtags", []),
                        channel_metadata=post.get("channel_metadata", {}),
                    )

                    generated.append({
                        "channel": channel,
                        "content": post,
                        "compliance": {
                            "passed": compliance.passed,
                            "risk_score": compliance.risk_score,
                            "risk_level": compliance.risk_level,
                            "violations": compliance.violations,
                            "warnings": compliance.warnings,
                        },
                        "variant_label": chr(65 + variant_idx) if generate_variants else None,
                        "status": "draft",
                    })

        return generated

    # ── Content Repurposing ──────────────────────────────────────────────────

    async def repurpose_content(
        self,
        workspace_id: str,
        source_text: str,
        source_type: str = "blog_post",
        target_channels: list[str] = None,
    ) -> list[dict]:
        """Take one piece of content → generate multi-channel posts."""
        channels = target_channels or ["instagram", "twitter", "linkedin", "tiktok"]
        agent = self._repurpose

        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={
                "source_text": source_text,
                "source_type": source_type,
                "target_channels": channels,
            },
        ))

        if not result.success:
            return []

        items = []
        for item in result.data.get("repurposed", []):
            content = item.get("content", {})
            channel = item.get("channel", "")

            compliance = compliance_service.check_content(
                body=content.get("body", ""),
                channel=channel,
                hashtags=content.get("hashtags", []),
                channel_metadata=content.get("channel_metadata", {}),
            )

            items.append({
                "channel": channel,
                "content": content,
                "compliance": {
                    "passed": compliance.passed,
                    "risk_score": compliance.risk_score,
                    "risk_level": compliance.risk_level,
                    "warnings": compliance.warnings,
                },
                "status": "draft",
            })

        return items

    # ── Campaign Planning ────────────────────────────────────────────────────

    async def plan_campaign(
        self,
        workspace_id: str,
        objective: str,
        channels: list[str],
        duration_days: int = 30,
        budget: float = 0.0,
    ) -> dict:
        planner = self._campaign_planner
        result = await planner.execute(AgentInput(
            workspace_id=workspace_id,
            payload={
                "objective": objective,
                "channels": channels,
                "duration_days": duration_days,
                "budget": budget,
            },
        ))
        return result.data.get("campaign_plan", {}) if result.success else {}

    # ── Calendar Generation ──────────────────────────────────────────────────

    async def generate_calendar(
        self,
        workspace_id: str,
        campaign_plan: dict,
        start_date: str = None,
        timezone: str = "UTC",
    ) -> dict:
        cal_agent = self._calendar
        result = await cal_agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={
                "campaign_plan": campaign_plan,
                "start_date": start_date or datetime.utcnow().isoformat(),
                "timezone": timezone,
            },
        ))
        return result.data if result.success else {}

    # ── Publishing ───────────────────────────────────────────────────────────

    async def publish_content(
        self,
        channel: str,
        content: dict,
        access_token: str = None,
        automation_level: int = 0,
    ) -> dict:
        """Publish content through the connector, respecting safety gates."""

        # Compliance recheck before publishing
        compliance = compliance_service.check_content(
            body=content.get("body", ""),
            channel=channel,
            hashtags=content.get("hashtags", []),
            channel_metadata=content.get("channel_metadata", {}),
        )

        # Check automation level
        allowed, reason = compliance_service.check_publishing_allowed(
            automation_level, compliance.risk_level
        )

        if not allowed:
            return {
                "published": False,
                "reason": reason,
                "risk_level": compliance.risk_level,
                "requires_approval": True,
            }

        if not compliance.passed:
            return {
                "published": False,
                "reason": f"Content failed compliance check: {compliance.violations}",
                "risk_level": compliance.risk_level,
            }

        # Get connector and publish
        try:
            connector = ConnectorRegistry.get(channel, access_token=access_token)
            result = await connector.publish(content)

            return {
                "published": result.success,
                "external_id": result.external_id,
                "url": result.url,
                "error": result.error,
            }
        except Exception as e:
            logger.error(f"Publishing failed for {channel}: {e}")
            return {"published": False, "error": str(e)}

    # ── Metrics Fetching ─────────────────────────────────────────────────────

    async def fetch_metrics(self, channel: str, external_id: str,
                            access_token: str = None) -> dict:
        try:
            connector = ConnectorRegistry.get(channel, access_token=access_token)
            result = await connector.get_metrics(external_id)
            return result.metrics if result.success else {}
        except Exception as e:
            logger.error(f"Metrics fetch failed: {e}")
            return {}

    # ── Hook Generation ──────────────────────────────────────────────────────

    async def generate_hooks(self, workspace_id: str, topic: str,
                             channel: str = "instagram", count: int = 5) -> list[dict]:
        agent = self._hooks
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={"topic": topic, "channel": channel, "num_hooks": count},
        ))
        return result.data.get("hooks", []) if result.success else []

    # ── Hashtag Strategy ─────────────────────────────────────────────────────

    async def generate_hashtags(self, workspace_id: str, topic: str,
                                channel: str = "instagram", niche: str = "") -> dict:
        agent = self._hashtags
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={"topic": topic, "channel": channel, "niche": niche},
        ))
        return result.data.get("hashtag_strategy", {}) if result.success else {}

    # ── Optimal Posting Times ────────────────────────────────────────────────

    async def get_optimal_times(self, workspace_id: str, channel: str,
                                timezone: str = "UTC") -> dict:
        agent = self._timing
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={"channel": channel, "timezone": timezone},
        ))
        return result.data if result.success else {}

    # ── Channel Strategy ─────────────────────────────────────────────────────

    async def get_channel_strategy(self, workspace_id: str,
                                   goals: list[str] = None,
                                   industry: str = "") -> dict:
        agent = self._channel_strategy
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={"goals": goals or ["awareness"], "industry": industry},
        ))
        return result.data.get("strategy", {}) if result.success else {}

    # ── Ad Campaign Generation ───────────────────────────────────────────────

    async def generate_ad_campaign(self, workspace_id: str, **kwargs) -> dict:
        agent = self._ad_gen
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id, payload=kwargs,
        ))
        return result.data.get("ad_campaign", {}) if result.success else {}

    # ── Performance Feedback ─────────────────────────────────────────────────

    async def get_performance_feedback(self, workspace_id: str,
                                       metrics: list[dict],
                                       channel: str = None) -> dict:
        agent = self._perf_feedback
        result = await agent.execute(AgentInput(
            workspace_id=workspace_id,
            payload={"metrics": metrics, "channel": channel},
        ))
        return result.data.get("feedback", {}) if result.success else {}


# Singleton
marketing_service = MarketingService()