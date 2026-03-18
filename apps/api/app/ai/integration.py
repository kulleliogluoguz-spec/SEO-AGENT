"""
AI Integration Bridge
=====================
Connects the custom AI subsystem to the existing platform.

This module:
1. Replaces direct Anthropic API calls with the AIRouter
2. Provides a drop-in LangGraph-compatible LLM wrapper
3. Injects domain context into AI calls
4. Records traces and training data from agent operations
5. Integrates guardrails into the agent pipeline

Usage in existing agents:
    # Before (direct Anthropic):
    response = await anthropic_client.messages.create(...)

    # After (via AI subsystem):
    from app.ai.integration import get_ai_client
    ai = get_ai_client()
    result = await ai.complete(
        message="Analyze this site's SEO",
        engine="reasoning",
        workspace_id=workspace_id,
        site_id=site_id,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.ai.engines.engine_manager import EngineResult, get_engine_manager
from app.ai.guardrails.guardrail_manager import get_guardrail_manager
from app.ai.memory.context_manager import get_context_manager
from app.ai.observability.tracer import AITrace, get_ai_tracer
from app.ai.providers.base import AIMessage, AIRequest
from app.ai.router.ai_router import get_ai_router
from app.ai.training.training_manager import DataQuality, get_dataset_manager

logger = logging.getLogger(__name__)


class AIClient:
    """
    High-level AI client for the platform.

    This is the primary interface that existing agents and services
    should use instead of direct Anthropic API calls.
    """

    async def complete(
        self,
        message: str,
        engine: str = "reasoning",
        context: dict[str, Any] | None = None,
        workspace_id: str = "",
        site_id: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
        check_guardrails: bool = True,
    ) -> EngineResult:
        """
        Execute an AI completion through the subsystem.

        This replaces direct Anthropic API calls with:
        1. Input guardrail check
        2. Context injection
        3. Model routing
        4. Provider execution
        5. Output guardrail check
        6. Trace recording
        7. Training data collection
        """

        # 1. Input guardrails
        if check_guardrails:
            gm = get_guardrail_manager()
            input_check = gm.check_input(message)
            if input_check.blocked:
                return EngineResult(
                    success=False,
                    error=f"Input blocked by guardrails: {input_check.issues}",
                    engine_name=engine,
                )
            if input_check.sanitized_input:
                message = input_check.sanitized_input

        # 2. Load context
        ctx_manager = get_context_manager()
        ai_context = await ctx_manager.get_context(workspace_id, site_id)
        merged_context = {**ai_context.to_dict(), **(context or {})}

        # 3. Execute through engine
        engine_mgr = get_engine_manager()
        engine_instance = engine_mgr.get_engine(engine)
        if not engine_instance:
            return EngineResult(
                success=False,
                error=f"Unknown engine: {engine}",
                engine_name=engine,
            )

        result = await engine_instance.execute(
            task=message,
            context=merged_context,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            tools=tools,
            workspace_id=workspace_id,
            site_id=site_id,
        )

        # 4. Output guardrails
        if check_guardrails and result.success and result.raw_content:
            output_check = gm.check_output(result.raw_content)
            if output_check.blocked:
                logger.warning(f"Output blocked by guardrails: {output_check.issues}")
                result.success = False
                result.error = f"Output blocked: {output_check.issues}"

        # 5. Record trace
        tracer = get_ai_tracer()
        tracer.record(AITrace(
            trace_id=result.trace_id,
            engine=engine,
            role=engine_instance.ai_role.value,
            model_used=result.model_used,
            provider=result.provider_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            cost_usd=result.cost_usd,
            success=result.success,
            error=result.error,
            input_preview=message[:200],
            output_preview=(result.raw_content or "")[:200],
            workspace_id=workspace_id,
            site_id=site_id,
        ))

        return result

    async def complete_raw(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        model_id: str = "",
        role: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> AIMessage:
        """
        Low-level completion through the router (bypasses engines).
        Use this when you need direct control over messages.
        """
        ai_router = get_ai_router()
        request = AIRequest(
            messages=messages,
            model_id=model_id,
            system=system,
            role=role,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools or [],
            response_format=response_format,
        )
        return await ai_router.execute(request)

    async def classify(self, text: str) -> dict[str, Any]:
        """Quick task classification using the routing engine."""
        engine_mgr = get_engine_manager()
        result = await engine_mgr.routing.classify_task(text)
        return result.data if result.success else {"category": "general", "confidence": 0.0}

    async def check_content(self, content: str, content_type: str = "general") -> dict[str, Any]:
        """Run content through guardrail + AI safety check."""
        engine_mgr = get_engine_manager()
        result = await engine_mgr.guardrail.check_content(content, content_type)
        return result.data if result.success else {"passed": False, "error": result.error}

    def record_feedback(
        self,
        instruction: str,
        accepted_output: str,
        rejected_output: str = "",
        category: str = "",
    ) -> None:
        """Record user feedback for training data collection."""
        dm = get_dataset_manager()
        if rejected_output:
            dm.record_preference(
                instruction=instruction,
                chosen=accepted_output,
                rejected=rejected_output,
                category=category,
            )
        else:
            dm.record_sft_example(
                instruction=instruction,
                output=accepted_output,
                category=category,
                quality=DataQuality.SILVER,
            )


# ─── LangGraph Integration ───────────────────────────────────────

class LangGraphLLMAdapter:
    """
    Adapter that makes the AI subsystem work as a LangGraph-compatible LLM.

    Drop-in replacement for direct ChatAnthropic usage in LangGraph graphs.
    """

    def __init__(self, engine: str = "reasoning", **defaults: Any) -> None:
        self.engine = engine
        self.defaults = defaults
        self._client = AIClient()

    async def ainvoke(self, messages: list[dict], **kwargs: Any) -> dict:
        """LangGraph-compatible async invocation."""
        merged = {**self.defaults, **kwargs}

        # Extract the last user message as the task
        user_messages = [m for m in messages if m.get("role") == "user"]
        task = user_messages[-1]["content"] if user_messages else ""

        system_messages = [m for m in messages if m.get("role") == "system"]
        system = system_messages[0]["content"] if system_messages else ""

        result = await self._client.complete(
            message=task,
            engine=self.engine,
            context={"system_override": system} if system else {},
            **{k: v for k, v in merged.items() if k in ("temperature", "max_tokens", "workspace_id", "site_id")},
        )

        return {
            "content": result.raw_content or result.error or "",
            "data": result.data,
            "model": result.model_used,
            "success": result.success,
        }


# ─── Factory Functions ────────────────────────────────────────────

_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get the singleton AI client."""
    global _client
    if _client is None:
        _client = AIClient()
    return _client


def get_langgraph_llm(engine: str = "reasoning", **kwargs: Any) -> LangGraphLLMAdapter:
    """Get a LangGraph-compatible LLM backed by the AI subsystem."""
    return LangGraphLLMAdapter(engine=engine, **kwargs)
