"""
Provider Manager — Manages all AI provider instances.

Handles:
- Provider initialization based on config
- Health monitoring
- Provider selection for model IDs
- Graceful shutdown
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from app.ai.providers.base import AIMessage, AIRequest, BaseProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.vllm_provider import VLLMProvider
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.registry.model_registry import ModelProvider, get_model_registry

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Manages provider instances and routes requests to the correct provider
    based on the model's registered provider type.
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all configured providers."""
        if self._initialized:
            return

        # Ollama (local dev)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._providers["ollama"] = OllamaProvider(base_url=ollama_url)

        # vLLM (production)
        vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
        vllm_key = os.getenv("VLLM_API_KEY", "EMPTY")
        self._providers["vllm"] = VLLMProvider(base_url=vllm_url, api_key=vllm_key)

        # Anthropic (fallback)
        self._providers["anthropic"] = AnthropicProvider()

        self._initialized = True
        logger.info(f"ProviderManager initialized with providers: {list(self._providers.keys())}")

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        return self._providers.get(provider_name)

    def get_provider_for_model(self, model_id: str) -> Optional[BaseProvider]:
        """Look up the model in the registry and return its provider."""
        registry = get_model_registry()
        card = registry.get(model_id)
        if card is None:
            return None
        return self._providers.get(card.provider.value)

    async def complete(self, request: AIRequest) -> AIMessage:
        """Route a completion request to the correct provider."""
        provider = self.get_provider_for_model(request.model_id)
        if provider is None:
            # Try to resolve model_id as a provider-specific model string
            registry = get_model_registry()
            for card in registry.list_enabled():
                if card.serving_model_id == request.model_id:
                    provider = self._providers.get(card.provider.value)
                    break

        if provider is None:
            logger.error(f"No provider found for model: {request.model_id}")
            return AIMessage(
                content=f"No provider available for model: {request.model_id}",
                finish_reason="error",
                model_id=request.model_id,
                trace_id=request.trace_id,
            )

        # Resolve serving model ID
        registry = get_model_registry()
        card = registry.get(request.model_id)
        if card and card.serving_model_id:
            request.model_id = card.serving_model_id

        return await provider.complete(request)

    async def complete_with_fallback(
        self,
        request: AIRequest,
        fallback_model_id: Optional[str] = None,
    ) -> AIMessage:
        """Try primary model, fall back on failure."""
        result = await self.complete(request)

        if result.finish_reason.value == "error" and fallback_model_id:
            logger.warning(
                f"Primary model {request.model_id} failed, falling back to {fallback_model_id}"
            )
            fallback_request = AIRequest(
                messages=request.messages,
                model_id=fallback_model_id,
                system=request.system,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
                tool_choice=request.tool_choice,
                response_format=request.response_format,
                trace_id=request.trace_id,
                role=request.role,
            )
            result = await self.complete(fallback_request)

        return result

    async def health_check_all(self) -> dict[str, Any]:
        """Check health of all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results

    async def list_available_models(self) -> dict[str, list[str]]:
        """List models available on each provider."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.list_models()
            except Exception as e:
                results[name] = []
                logger.warning(f"Failed to list models for {name}: {e}")
        return results

    async def shutdown(self) -> None:
        """Gracefully close all providers."""
        for name, provider in self._providers.items():
            try:
                await provider.close()
            except Exception as e:
                logger.warning(f"Error closing provider {name}: {e}")
        self._initialized = False


# Singleton
_manager: Optional[ProviderManager] = None


async def get_provider_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
        await _manager.initialize()
    return _manager
