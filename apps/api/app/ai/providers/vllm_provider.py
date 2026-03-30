"""
vLLM Provider — Production-grade GPU model serving.

Connects to vLLM's OpenAI-compatible API.
Used for high-throughput production deployments.
"""

from __future__ import annotations

import json
import logging
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


class VLLMProvider(BaseProvider):
    """Provider for vLLM-served models in production."""

    provider_name = "vllm"

    def __init__(
        self,
        base_url: str = "http://localhost:8001/v1",
        api_key: str = "EMPTY",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client

    async def complete(self, request: AIRequest) -> AIMessage:
        client = await self._get_client()
        start = time.time()

        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.extend(request.messages)

        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if request.tools:
            payload["tools"] = request.tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.stop:
            payload["stop"] = request.stop

        # vLLM supports guided decoding for structured output
        # payload["guided_json"] = schema  # if needed

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"vLLM HTTP error: {e.response.status_code}")
            return AIMessage(
                content=f"Provider error: {e.response.status_code}",
                finish_reason=FinishReason.ERROR,
                model_id=request.model_id,
                provider=self.provider_name,
                latency_ms=self._track_latency(start),
                trace_id=request.trace_id,
            )
        except httpx.RequestError as e:
            logger.error(f"vLLM connection error: {e}")
            return AIMessage(
                content=f"Connection error: {str(e)}",
                finish_reason=FinishReason.ERROR,
                model_id=request.model_id,
                provider=self.provider_name,
                latency_ms=self._track_latency(start),
                trace_id=request.trace_id,
            )

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        tool_calls = []
        for tc in message.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=fn.get("name", ""),
                arguments=args,
            ))

        finish = choice.get("finish_reason", "stop")
        return AIMessage(
            content=message.get("content", "") or "",
            role=message.get("role", "assistant"),
            tool_calls=tool_calls,
            finish_reason=FinishReason.TOOL_CALLS if tool_calls else FinishReason(finish or "stop"),
            model_id=request.model_id,
            provider=self.provider_name,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=self._track_latency(start),
            trace_id=request.trace_id,
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        client = await self._get_client()
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.extend(request.messages)

        payload = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content", ""):
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> dict[str, Any]:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            response.raise_for_status()
            return {"status": "healthy", "provider": self.provider_name}
        except Exception as e:
            return {"status": "unhealthy", "provider": self.provider_name, "error": str(e)}

    async def list_models(self) -> list[str]:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
