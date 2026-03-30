"""
AI Router / Gateway Layer
=========================
Routes AI requests to the optimal model based on:
- Task type / AI role
- Required capabilities
- Cost constraints
- Latency requirements
- Deployment profile (local vs production)
- Fallback chains
- Shadow mode for A/B evaluation

This is the single entry point for all AI calls in the platform.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.ai.providers.base import AIMessage, AIRequest, FinishReason
from app.ai.providers.provider_manager import get_provider_manager
from app.ai.registry.model_registry import (
    AIRole,
    DeploymentProfile,
    ModelCapability,
    ModelCard,
    get_model_registry,
)

logger = logging.getLogger(__name__)


@dataclass
class RoutingPolicy:
    """Configurable routing policy."""
    # Deployment mode
    profile: DeploymentProfile = DeploymentProfile.LOCAL

    # Cost limits
    max_cost_per_request: float = 0.10  # USD
    prefer_free: bool = True            # Prefer self-hosted (cost=0) models

    # Latency limits
    max_latency_ms: int = 30000

    # Fallback
    enable_fallback: bool = True
    fallback_to_anthropic: bool = True

    # Shadow mode
    enable_shadow: bool = False          # Run shadow models in parallel for eval

    # Role overrides (force a specific model for a role)
    role_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """The result of a routing decision."""
    model_id: str
    model_card: Optional[ModelCard]
    provider: str
    reason: str
    fallback_model_id: Optional[str] = None
    shadow_model_id: Optional[str] = None
    routing_latency_ms: float = 0.0


class AIRouter:
    """
    Central router for all AI requests.
    Selects the best model and provider based on the routing policy.
    """

    def __init__(self, policy: Optional[RoutingPolicy] = None) -> None:
        self.policy = policy or self._default_policy()
        self._call_count = 0
        self._error_count = 0
        self._fallback_count = 0
        self._total_cost = 0.0

    @staticmethod
    def _default_policy() -> RoutingPolicy:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            return RoutingPolicy(
                profile=DeploymentProfile.PRODUCTION,
                prefer_free=True,
                enable_fallback=True,
                fallback_to_anthropic=False,
            )
        return RoutingPolicy(
            profile=DeploymentProfile.LOCAL,
            prefer_free=True,
            enable_fallback=True,
            fallback_to_anthropic=False,
        )

    def route(self, request: AIRequest) -> RoutingDecision:
        """Determine the best model for a request."""
        start = time.time()
        registry = get_model_registry()

        # 1. Check role overrides
        if request.role and request.role in self.policy.role_overrides:
            override_id = self.policy.role_overrides[request.role]
            card = registry.get(override_id)
            if card and card.enabled:
                return RoutingDecision(
                    model_id=override_id,
                    model_card=card,
                    provider=card.provider.value,
                    reason=f"role_override:{request.role}",
                    routing_latency_ms=(time.time() - start) * 1000,
                )

        # 2. If model_id is already specified, use it directly
        if request.model_id:
            card = registry.get(request.model_id)
            if card and card.enabled:
                fallback = self._find_fallback(request.role) if self.policy.enable_fallback else None
                return RoutingDecision(
                    model_id=request.model_id,
                    model_card=card,
                    provider=card.provider.value,
                    reason="explicit_model",
                    fallback_model_id=fallback,
                    routing_latency_ms=(time.time() - start) * 1000,
                )

        # 3. Route by AI role
        if request.role:
            try:
                role = AIRole(request.role)
            except ValueError:
                role = None

            if role:
                candidates = registry.list_for_role(role)
                best = self._select_best(candidates)
                if best:
                    fallback = self._find_fallback(request.role)
                    shadow = self._find_shadow(role) if self.policy.enable_shadow else None
                    return RoutingDecision(
                        model_id=best.id,
                        model_card=best,
                        provider=best.provider.value,
                        reason=f"role_routing:{role.value}",
                        fallback_model_id=fallback,
                        shadow_model_id=shadow,
                        routing_latency_ms=(time.time() - start) * 1000,
                    )

        # 4. Capability-based routing
        required_caps = self._infer_capabilities(request)
        if required_caps:
            all_models = registry.list_for_profile(self.policy.profile)
            filtered = [
                m for m in all_models
                if all(m.has_capability(cap) for cap in required_caps) and not m.is_fallback
            ]
            if filtered:
                best = self._select_best(filtered)
                if best:
                    return RoutingDecision(
                        model_id=best.id,
                        model_card=best,
                        provider=best.provider.value,
                        reason=f"capability_routing:{[c.value for c in required_caps]}",
                        fallback_model_id=self._find_fallback(None),
                        routing_latency_ms=(time.time() - start) * 1000,
                    )

        # 5. Default: use core reasoning model
        default_card = registry.get_primary_for_role(AIRole.CORE_REASONING)
        if default_card:
            return RoutingDecision(
                model_id=default_card.id,
                model_card=default_card,
                provider=default_card.provider.value,
                reason="default_reasoning",
                fallback_model_id=self._find_fallback(None),
                routing_latency_ms=(time.time() - start) * 1000,
            )

        # 6. Absolute fallback to Anthropic
        if self.policy.fallback_to_anthropic:
            return RoutingDecision(
                model_id="claude-sonnet-4",
                model_card=registry.get("claude-sonnet-4"),
                provider="anthropic",
                reason="absolute_fallback",
                routing_latency_ms=(time.time() - start) * 1000,
            )

        return RoutingDecision(
            model_id="",
            model_card=None,
            provider="none",
            reason="no_model_available",
            routing_latency_ms=(time.time() - start) * 1000,
        )

    def _select_best(self, candidates: list[ModelCard]) -> Optional[ModelCard]:
        """
        Select the best model from candidates using a scoring function.

        Score factors:
        - Profile match (local/prod)
        - Cost (prefer free self-hosted)
        - Latency (prefer fast)
        - Non-fallback preferred
        """
        if not candidates:
            return None

        def score(card: ModelCard) -> float:
            s = 0.0
            # Profile match
            if card.is_available_for(self.policy.profile):
                s += 100
            # Prefer non-fallback
            if not card.is_fallback:
                s += 50
            # Prefer free (self-hosted)
            if self.policy.prefer_free and card.cost_per_1k_input == 0:
                s += 30
            # Lower latency is better
            if card.avg_latency_ms <= self.policy.max_latency_ms:
                s += 20 * (1 - card.avg_latency_ms / max(self.policy.max_latency_ms, 1))
            # Not in shadow mode
            if not card.shadow_mode:
                s += 10
            return s

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def _find_fallback(self, role: Optional[str]) -> Optional[str]:
        if not self.policy.enable_fallback:
            return None
        registry = get_model_registry()

        # Try role-specific fallback
        if role:
            try:
                ai_role = AIRole(role)
                fallback = registry.get_fallback_for_role(ai_role)
                if fallback:
                    return fallback.id
            except ValueError:
                pass

        # General fallback to Anthropic
        if self.policy.fallback_to_anthropic:
            return "claude-sonnet-4"
        return None

    def _find_shadow(self, role: AIRole) -> Optional[str]:
        registry = get_model_registry()
        candidates = registry.list_for_role(role)
        shadows = [m for m in candidates if m.shadow_mode]
        return shadows[0].id if shadows else None

    def _infer_capabilities(self, request: AIRequest) -> list[ModelCapability]:
        """Infer required capabilities from the request."""
        caps = []
        if request.tools:
            caps.append(ModelCapability.TOOL_USE)
            caps.append(ModelCapability.FUNCTION_CALLING)
        if request.response_format and request.response_format.get("type") == "json_object":
            caps.append(ModelCapability.JSON_MODE)
        return caps

    async def execute(self, request: AIRequest) -> AIMessage:
        """
        Route and execute an AI request.
        This is the MAIN entry point for all AI calls in the platform.
        """
        self._call_count += 1
        decision = self.route(request)

        if not decision.model_id:
            return AIMessage(
                content="No model available to handle this request.",
                finish_reason=FinishReason.ERROR,
                trace_id=request.trace_id,
            )

        # Set the resolved model
        request.model_id = decision.model_id

        manager = await get_provider_manager()
        result = await manager.complete_with_fallback(
            request,
            fallback_model_id=decision.fallback_model_id,
        )

        if result.finish_reason == FinishReason.ERROR:
            self._error_count += 1

        self._total_cost += result.cost_usd

        # Log routing decision
        logger.info(
            f"AI call: role={request.role} model={decision.model_id} "
            f"provider={decision.provider} reason={decision.reason} "
            f"latency={result.latency_ms:.0f}ms tokens={result.input_tokens}+{result.output_tokens}"
        )

        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_calls": self._call_count,
            "error_count": self._error_count,
            "fallback_count": self._fallback_count,
            "total_cost_usd": round(self._total_cost, 4),
            "policy": {
                "profile": self.policy.profile.value,
                "prefer_free": self.policy.prefer_free,
                "enable_fallback": self.policy.enable_fallback,
                "enable_shadow": self.policy.enable_shadow,
            },
        }


# Singleton
_router: Optional[AIRouter] = None


def get_ai_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
