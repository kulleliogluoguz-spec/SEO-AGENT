"""
AI Admin API Endpoints
======================
REST endpoints for managing the custom AI subsystem.

Provides admin/control surfaces for:
- Model registry management
- Provider health monitoring
- Routing policy configuration
- Prompt version management
- Evaluation runs
- AI traces and metrics
- Training data stats
- Adapter management
- Guardrail settings
- Cost tracking
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# ─── Import all AI subsystem components ───────────────────────────
from app.ai.registry.model_registry import get_model_registry, AIRole, DeploymentProfile
from app.ai.providers.provider_manager import get_provider_manager
from app.ai.router.ai_router import get_ai_router, RoutingPolicy
from app.ai.prompts.prompt_registry import get_prompt_registry, PromptCategory
from app.ai.engines.engine_manager import get_engine_manager
from app.ai.tools.tool_registry import get_tool_registry
from app.ai.memory.context_manager import get_context_manager
from app.ai.guardrails.guardrail_manager import get_guardrail_manager
from app.ai.observability.tracer import get_ai_tracer
from app.ai.evaluation.eval_harness import get_eval_harness
from app.ai.training.training_manager import get_dataset_manager, get_adapter_manager

router = APIRouter(prefix="/ai", tags=["AI Subsystem"])


# ─── Request/Response Schemas ─────────────────────────────────────

class AICompletionRequest(BaseModel):
    """Request body for AI completion."""
    message: str
    engine: str = "reasoning"
    context: dict[str, Any] = Field(default_factory=dict)
    temperature: float = 0.3
    max_tokens: int = 4096
    response_format: Optional[dict] = None
    workspace_id: str = ""
    site_id: str = ""


class ModelToggleRequest(BaseModel):
    model_id: str
    enabled: bool


class ShadowModeRequest(BaseModel):
    model_id: str
    shadow: bool


class RoutingPolicyUpdate(BaseModel):
    profile: Optional[str] = None
    prefer_free: Optional[bool] = None
    enable_fallback: Optional[bool] = None
    fallback_to_anthropic: Optional[bool] = None
    enable_shadow: Optional[bool] = None
    role_overrides: Optional[dict[str, str]] = None


class PromptVersionRequest(BaseModel):
    prompt_id: str
    version: str


class EvalRunRequest(BaseModel):
    suite_id: str


# ─── AI Completion ────────────────────────────────────────────────

@router.post("/complete")
async def ai_complete(req: AICompletionRequest) -> dict[str, Any]:
    """Execute an AI completion through the engine manager."""
    engine_mgr = get_engine_manager()
    engine = engine_mgr.get_engine(req.engine)
    if not engine:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {req.engine}")

    result = await engine.execute(
        task=req.message,
        context=req.context,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        response_format=req.response_format,
        workspace_id=req.workspace_id,
        site_id=req.site_id,
    )

    return {
        "success": result.success,
        "data": result.data,
        "raw_content": result.raw_content[:2000] if result.raw_content else "",
        "error": result.error,
        "model_used": result.model_used,
        "provider_used": result.provider_used,
        "latency_ms": round(result.latency_ms, 1),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(result.cost_usd, 6),
        "trace_id": result.trace_id,
        "engine": result.engine_name,
    }


# ─── Model Registry ──────────────────────────────────────────────

@router.get("/models")
async def list_models() -> dict[str, Any]:
    """List all registered models."""
    registry = get_model_registry()
    return {"models": registry.to_dict()}


@router.get("/models/{model_id}")
async def get_model(model_id: str) -> dict[str, Any]:
    """Get details of a specific model."""
    registry = get_model_registry()
    card = registry.get(model_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    models = registry.to_dict()
    return next(m for m in models if m["id"] == model_id)


@router.post("/models/toggle")
async def toggle_model(req: ModelToggleRequest) -> dict[str, Any]:
    """Enable or disable a model."""
    registry = get_model_registry()
    if req.enabled:
        success = registry.enable_model(req.model_id)
    else:
        success = registry.disable_model(req.model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model not found: {req.model_id}")
    return {"model_id": req.model_id, "enabled": req.enabled}


@router.post("/models/shadow")
async def set_shadow_mode(req: ShadowModeRequest) -> dict[str, Any]:
    """Set shadow mode for A/B evaluation."""
    registry = get_model_registry()
    success = registry.set_shadow_mode(req.model_id, req.shadow)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model not found: {req.model_id}")
    return {"model_id": req.model_id, "shadow_mode": req.shadow}


@router.get("/models/roles")
async def list_role_assignments() -> dict[str, Any]:
    """Show which models serve which AI roles."""
    registry = get_model_registry()
    result = {}
    for role in AIRole:
        models = registry.list_for_role(role)
        primary = registry.get_primary_for_role(role)
        fallback = registry.get_fallback_for_role(role)
        result[role.value] = {
            "primary": primary.id if primary else None,
            "fallback": fallback.id if fallback else None,
            "all_candidates": [m.id for m in models],
        }
    return {"role_assignments": result}


# ─── Providers ────────────────────────────────────────────────────

@router.get("/providers/health")
async def provider_health() -> dict[str, Any]:
    """Check health of all AI providers."""
    manager = await get_provider_manager()
    return {"providers": await manager.health_check_all()}


@router.get("/providers/models")
async def provider_models() -> dict[str, Any]:
    """List models available on each provider."""
    manager = await get_provider_manager()
    return {"available_models": await manager.list_available_models()}


# ─── Router ───────────────────────────────────────────────────────

@router.get("/router/policy")
async def get_routing_policy() -> dict[str, Any]:
    """Get current routing policy."""
    ai_router = get_ai_router()
    return {
        "policy": {
            "profile": ai_router.policy.profile.value,
            "prefer_free": ai_router.policy.prefer_free,
            "max_cost_per_request": ai_router.policy.max_cost_per_request,
            "max_latency_ms": ai_router.policy.max_latency_ms,
            "enable_fallback": ai_router.policy.enable_fallback,
            "fallback_to_anthropic": ai_router.policy.fallback_to_anthropic,
            "enable_shadow": ai_router.policy.enable_shadow,
            "role_overrides": ai_router.policy.role_overrides,
        },
        "stats": ai_router.get_stats(),
    }


@router.put("/router/policy")
async def update_routing_policy(req: RoutingPolicyUpdate) -> dict[str, Any]:
    """Update routing policy."""
    ai_router = get_ai_router()
    if req.profile:
        try:
            ai_router.policy.profile = DeploymentProfile(req.profile)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid profile: {req.profile}")
    if req.prefer_free is not None:
        ai_router.policy.prefer_free = req.prefer_free
    if req.enable_fallback is not None:
        ai_router.policy.enable_fallback = req.enable_fallback
    if req.fallback_to_anthropic is not None:
        ai_router.policy.fallback_to_anthropic = req.fallback_to_anthropic
    if req.enable_shadow is not None:
        ai_router.policy.enable_shadow = req.enable_shadow
    if req.role_overrides is not None:
        ai_router.policy.role_overrides = req.role_overrides
    return {"status": "updated", "policy": req.model_dump(exclude_none=True)}


# ─── Engines ──────────────────────────────────────────────────────

@router.get("/engines")
async def list_engines() -> dict[str, Any]:
    """List all AI engines and their stats."""
    engine_mgr = get_engine_manager()
    return engine_mgr.get_all_stats()


# ─── Prompts ──────────────────────────────────────────────────────

@router.get("/prompts")
async def list_prompts(
    category: Optional[str] = Query(None),
) -> dict[str, Any]:
    """List all prompt templates."""
    registry = get_prompt_registry()
    if category:
        try:
            cat = PromptCategory(category)
            prompts = registry.list_by_category(cat)
            return {"prompts": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category.value,
                    "version": p.version,
                    "fingerprint": p.fingerprint,
                    "variables": p.variables,
                    "output_format": p.output_format,
                    "example_count": len(p.examples),
                }
                for p in prompts
            ]}
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    return {"prompts": registry.list_all()}


@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str, version: Optional[str] = None) -> dict[str, Any]:
    """Get a specific prompt template."""
    registry = get_prompt_registry()
    prompt = registry.get(prompt_id, version=version)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")
    return {
        "id": prompt.id,
        "name": prompt.name,
        "category": prompt.category.value,
        "version": prompt.version,
        "system_template": prompt.system_template,
        "user_template": prompt.user_template,
        "variables": prompt.variables,
        "output_format": prompt.output_format,
        "output_schema": prompt.output_schema,
        "examples": [{"input": e.input, "output": e.output, "label": e.label} for e in prompt.examples],
        "fingerprint": prompt.fingerprint,
    }


@router.post("/prompts/activate")
async def activate_prompt_version(req: PromptVersionRequest) -> dict[str, Any]:
    """Set the active version for a prompt."""
    registry = get_prompt_registry()
    success = registry.set_active_version(req.prompt_id, req.version)
    if not success:
        raise HTTPException(status_code=404, detail=f"Prompt/version not found")
    return {"status": "activated", "prompt_id": req.prompt_id, "version": req.version}


# ─── Tools ────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    """List all registered tools."""
    registry = get_tool_registry()
    return {"tools": registry.list_all()}


@router.get("/tools/executions")
async def get_tool_executions(limit: int = 50) -> dict[str, Any]:
    """Get recent tool execution log."""
    registry = get_tool_registry()
    return {"executions": registry.get_execution_log(limit=limit)}


# ─── Traces / Observability ──────────────────────────────────────

@router.get("/traces")
async def get_traces(
    limit: int = Query(50, le=200),
    engine: str = Query(""),
    model: str = Query(""),
) -> dict[str, Any]:
    """Get recent AI traces."""
    tracer = get_ai_tracer()
    return {"traces": tracer.get_recent_traces(limit=limit, engine=engine, model=model)}


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get AI metrics dashboard."""
    tracer = get_ai_tracer()
    return tracer.get_dashboard_summary()


@router.get("/metrics/cost")
async def get_cost_report() -> dict[str, Any]:
    """Get cost breakdown."""
    tracer = get_ai_tracer()
    return tracer.get_cost_report()


# ─── Evaluation ───────────────────────────────────────────────────

@router.get("/evals/suites")
async def list_eval_suites() -> dict[str, Any]:
    """List all evaluation suites."""
    harness = get_eval_harness()
    return {"suites": harness.list_suites()}


@router.get("/evals/runs")
async def get_eval_runs(
    suite_id: str = Query(""),
    limit: int = Query(20),
) -> dict[str, Any]:
    """Get evaluation run history."""
    harness = get_eval_harness()
    return {"runs": harness.get_run_history(suite_id=suite_id, limit=limit)}


@router.post("/evals/run")
async def run_eval_suite(req: EvalRunRequest) -> dict[str, Any]:
    """Run an evaluation suite."""
    harness = get_eval_harness()
    engine_mgr = get_engine_manager()

    suite = harness.get_suite(req.suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite not found: {req.suite_id}")

    # Get the engine for this suite
    engine = engine_mgr.get_engine(suite.engine or "reasoning")
    if not engine:
        raise HTTPException(status_code=400, detail=f"Engine not found: {suite.engine}")

    run = await harness.run_suite(req.suite_id, engine.execute)
    return {"run": run.summary()}


# ─── Training / Datasets ─────────────────────────────────────────

@router.get("/training/stats")
async def get_training_stats() -> dict[str, Any]:
    """Get training dataset statistics."""
    dm = get_dataset_manager()
    return dm.get_stats()


@router.get("/training/adapters")
async def list_adapters() -> dict[str, Any]:
    """List LoRA adapters."""
    am = get_adapter_manager()
    return {"adapters": am.list_adapters()}


# ─── Guardrails ──────────────────────────────────────────────────

@router.get("/guardrails/stats")
async def get_guardrail_stats() -> dict[str, Any]:
    """Get guardrail check statistics."""
    gm = get_guardrail_manager()
    return gm.get_stats()


@router.post("/guardrails/check-input")
async def check_input(text: str = "") -> dict[str, Any]:
    """Test input guardrail."""
    gm = get_guardrail_manager()
    result = gm.check_input(text)
    return {
        "passed": result.passed,
        "blocked": result.blocked,
        "issues": result.issues,
    }


@router.post("/guardrails/check-output")
async def check_output(content: str = "", content_type: str = "general") -> dict[str, Any]:
    """Test output guardrail."""
    gm = get_guardrail_manager()
    result = gm.check_output(content, content_type)
    return {
        "passed": result.passed,
        "blocked": result.blocked,
        "issues": result.issues,
    }


# ─── System Overview ─────────────────────────────────────────────

@router.get("/status")
async def ai_system_status() -> dict[str, Any]:
    """Get comprehensive AI system status."""
    registry = get_model_registry()
    manager = await get_provider_manager()
    ai_router = get_ai_router()
    tracer = get_ai_tracer()
    engine_mgr = get_engine_manager()

    provider_health = await manager.health_check_all()

    return {
        "status": "operational",
        "models": {
            "total": len(registry.list_all()),
            "enabled": len(registry.list_enabled()),
        },
        "providers": provider_health,
        "router": ai_router.get_stats(),
        "engines": engine_mgr.get_all_stats(),
        "metrics_summary": {
            "total_calls": tracer.get_dashboard_summary().get("total_calls", 0),
            "total_cost_usd": tracer.get_cost_report().get("total_cost_usd", 0),
        },
    }
