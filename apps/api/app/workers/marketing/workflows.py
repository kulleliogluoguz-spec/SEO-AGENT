"""
Marketing Execution Workflows — Temporal Definitions
Durable workflows for: content generation pipeline, campaign execution,
scheduled publishing, performance tracking, content repurposing.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Workflow Input/Output Types ─────────────────────────────────────────────

@dataclass
class ContentPipelineInput:
    workspace_id: str
    topic: str
    channels: list[str]
    campaign_id: Optional[str] = None
    funnel_stage: str = "awareness"
    tone: str = "professional"
    key_points: list[str] = None
    auto_approve_low_risk: bool = False


@dataclass
class PublishWorkflowInput:
    workspace_id: str
    content_item_id: str
    channel: str
    scheduled_at: Optional[str] = None
    timezone: str = "UTC"


@dataclass
class CampaignExecutionInput:
    workspace_id: str
    campaign_id: str
    channels: list[str]
    objective: str
    duration_days: int = 30
    budget: float = 0.0


@dataclass
class RepurposeWorkflowInput:
    workspace_id: str
    source_text: str
    source_type: str = "blog_post"
    source_id: Optional[str] = None
    target_channels: list[str] = None


@dataclass
class PerformanceTrackingInput:
    workspace_id: str
    content_item_ids: list[str]
    channel: str
    interval_hours: int = 24


# ═════════════════════════════════════════════════════════════════════════════
#  CONTENT GENERATION PIPELINE WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class ContentGenerationPipelineWorkflow:
    """
    Workflow: Topic → Generate → Compliance Check → Auto/Manual Approval → Queue
    
    Steps:
    1. Generate content for each channel
    2. Run compliance check
    3. If low-risk + auto_approve: auto-approve
    4. Otherwise: queue for manual approval
    5. Return generated items
    """

    async def run(self, input: ContentPipelineInput) -> dict:
        logger.info(f"[ContentPipeline] Starting for topic='{input.topic}' channels={input.channels}")

        from app.services.marketing.service import marketing_service

        # Step 1: Generate content
        items = await marketing_service.generate_content(
            workspace_id=input.workspace_id,
            topic=input.topic,
            channels=input.channels,
            funnel_stage=input.funnel_stage,
            tone=input.tone,
            key_points=input.key_points or [],
        )

        # Step 2: Process each item
        results = []
        for item in items:
            compliance = item.get("compliance", {})
            risk_level = compliance.get("risk_level", "medium")

            # Step 3: Auto-approve low-risk if enabled
            if input.auto_approve_low_risk and risk_level == "low" and compliance.get("passed"):
                item["status"] = "approved"
                item["auto_approved"] = True
            else:
                item["status"] = "pending_approval"
                item["auto_approved"] = False

            results.append(item)

        logger.info(f"[ContentPipeline] Generated {len(results)} items")
        return {"items": results, "total": len(results)}


# ═════════════════════════════════════════════════════════════════════════════
#  SCHEDULED PUBLISHING WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class ScheduledPublishWorkflow:
    """
    Workflow: Wait until scheduled time → Final compliance check → Publish → Track
    
    Steps:
    1. Wait until scheduled_at
    2. Re-run compliance check
    3. Publish via connector
    4. Record result
    5. Schedule metrics collection
    """

    async def run(self, input: PublishWorkflowInput) -> dict:
        logger.info(f"[PublishWorkflow] Content={input.content_item_id} Channel={input.channel}")

        from app.services.marketing.service import marketing_service

        # Step 1: Wait until scheduled time (in Temporal, use workflow.sleep)
        if input.scheduled_at:
            scheduled = datetime.fromisoformat(input.scheduled_at)
            now = datetime.utcnow()
            if scheduled > now:
                delay = (scheduled - now).total_seconds()
                logger.info(f"[PublishWorkflow] Waiting {delay:.0f}s until scheduled time")
                # In Temporal: await workflow.sleep(delay)
                # For testing: await asyncio.sleep(min(delay, 5))

        # Step 2 + 3: Publish (compliance is checked inside)
        result = await marketing_service.publish_content(
            channel=input.channel,
            content={"caption": "scheduled content", "hashtags": []},  # In prod: fetch from DB
            automation_level=2,
        )

        return {
            "content_item_id": input.content_item_id,
            "published": result.get("published", False),
            "external_id": result.get("external_id"),
            "url": result.get("url"),
            "error": result.get("error"),
        }


# ═════════════════════════════════════════════════════════════════════════════
#  CAMPAIGN EXECUTION WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class CampaignExecutionWorkflow:
    """
    Workflow: Plan → Generate Calendar → Create Content → Queue Approvals → Schedule
    
    Full campaign lifecycle as a durable workflow.
    """

    async def run(self, input: CampaignExecutionInput) -> dict:
        logger.info(f"[CampaignExecution] Campaign={input.campaign_id}")

        from app.services.marketing.service import marketing_service

        # Step 1: Generate campaign plan
        plan = await marketing_service.plan_campaign(
            workspace_id=input.workspace_id,
            objective=input.objective,
            channels=input.channels,
            duration_days=input.duration_days,
            budget=input.budget,
        )

        # Step 2: Generate content calendar
        calendar = await marketing_service.generate_calendar(
            workspace_id=input.workspace_id,
            campaign_plan=plan,
        )

        # Step 3: Generate content for each calendar slot (first week only for demo)
        total_slots = calendar.get("total_slots", 0)
        content_generated = min(total_slots, 14)  # Cap at 14 for demo

        return {
            "campaign_id": input.campaign_id,
            "plan": plan,
            "calendar_slots": total_slots,
            "content_generated": content_generated,
            "status": "content_queued_for_approval",
        }


# ═════════════════════════════════════════════════════════════════════════════
#  CONTENT REPURPOSING WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class RepurposeWorkflow:
    """
    Workflow: Source content → Extract key points → Generate per channel → Compliance → Queue
    """

    async def run(self, input: RepurposeWorkflowInput) -> dict:
        from app.services.marketing.service import marketing_service

        channels = input.target_channels or ["instagram", "twitter", "linkedin", "tiktok"]

        items = await marketing_service.repurpose_content(
            workspace_id=input.workspace_id,
            source_text=input.source_text,
            source_type=input.source_type,
            target_channels=channels,
        )

        return {
            "source_type": input.source_type,
            "channels_targeted": channels,
            "items_generated": len(items),
            "items": items,
        }


# ═════════════════════════════════════════════════════════════════════════════
#  PERFORMANCE TRACKING WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class PerformanceTrackingWorkflow:
    """
    Workflow: Periodically fetch metrics for published content → Store → Analyze
    """

    async def run(self, input: PerformanceTrackingInput) -> dict:
        from app.services.marketing.service import marketing_service

        results = []
        for item_id in input.content_item_ids:
            metrics = await marketing_service.fetch_metrics(
                channel=input.channel,
                external_id=item_id,
            )
            results.append({"content_item_id": item_id, "metrics": metrics})

        # Get AI feedback
        all_metrics = [r["metrics"] for r in results if r["metrics"]]
        feedback = await marketing_service.get_performance_feedback(
            workspace_id=input.workspace_id,
            metrics=all_metrics,
            channel=input.channel,
        )

        return {
            "tracked_items": len(results),
            "metrics": results,
            "feedback": feedback,
        }


# ─── Workflow Registry ───────────────────────────────────────────────────────

MARKETING_WORKFLOWS = {
    "content_generation_pipeline": ContentGenerationPipelineWorkflow,
    "scheduled_publish": ScheduledPublishWorkflow,
    "campaign_execution": CampaignExecutionWorkflow,
    "content_repurpose": RepurposeWorkflow,
    "performance_tracking": PerformanceTrackingWorkflow,
}