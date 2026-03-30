"""
Engine Manager — Logical AI Role Architecture
==============================================
Separates logical AI roles (what the system needs to do)
from physical model backends (which model actually does it).

Each engine:
- Has a dedicated AI role
- Uses the router to resolve the actual model
- Loads the correct prompt template
- Validates outputs against contracts
- Tracks performance per-engine
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.ai.providers.base import AIMessage, AIRequest, FinishReason
from app.ai.registry.model_registry import AIRole
from app.ai.router.ai_router import get_ai_router
from app.ai.prompts.prompt_registry import get_prompt_registry

logger = logging.getLogger(__name__)


@dataclass
class EngineResult:
    """Standardized result from any engine."""
    success: bool
    data: Any = None              # Parsed structured output or raw text
    raw_content: str = ""
    error: Optional[str] = None
    model_used: str = ""
    provider_used: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    trace_id: str = ""
    engine_name: str = ""


class BaseEngine:
    """Base class for all logical AI engines."""

    engine_name: str = "base"
    ai_role: AIRole = AIRole.CORE_REASONING
    default_prompt_id: str = "system.base"

    def __init__(self) -> None:
        self._call_count = 0
        self._error_count = 0

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        prompt_overrides: dict[str, str] | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        workspace_id: str | None = None,
        site_id: str | None = None,
    ) -> EngineResult:
        """Execute a task through this engine."""
        self._call_count += 1

        # Load prompt
        prompt_reg = get_prompt_registry()
        prompt = prompt_reg.get(self.default_prompt_id)

        system_msg = ""
        if prompt:
            render_vars = {**(context or {}), **(prompt_overrides or {})}
            system_msg = prompt.render_system(**render_vars)
            if prompt.output_format == "json" and not response_format:
                response_format = {"type": "json_object"}

        # Build request
        messages = [{"role": "user", "content": task}]

        request = AIRequest(
            messages=messages,
            system=system_msg,
            role=self.ai_role.value,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools or [],
            response_format=response_format,
            workspace_id=workspace_id,
            site_id=site_id,
        )

        # Route and execute
        router = get_ai_router()
        response = await router.execute(request)

        if response.finish_reason == FinishReason.ERROR:
            self._error_count += 1
            return EngineResult(
                success=False,
                error=response.content,
                raw_content=response.content,
                model_used=response.model_id,
                provider_used=response.provider,
                latency_ms=response.latency_ms,
                trace_id=response.trace_id,
                engine_name=self.engine_name,
            )

        # Parse structured output if JSON expected
        data = response.content
        if response_format and response_format.get("type") == "json_object":
            try:
                data = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"{self.engine_name}: Failed to parse JSON output")
                    data = {"raw": response.content}

        return EngineResult(
            success=True,
            data=data,
            raw_content=response.content,
            model_used=response.model_id,
            provider_used=response.provider,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            trace_id=response.trace_id,
            engine_name=self.engine_name,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "engine": self.engine_name,
            "role": self.ai_role.value,
            "calls": self._call_count,
            "errors": self._error_count,
        }


# ─── Concrete Engine Implementations ──────────────────────────────


class ReasoningEngine(BaseEngine):
    engine_name = "reasoning"
    ai_role = AIRole.CORE_REASONING
    default_prompt_id = "system.base"


class StructuredOutputEngine(BaseEngine):
    engine_name = "structured_output"
    ai_role = AIRole.STRUCTURED_OUTPUT
    default_prompt_id = "system.base"

    async def execute(self, task: str, **kwargs: Any) -> EngineResult:
        kwargs.setdefault("response_format", {"type": "json_object"})
        return await super().execute(task, **kwargs)


class ToolUseEngine(BaseEngine):
    engine_name = "tool_use"
    ai_role = AIRole.TOOL_EXECUTION
    default_prompt_id = "system.base"


class ContentStrategyEngine(BaseEngine):
    engine_name = "content_strategy"
    ai_role = AIRole.CONTENT_STRATEGY
    default_prompt_id = "content.strategy_brief"


class RecommendationEngine(BaseEngine):
    engine_name = "recommendation"
    ai_role = AIRole.RECOMMENDATION
    default_prompt_id = "recommendation.generate"

    async def generate_recommendations(
        self,
        analysis_data: dict,
        workspace_context: dict | None = None,
        existing_recs: list | None = None,
    ) -> EngineResult:
        context = {
            "analysis_data": json.dumps(analysis_data, indent=2),
            "workspace_context": json.dumps(workspace_context or {}),
            "existing_recommendations": json.dumps(existing_recs or []),
        }
        return await self.execute(
            task="Generate prioritized growth recommendations based on the analysis data.",
            context=context,
            response_format={"type": "json_object"},
        )


class EvidenceSynthesisEngine(BaseEngine):
    engine_name = "evidence_synthesis"
    ai_role = AIRole.EVIDENCE_SYNTHESIS
    default_prompt_id = "system.base"


class CompetitorReasoningEngine(BaseEngine):
    engine_name = "competitor_reasoning"
    ai_role = AIRole.COMPETITOR_REASONING
    default_prompt_id = "competitor.analysis"


class VisibilityReasoningEngine(BaseEngine):
    engine_name = "visibility_reasoning"
    ai_role = AIRole.VISIBILITY_REASONING
    default_prompt_id = "geo.visibility_analysis"


class MarketingPlanningEngine(BaseEngine):
    engine_name = "marketing_planning"
    ai_role = AIRole.MARKETING_PLANNING
    default_prompt_id = "system.base"


class SocialAdaptationEngine(BaseEngine):
    engine_name = "social_adaptation"
    ai_role = AIRole.SOCIAL_ADAPTATION
    default_prompt_id = "social.adapt_content"


class AdCopyEngine(BaseEngine):
    engine_name = "ad_copy"
    ai_role = AIRole.AD_COPY
    default_prompt_id = "ad.copy_generation"


class ReportSynthesisEngine(BaseEngine):
    engine_name = "report_synthesis"
    ai_role = AIRole.REPORT_SYNTHESIS
    default_prompt_id = "reporting.weekly_summary"


class GuardrailEngine(BaseEngine):
    engine_name = "guardrail"
    ai_role = AIRole.GUARDRAIL
    default_prompt_id = "guardrail.content_check"

    async def check_content(self, content: str, content_type: str = "general", platform: str = "web") -> EngineResult:
        context = {
            "content_to_check": content,
            "content_type": content_type,
            "target_platform": platform,
        }
        return await self.execute(
            task="Review this content for safety, compliance, and quality issues.",
            context=context,
            response_format={"type": "json_object"},
            temperature=0.1,
        )


class RoutingEngine(BaseEngine):
    engine_name = "routing_classifier"
    ai_role = AIRole.ROUTING
    default_prompt_id = "routing.classify_task"

    async def classify_task(self, task_description: str) -> EngineResult:
        return await self.execute(
            task=f"Classify this task: {task_description}",
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )


class EvalEngine(BaseEngine):
    engine_name = "eval"
    ai_role = AIRole.EVAL
    default_prompt_id = "evaluation.quality_check"


# ─── Engine Manager ──────────────────────────────────────────────


class EngineManager:
    """
    Central manager for all AI engines.
    Provides typed access to each engine.
    """

    def __init__(self) -> None:
        self.reasoning = ReasoningEngine()
        self.structured_output = StructuredOutputEngine()
        self.tool_use = ToolUseEngine()
        self.content_strategy = ContentStrategyEngine()
        self.recommendation = RecommendationEngine()
        self.evidence_synthesis = EvidenceSynthesisEngine()
        self.competitor_reasoning = CompetitorReasoningEngine()
        self.visibility_reasoning = VisibilityReasoningEngine()
        self.marketing_planning = MarketingPlanningEngine()
        self.social_adaptation = SocialAdaptationEngine()
        self.ad_copy = AdCopyEngine()
        self.report_synthesis = ReportSynthesisEngine()
        self.guardrail = GuardrailEngine()
        self.routing = RoutingEngine()
        self.eval = EvalEngine()

        self._engines = {
            "reasoning": self.reasoning,
            "structured_output": self.structured_output,
            "tool_use": self.tool_use,
            "content_strategy": self.content_strategy,
            "recommendation": self.recommendation,
            "evidence_synthesis": self.evidence_synthesis,
            "competitor_reasoning": self.competitor_reasoning,
            "visibility_reasoning": self.visibility_reasoning,
            "marketing_planning": self.marketing_planning,
            "social_adaptation": self.social_adaptation,
            "ad_copy": self.ad_copy,
            "report_synthesis": self.report_synthesis,
            "guardrail": self.guardrail,
            "routing": self.routing,
            "eval": self.eval,
        }

    def get_engine(self, name: str) -> Optional[BaseEngine]:
        return self._engines.get(name)

    def list_engines(self) -> list[dict[str, Any]]:
        return [engine.get_stats() for engine in self._engines.values()]

    def get_all_stats(self) -> dict[str, Any]:
        return {
            "engines": self.list_engines(),
            "total_calls": sum(e._call_count for e in self._engines.values()),
            "total_errors": sum(e._error_count for e in self._engines.values()),
        }


# Singleton
_manager: Optional[EngineManager] = None


def get_engine_manager() -> EngineManager:
    global _manager
    if _manager is None:
        _manager = EngineManager()
    return _manager
