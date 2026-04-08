"""
AI Model Configuration — Local Model Stack
All inference local via Ollama. Zero external API calls.

Selects the best available model from a single quality-ordered ranking
and falls back to the next one if the top choice isn't installed locally.
This avoids wasting connection timeouts on models that aren't present.
"""

from __future__ import annotations

import logging
import os
import re
from enum import Enum

import requests

logger = logging.getLogger(__name__)
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# Single source of truth for model preference order. The selector walks this
# list and returns the first one that is actually installed locally.
#
# Update this list when new models are pulled. Keep it short — every entry
# is a candidate the selector has to verify against `ollama list`.
MODEL_QUALITY_RANKING = [
    "qwen3:14b",
    "qwen3:8b",
]


class TaskType(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    REASONING = "reasoning"
    MULTILINGUAL = "multilingual"
    CREATIVE = "creative"


class ModelSelector:
    """Pick the best installed Ollama model from `MODEL_QUALITY_RANKING`."""

    _available: list[str] | None = None

    @classmethod
    def get_available(cls) -> list[str]:
        if cls._available is None:
            try:
                r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
                cls._available = [m["name"] for m in r.json().get("models", [])]
            except Exception:
                cls._available = ["qwen3:8b"]
        return cls._available

    @classmethod
    def invalidate_cache(cls) -> None:
        """Force the next call to re-query Ollama for the installed models."""
        cls._available = None

    # Back-compat alias — older callers used reset_cache().
    reset_cache = invalidate_cache

    @classmethod
    def get_best_model(cls) -> str:
        """
        Walk MODEL_QUALITY_RANKING in order and return the first installed
        match. Match is exact (`name:tag`) or by base name (`name` matches
        any tag of that name) so the ranking entries can be specific or
        generic. Falls back to the first locally-available model, then to
        `qwen3:8b` as a last resort.
        """
        avail = cls.get_available()
        for candidate in MODEL_QUALITY_RANKING:
            # Exact match first
            if candidate in avail:
                return candidate
            # Then base-name match (e.g. "qwen3:14b" -> any "qwen3:*")
            base = candidate.split(":")[0]
            for a in avail:
                if a.split(":")[0] == base:
                    return a
        return avail[0] if avail else "qwen3:8b"

    @classmethod
    def select(cls, task: TaskType) -> str:
        """
        Pick a model for the given task type.

        Currently every task uses the same single quality ranking — qwen3:14b
        is the primary, qwen3:8b is the only fallback. The `task` parameter
        is kept for API compatibility with existing callers (lead_qualifier,
        discovery_engine, finance, email_bridge) so we can re-introduce
        per-task differentiation later without touching them.
        """
        return cls.get_best_model()


def call_ollama(
    prompt: str,
    task: TaskType = TaskType.STANDARD,
    model: str | None = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
    system: str | None = None,
    timeout: int = 120,
) -> str:
    """Universal Ollama call with model selection and graceful error handling."""
    selected = model or ModelSelector.select(task)
    payload: dict = {
        "model": selected,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }
    if system:
        payload["system"] = system
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        # qwen3 emits <think>...</think> reasoning blocks — strip them.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text
    except requests.exceptions.Timeout:
        logger.warning("Ollama timeout for model %s", selected)
        return "[AI timeout — model loading. Retry in 30s.]"
    except requests.exceptions.ConnectionError:
        return "[AI unavailable — run: ollama serve]"
    except Exception as e:
        logger.error("Ollama error: %s", e)
        return f"[AI error: {str(e)[:100]}]"


def call_ollama_json(
    prompt: str,
    schema_example: dict,
    task: TaskType = TaskType.STANDARD,
    model: str | None = None,
    timeout: int = 120,
) -> dict:
    """Call Ollama and parse a JSON object out of the response."""
    import json

    json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No explanation, no markdown, no backticks.
Example format: {str(schema_example)}"""
    response = call_ollama(
        json_prompt,
        task=task,
        model=model,
        max_tokens=1000,
        temperature=0.1,
        timeout=timeout,
    )
    cleaned = response.strip()
    for fence in ("```json", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence) :].lstrip()
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")].rstrip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        logger.error("JSON parse failed: %s", cleaned[:200])
        return {}
