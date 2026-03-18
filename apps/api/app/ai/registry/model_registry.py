"""
Model Registry — Central catalog of all available models.

Each model is described by a ModelCard with:
- identity (id, family, provider)
- capabilities (reasoning, tool_use, structured_output, coding, multimodal)
- constraints (context_length, max_output, cost_per_1k_input/output)
- deployment profiles (local, production)
- role assignments (which logical AI roles this model can serve)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class ModelCapability(str, enum.Enum):
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    STRUCTURED_OUTPUT = "structured_output"
    CODING = "coding"
    MULTIMODAL_VISION = "multimodal_vision"
    MULTIMODAL_AUDIO = "multimodal_audio"
    LONG_CONTEXT = "long_context"
    FAST_INFERENCE = "fast_inference"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    EMBEDDING = "embedding"


class ModelProvider(str, enum.Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    LITELLM = "litellm"
    OPENAI_COMPAT = "openai_compat"
    ANTHROPIC = "anthropic"  # fallback/comparison
    LLAMACPP = "llamacpp"


class AIRole(str, enum.Enum):
    """Logical AI roles that map to physical models."""
    CORE_REASONING = "core_reasoning"
    TOOL_EXECUTION = "tool_execution"
    CODING_SYSTEMS = "coding_systems"
    CONTENT_STRATEGY = "content_strategy"
    RECOMMENDATION = "recommendation"
    EVIDENCE_SYNTHESIS = "evidence_synthesis"
    COMPETITOR_REASONING = "competitor_reasoning"
    VISIBILITY_REASONING = "visibility_reasoning"
    MARKETING_PLANNING = "marketing_planning"
    SOCIAL_ADAPTATION = "social_adaptation"
    AD_COPY = "ad_copy"
    REPORT_SYNTHESIS = "report_synthesis"
    GUARDRAIL = "guardrail"
    ROUTING = "routing"
    EVAL = "eval"
    STRUCTURED_OUTPUT = "structured_output"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"


class DeploymentProfile(str, enum.Enum):
    LOCAL = "local"          # Ollama / llama.cpp — dev machine
    PRODUCTION = "production"  # vLLM / cloud GPU
    HYBRID = "hybrid"        # LiteLLM routing between local + prod


@dataclass
class ModelCard:
    """Complete description of a model available in the system."""

    # Identity
    id: str                              # e.g. "qwen3-235b-a22b"
    name: str                            # Human-readable
    family: str                          # e.g. "qwen3", "llama4", "deepseek-r1"
    version: str = "latest"

    # Provider & serving
    provider: ModelProvider = ModelProvider.OLLAMA
    serving_model_id: str = ""           # Model string for the provider API
    base_url: str = ""                   # Provider endpoint

    # Capabilities
    capabilities: list[ModelCapability] = field(default_factory=list)
    roles: list[AIRole] = field(default_factory=list)

    # Constraints
    context_length: int = 32768
    max_output_tokens: int = 8192
    supports_streaming: bool = True

    # Cost (USD per 1K tokens, 0 for self-hosted)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    # Performance estimates
    avg_latency_ms: int = 2000           # Typical first-token latency
    tokens_per_second: int = 40          # Estimated generation speed

    # Deployment
    profiles: list[DeploymentProfile] = field(default_factory=lambda: [DeploymentProfile.LOCAL])
    gpu_memory_gb: float = 0.0           # VRAM needed for self-hosted
    quantization: Optional[str] = None   # e.g. "Q4_K_M", "AWQ", "GPTQ"

    # Adapter support
    supports_lora: bool = False
    active_adapters: list[str] = field(default_factory=list)

    # Status
    enabled: bool = True
    is_fallback: bool = False
    shadow_mode: bool = False            # Run in shadow for eval, don't serve

    def has_capability(self, cap: ModelCapability) -> bool:
        return cap in self.capabilities

    def can_serve_role(self, role: AIRole) -> bool:
        return role in self.roles

    def is_available_for(self, profile: DeploymentProfile) -> bool:
        return profile in self.profiles


class ModelRegistry:
    """
    Central registry of all models available to the AI subsystem.

    In production, this could be backed by a database.
    For now, it's code-defined with sensible defaults for the
    recommended open-source stack.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelCard] = {}
        self._role_assignments: dict[AIRole, list[str]] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load the recommended default model lineup."""

        # ── CORE REASONING MODEL ─────────────────────────────────────
        # Qwen3-235B-A22B (MoE): Best open reasoning model as of mid-2025.
        # 22B active params from 235B total — excellent quality/cost ratio.
        self.register(ModelCard(
            id="qwen3-235b-a22b",
            name="Qwen3 235B-A22B (MoE)",
            family="qwen3",
            serving_model_id="qwen3:235b-a22b",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.REASONING,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODING,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.JSON_MODE,
            ],
            roles=[
                AIRole.CORE_REASONING,
                AIRole.RECOMMENDATION,
                AIRole.EVIDENCE_SYNTHESIS,
                AIRole.COMPETITOR_REASONING,
                AIRole.VISIBILITY_REASONING,
                AIRole.CONTENT_STRATEGY,
                AIRole.MARKETING_PLANNING,
                AIRole.REPORT_SYNTHESIS,
            ],
            context_length=131072,
            max_output_tokens=16384,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency_ms=3000,
            tokens_per_second=35,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=48.0,
            quantization="AWQ",
            supports_lora=True,
        ))

        # ── TOOL / STRUCTURED OUTPUT MODEL ───────────────────────────
        # Qwen3-30B-A3B: Smaller MoE, extremely fast for tool use.
        self.register(ModelCard(
            id="qwen3-30b-a3b",
            name="Qwen3 30B-A3B (MoE)",
            family="qwen3",
            serving_model_id="qwen3:30b-a3b",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.REASONING,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.JSON_MODE,
                ModelCapability.FAST_INFERENCE,
            ],
            roles=[
                AIRole.TOOL_EXECUTION,
                AIRole.STRUCTURED_OUTPUT,
                AIRole.SOCIAL_ADAPTATION,
                AIRole.AD_COPY,
            ],
            context_length=131072,
            max_output_tokens=8192,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency_ms=800,
            tokens_per_second=80,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=8.0,
            quantization="Q4_K_M",
            supports_lora=True,
        ))

        # ── CODING / SYSTEMS MODEL ──────────────────────────────────
        # DeepSeek-R1 distill or Qwen2.5-Coder for code-heavy tasks.
        self.register(ModelCard(
            id="qwen2.5-coder-32b",
            name="Qwen2.5 Coder 32B",
            family="qwen2.5-coder",
            serving_model_id="qwen2.5-coder:32b",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.CODING,
                ModelCapability.REASONING,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
            ],
            roles=[
                AIRole.CODING_SYSTEMS,
            ],
            context_length=131072,
            max_output_tokens=8192,
            avg_latency_ms=1500,
            tokens_per_second=45,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=20.0,
            quantization="Q4_K_M",
            supports_lora=True,
        ))

        # ── SMALL FAST MODEL (Router / Classifier / Guardrails) ─────
        # Qwen3-8B: Great for routing, classification, guardrails.
        self.register(ModelCard(
            id="qwen3-8b",
            name="Qwen3 8B",
            family="qwen3",
            serving_model_id="qwen3:8b",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.REASONING,
                ModelCapability.FAST_INFERENCE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.FUNCTION_CALLING,
            ],
            roles=list(AIRole),  # Local dev: serve all roles
            context_length=131072,
            max_output_tokens=4096,
            avg_latency_ms=300,
            tokens_per_second=120,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=5.0,
            quantization="Q4_K_M",
        ))

        # ── TINY MODEL (Quick classification / triage) ──────────────
        self.register(ModelCard(
            id="qwen3-1.7b",
            name="Qwen3 1.7B",
            family="qwen3",
            serving_model_id="qwen3:1.7b",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.FAST_INFERENCE,
                ModelCapability.STRUCTURED_OUTPUT,
            ],
            roles=[
                AIRole.CLASSIFICATION,
                AIRole.ROUTING,
            ],
            context_length=32768,
            max_output_tokens=2048,
            avg_latency_ms=100,
            tokens_per_second=200,
            profiles=[DeploymentProfile.LOCAL],
            gpu_memory_gb=1.5,
            quantization="Q4_K_M",
        ))

        # ── MULTIMODAL / VISION MODEL (Future) ──────────────────────
        self.register(ModelCard(
            id="llama4-scout-17b",
            name="Llama 4 Scout 17B-16E",
            family="llama4",
            serving_model_id="llama4:scout",
            provider=ModelProvider.OLLAMA,
            capabilities=[
                ModelCapability.REASONING,
                ModelCapability.MULTIMODAL_VISION,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
            ],
            roles=[
                AIRole.CORE_REASONING,
                AIRole.EVIDENCE_SYNTHESIS,
            ],
            context_length=131072,
            max_output_tokens=8192,
            avg_latency_ms=2000,
            tokens_per_second=30,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=24.0,
            enabled=True,
        ))

        # ── EMBEDDING MODEL ─────────────────────────────────────────
        self.register(ModelCard(
            id="nomic-embed-text",
            name="Nomic Embed Text v1.5",
            family="nomic",
            serving_model_id="nomic-embed-text:latest",
            provider=ModelProvider.OLLAMA,
            capabilities=[ModelCapability.EMBEDDING],
            roles=[],
            context_length=8192,
            max_output_tokens=0,
            avg_latency_ms=50,
            tokens_per_second=0,
            profiles=[DeploymentProfile.LOCAL, DeploymentProfile.PRODUCTION],
            gpu_memory_gb=0.5,
        ))

        # ── ANTHROPIC FALLBACK (API) ────────────────────────────────
        self.register(ModelCard(
            id="claude-sonnet-4",
            name="Claude Sonnet 4 (API Fallback)",
            family="claude",
            serving_model_id="claude-sonnet-4-20250514",
            provider=ModelProvider.ANTHROPIC,
            capabilities=[
                ModelCapability.REASONING,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODING,
                ModelCapability.MULTIMODAL_VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.JSON_MODE,
            ],
            roles=list(AIRole),  # Can serve all roles as fallback
            context_length=200000,
            max_output_tokens=16384,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            avg_latency_ms=1500,
            tokens_per_second=80,
            profiles=[DeploymentProfile.PRODUCTION, DeploymentProfile.HYBRID],
            is_fallback=True,
            enabled=False,
        ))

        self._rebuild_role_index()

    def register(self, card: ModelCard) -> None:
        self._models[card.id] = card

    def get(self, model_id: str) -> Optional[ModelCard]:
        return self._models.get(model_id)

    def list_all(self) -> list[ModelCard]:
        return list(self._models.values())

    def list_enabled(self) -> list[ModelCard]:
        return [m for m in self._models.values() if m.enabled]

    def list_for_role(self, role: AIRole) -> list[ModelCard]:
        return [
            self._models[mid]
            for mid in self._role_assignments.get(role, [])
            if self._models[mid].enabled
        ]

    def list_for_profile(self, profile: DeploymentProfile) -> list[ModelCard]:
        return [m for m in self._models.values() if m.enabled and m.is_available_for(profile)]

    def get_primary_for_role(self, role: AIRole) -> Optional[ModelCard]:
        """Get the best (first non-fallback) model for a role."""
        candidates = self.list_for_role(role)
        primary = [m for m in candidates if not m.is_fallback]
        return primary[0] if primary else (candidates[0] if candidates else None)

    def get_fallback_for_role(self, role: AIRole) -> Optional[ModelCard]:
        candidates = self.list_for_role(role)
        fallbacks = [m for m in candidates if m.is_fallback]
        return fallbacks[0] if fallbacks else None

    def enable_model(self, model_id: str) -> bool:
        if model_id in self._models:
            self._models[model_id].enabled = True
            self._rebuild_role_index()
            return True
        return False

    def disable_model(self, model_id: str) -> bool:
        if model_id in self._models:
            self._models[model_id].enabled = False
            self._rebuild_role_index()
            return True
        return False

    def set_shadow_mode(self, model_id: str, shadow: bool) -> bool:
        if model_id in self._models:
            self._models[model_id].shadow_mode = shadow
            return True
        return False

    def _rebuild_role_index(self) -> None:
        self._role_assignments = {}
        for model in self._models.values():
            for role in model.roles:
                if role not in self._role_assignments:
                    self._role_assignments[role] = []
                self._role_assignments[role].append(model.id)

    def to_dict(self) -> list[dict]:
        """Serialize for API/admin responses."""
        results = []
        for m in self._models.values():
            results.append({
                "id": m.id,
                "name": m.name,
                "family": m.family,
                "provider": m.provider.value,
                "capabilities": [c.value for c in m.capabilities],
                "roles": [r.value for r in m.roles],
                "context_length": m.context_length,
                "max_output_tokens": m.max_output_tokens,
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
                "avg_latency_ms": m.avg_latency_ms,
                "profiles": [p.value for p in m.profiles],
                "gpu_memory_gb": m.gpu_memory_gb,
                "quantization": m.quantization,
                "supports_lora": m.supports_lora,
                "enabled": m.enabled,
                "is_fallback": m.is_fallback,
                "shadow_mode": m.shadow_mode,
            })
        return results


# Singleton instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
