"""
AI Provider Abstraction Layer
=============================
Unified interface for all model providers (Ollama, vLLM, OpenAI-compat, Anthropic, LiteLLM).
Each provider implements the same BaseProvider interface.
"""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    ERROR = "error"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AIMessage:
    """Unified response from any provider."""
    content: str = ""
    role: str = "assistant"
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: FinishReason = FinishReason.STOP

    # Metadata
    model_id: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    trace_id: str = ""
    cost_usd: float = 0.0

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class AIRequest:
    """Unified request to any provider."""
    messages: list[dict[str, Any]]
    model_id: str = ""                    # Registry model ID
    system: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: Optional[str] = None     # "auto", "required", "none"
    response_format: Optional[dict] = None  # {"type": "json_object"}
    stop: Optional[list[str]] = None
    stream: bool = False

    # Routing hints
    role: Optional[str] = None             # AIRole hint for the router
    priority: str = "normal"               # "low", "normal", "high"
    timeout_ms: int = 60000
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    workspace_id: Optional[str] = None
    site_id: Optional[str] = None
    agent_id: Optional[str] = None


class BaseProvider(abc.ABC):
    """Abstract base class for all AI providers."""

    provider_name: str = "base"

    @abc.abstractmethod
    async def complete(self, request: AIRequest) -> AIMessage:
        """Generate a completion."""
        ...

    @abc.abstractmethod
    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health."""
        ...

    @abc.abstractmethod
    async def list_models(self) -> list[str]:
        """List available models on this provider."""
        ...

    def _track_latency(self, start: float) -> float:
        return (time.time() - start) * 1000
