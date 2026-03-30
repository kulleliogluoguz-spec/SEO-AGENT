"""
AI Observability Layer — Tracing, metrics, and cost tracking.

Provides:
- Model call tracing with full request/response capture
- Routing decision logging
- Prompt version tracking
- Tool execution tracing
- Latency metrics per model/provider/engine
- Cost estimation and tracking
- Structured output validation failure tracking
- Evaluation score history
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AITrace:
    """A single AI operation trace."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    # Request info
    engine: str = ""
    role: str = ""
    prompt_id: str = ""
    prompt_version: str = ""

    # Routing
    routing_reason: str = ""
    model_requested: str = ""
    model_used: str = ""
    provider: str = ""
    was_fallback: bool = False

    # Input/Output
    input_preview: str = ""       # First 200 chars of input
    output_preview: str = ""      # First 200 chars of output
    input_tokens: int = 0
    output_tokens: int = 0

    # Performance
    latency_ms: float = 0.0
    routing_latency_ms: float = 0.0

    # Cost
    cost_usd: float = 0.0

    # Quality
    output_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    guardrail_issues: list[dict] = field(default_factory=list)

    # Tool calls
    tool_calls: list[dict] = field(default_factory=list)

    # Status
    success: bool = True
    error: Optional[str] = None

    # Context
    workspace_id: str = ""
    site_id: str = ""
    agent_id: str = ""


@dataclass
class MetricBucket:
    """Aggregated metrics for a time window."""
    count: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    fallback_count: int = 0
    validation_failures: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.count, 1)

    @property
    def error_rate(self) -> float:
        return self.errors / max(self.count, 1)


class AITracer:
    """
    Central tracing and metrics system for the AI layer.

    In production, traces would be exported to an observability backend
    (e.g., Jaeger, Datadog, or a custom trace store).
    Currently stores in-memory with configurable retention.
    """

    def __init__(self, max_traces: int = 10000) -> None:
        self._traces: list[AITrace] = []
        self._max_traces = max_traces

        # Aggregated metrics per model
        self._model_metrics: dict[str, MetricBucket] = defaultdict(MetricBucket)
        # Per provider
        self._provider_metrics: dict[str, MetricBucket] = defaultdict(MetricBucket)
        # Per engine
        self._engine_metrics: dict[str, MetricBucket] = defaultdict(MetricBucket)

    def record(self, trace: AITrace) -> None:
        """Record a trace and update metrics."""
        self._traces.append(trace)

        # Trim old traces
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-self._max_traces:]

        # Update model metrics
        m = self._model_metrics[trace.model_used]
        m.count += 1
        m.total_latency_ms += trace.latency_ms
        m.total_input_tokens += trace.input_tokens
        m.total_output_tokens += trace.output_tokens
        m.total_cost_usd += trace.cost_usd
        if not trace.success:
            m.errors += 1
        if trace.was_fallback:
            m.fallback_count += 1
        if not trace.output_valid:
            m.validation_failures += 1

        # Update provider metrics
        p = self._provider_metrics[trace.provider]
        p.count += 1
        p.total_latency_ms += trace.latency_ms
        p.total_cost_usd += trace.cost_usd
        if not trace.success:
            p.errors += 1

        # Update engine metrics
        if trace.engine:
            e = self._engine_metrics[trace.engine]
            e.count += 1
            e.total_latency_ms += trace.latency_ms
            e.total_cost_usd += trace.cost_usd
            if not trace.success:
                e.errors += 1

        logger.debug(
            f"Trace: {trace.engine}/{trace.model_used} "
            f"latency={trace.latency_ms:.0f}ms tokens={trace.input_tokens}+{trace.output_tokens} "
            f"cost=${trace.cost_usd:.4f}"
        )

    def get_recent_traces(self, limit: int = 50, engine: str = "", model: str = "") -> list[dict]:
        """Get recent traces with optional filtering."""
        traces = self._traces
        if engine:
            traces = [t for t in traces if t.engine == engine]
        if model:
            traces = [t for t in traces if t.model_used == model]
        return [self._trace_to_dict(t) for t in traces[-limit:]]

    def get_model_metrics(self) -> dict[str, dict]:
        return {
            model: {
                "count": m.count,
                "errors": m.errors,
                "error_rate": round(m.error_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "total_input_tokens": m.total_input_tokens,
                "total_output_tokens": m.total_output_tokens,
                "total_cost_usd": round(m.total_cost_usd, 4),
                "fallback_count": m.fallback_count,
                "validation_failures": m.validation_failures,
            }
            for model, m in self._model_metrics.items()
        }

    def get_provider_metrics(self) -> dict[str, dict]:
        return {
            provider: {
                "count": m.count,
                "errors": m.errors,
                "error_rate": round(m.error_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "total_cost_usd": round(m.total_cost_usd, 4),
            }
            for provider, m in self._provider_metrics.items()
        }

    def get_engine_metrics(self) -> dict[str, dict]:
        return {
            engine: {
                "count": m.count,
                "errors": m.errors,
                "error_rate": round(m.error_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "total_cost_usd": round(m.total_cost_usd, 4),
            }
            for engine, m in self._engine_metrics.items()
        }

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get a summary for the admin dashboard."""
        total_calls = sum(m.count for m in self._model_metrics.values())
        total_errors = sum(m.errors for m in self._model_metrics.values())
        total_cost = sum(m.total_cost_usd for m in self._model_metrics.values())
        total_tokens = sum(
            m.total_input_tokens + m.total_output_tokens
            for m in self._model_metrics.values()
        )

        return {
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": round(total_errors / max(total_calls, 1), 4),
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "active_models": len(self._model_metrics),
            "active_providers": len(self._provider_metrics),
            "active_engines": len(self._engine_metrics),
            "model_breakdown": self.get_model_metrics(),
            "provider_breakdown": self.get_provider_metrics(),
            "engine_breakdown": self.get_engine_metrics(),
            "recent_errors": [
                self._trace_to_dict(t)
                for t in self._traces[-100:]
                if not t.success
            ][-10:],
        }

    def get_cost_report(self) -> dict[str, Any]:
        """Cost breakdown by model and provider."""
        return {
            "total_cost_usd": round(sum(m.total_cost_usd for m in self._model_metrics.values()), 4),
            "by_model": {
                model: round(m.total_cost_usd, 4)
                for model, m in self._model_metrics.items()
            },
            "by_provider": {
                provider: round(m.total_cost_usd, 4)
                for provider, m in self._provider_metrics.items()
            },
            "self_hosted_calls": sum(
                m.count for model, m in self._model_metrics.items()
                if m.total_cost_usd == 0
            ),
            "api_calls": sum(
                m.count for model, m in self._model_metrics.items()
                if m.total_cost_usd > 0
            ),
        }

    def _trace_to_dict(self, trace: AITrace) -> dict:
        return {
            "trace_id": trace.trace_id,
            "timestamp": trace.timestamp,
            "engine": trace.engine,
            "role": trace.role,
            "model_used": trace.model_used,
            "provider": trace.provider,
            "routing_reason": trace.routing_reason,
            "was_fallback": trace.was_fallback,
            "input_tokens": trace.input_tokens,
            "output_tokens": trace.output_tokens,
            "latency_ms": round(trace.latency_ms, 1),
            "cost_usd": round(trace.cost_usd, 4),
            "success": trace.success,
            "error": trace.error,
            "output_valid": trace.output_valid,
            "input_preview": trace.input_preview[:200],
            "output_preview": trace.output_preview[:200],
        }


# Singleton
_tracer: Optional[AITracer] = None


def get_ai_tracer() -> AITracer:
    global _tracer
    if _tracer is None:
        _tracer = AITracer()
    return _tracer
