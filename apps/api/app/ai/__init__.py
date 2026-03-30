"""
AI CMO OS — Custom AI Subsystem
================================
A production-grade, open-source-first, multi-model AI intelligence layer.

Architecture:
    Registry  → Model definitions, capabilities, costs
    Providers → vLLM, Ollama, OpenAI-compat, LiteLLM
    Router    → Task-based, cost-aware, capability-aware routing
    Engines   → Logical AI roles (reasoning, tools, content, etc.)
    Prompts   → Versioned prompt registry with contracts
    Tools     → Structured tool definitions with safety
    Memory    → Context management (workspace, brand, competitor)
    Eval      → Quality harness, regression tests
    Training  → Dataset scaffolding, LoRA/SFT pipeline stubs
    Guardrails→ Input/output validation, safety checks
    Observability → Tracing, metrics, cost tracking
"""

from app.ai.registry.model_registry import ModelRegistry, ModelCard
from app.ai.router.ai_router import AIRouter
from app.ai.providers.provider_manager import ProviderManager
from app.ai.engines.engine_manager import EngineManager
from app.ai.prompts.prompt_registry import PromptRegistry
from app.ai.observability.tracer import AITracer

__all__ = [
    "ModelRegistry",
    "ModelCard",
    "AIRouter",
    "ProviderManager",
    "EngineManager",
    "PromptRegistry",
    "AITracer",
]
