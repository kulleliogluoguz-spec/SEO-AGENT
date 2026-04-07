"""
AI Model Configuration — Local Model Stack
All inference local via Ollama. Zero external API calls.

Selects the best available model for a task and falls back to whatever
exists locally (typically qwen3:8b on this workstation).
"""
from __future__ import annotations

import logging
import os
import re
from enum import Enum
from typing import Optional

import requests

logger = logging.getLogger(__name__)
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class TaskType(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    REASONING = "reasoning"
    MULTILINGUAL = "multilingual"
    CREATIVE = "creative"


class ModelSelector:
    """Pick the best installed Ollama model for the requested task."""

    TASK_MODELS = {
        TaskType.FAST:         ["qwen3:8b", "gemma4:2b", "gemma3n:e4b", "llama3.2"],
        TaskType.STANDARD:     ["gemma4:27b", "qwen3:14b", "qwen3:8b", "gemma3n:e4b"],
        TaskType.REASONING:    ["deepseek-r1:8b", "gemma4:27b", "qwen3:8b"],
        TaskType.MULTILINGUAL: ["qwen3:14b", "qwen3:8b", "gemma4:27b", "gemma3n:e4b"],
        TaskType.CREATIVE:     ["gemma4:27b", "qwen3:14b", "qwen3:8b"],
    }
    _available: Optional[list[str]] = None

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
    def reset_cache(cls) -> None:
        cls._available = None

    @classmethod
    def select(cls, task: TaskType) -> str:
        avail = cls.get_available()
        for candidate in cls.TASK_MODELS.get(task, ["qwen3:8b"]):
            base = candidate.split(":")[0]
            for a in avail:
                if base in a:
                    return a
        return avail[0] if avail else "qwen3:8b"


def call_ollama(
    prompt: str,
    task: TaskType = TaskType.STANDARD,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
    system: Optional[str] = None,
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
    model: Optional[str] = None,
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
            cleaned = cleaned[len(fence):].lstrip()
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
