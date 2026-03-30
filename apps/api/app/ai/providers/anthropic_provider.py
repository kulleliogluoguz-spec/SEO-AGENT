"""
Anthropic Provider — API fallback for when self-hosted models are unavailable.

This preserves compatibility with the existing ANTHROPIC_API_KEY setup
while the system transitions to primarily open-source self-hosted models.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, AsyncIterator, Optional

import httpx

from app.ai.providers.base import (
    AIMessage,
    AIRequest,
    BaseProvider,
    FinishReason,
    ToolCall,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Fallback provider using the Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        return bool(self.api_key) and self.api_key != "your-anthropic-api-key-here"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
        return self._client

    async def complete(self, request: AIRequest) -> AIMessage:
        if not self.is_configured():
            return AIMessage(
                content="Anthropic API key not configured. Using demo mode.",
                finish_reason=FinishReason.ERROR,
                model_id=request.model_id,
                provider=self.provider_name,
                trace_id=request.trace_id,
            )

        client = await self._get_client()
        start = time.time()

        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.system:
            payload["system"] = request.system
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)
        if request.stop:
            payload["stop_sequences"] = request.stop

        try:
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic HTTP error: {e.response.status_code} - {e.response.text}")
            return AIMessage(
                content=f"Anthropic API error: {e.response.status_code}",
                finish_reason=FinishReason.ERROR,
                model_id=request.model_id,
                provider=self.provider_name,
                latency_ms=self._track_latency(start),
                trace_id=request.trace_id,
            )
        except httpx.RequestError as e:
            return AIMessage(
                content=f"Connection error: {str(e)}",
                finish_reason=FinishReason.ERROR,
                model_id=request.model_id,
                provider=self.provider_name,
                latency_ms=self._track_latency(start),
                trace_id=request.trace_id,
            )

        # Parse Anthropic response format
        content_text = ""
        tool_calls = []
        for block in data.get("content", []):
            if block["type"] == "text":
                content_text += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block["name"],
                    arguments=block.get("input", {}),
                ))

        usage = data.get("usage", {})
        stop_reason = data.get("stop_reason", "end_turn")
        finish_reason = FinishReason.TOOL_CALLS if tool_calls else FinishReason.STOP

        return AIMessage(
            content=content_text,
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            model_id=request.model_id,
            provider=self.provider_name,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=self._track_latency(start),
            trace_id=request.trace_id,
            cost_usd=self._estimate_cost(
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                request.model_id,
            ),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        if not self.is_configured():
            yield "Anthropic API key not configured."
            return

        client = await self._get_client()
        payload = {
            "model": request.model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.system:
            payload["system"] = request.system

        async with client.stream("POST", "/v1/messages", json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if text := delta.get("text", ""):
                                yield text
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {"status": "unconfigured", "provider": self.provider_name}
        return {"status": "healthy", "provider": self.provider_name}

    async def list_models(self) -> list[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20251001",
        ]

    def _convert_tools(self, openai_tools: list[dict]) -> list[dict]:
        """Convert OpenAI-format tools to Anthropic format."""
        anthropic_tools = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                fn = tool["function"]
                anthropic_tools.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })
        return anthropic_tools

    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        rates = {
            "claude-sonnet-4-20250514": (0.003, 0.015),
            "claude-haiku-4-5-20251001": (0.001, 0.005),
        }
        input_rate, output_rate = rates.get(model, (0.003, 0.015))
        return (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
