"""
Local Embedding Pipeline

Computes embeddings entirely locally via:
  1. Ollama (primary) — nomic-embed-text or any Ollama-served embedding model
  2. sentence-transformers (fallback) — direct Python inference

No external API is called. All data stays local.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Maximum number of texts to embed in a single batch request
DEFAULT_BATCH_SIZE = 32


class LocalEmbedder:
    """
    Compute text embeddings using a locally-served model.

    Priority order:
    1. Ollama (if OLLAMA_BASE_URL is set and the model is available)
    2. sentence-transformers (local Python inference, no server needed)

    Usage:
        embedder = LocalEmbedder()
        vectors = await embedder.embed(["hello world", "another text"])
    """

    def __init__(
        self,
        model: str | None = None,
        ollama_base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self.ollama_base_url = (
            ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.dimensions = dimensions or int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        self._st_model = None  # sentence-transformers lazy init
        self._ollama_available: Optional[bool] = None  # cached probe result

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns list of float vectors."""
        if not texts:
            return []

        # Try Ollama first
        if await self._is_ollama_available():
            try:
                return await self._embed_ollama_batch(texts)
            except Exception as e:
                logger.warning(f"Ollama embedding failed, falling back to sentence-transformers: {e}")
                self._ollama_available = False

        # Fallback: sentence-transformers (synchronous — run in thread pool)
        return await asyncio.get_event_loop().run_in_executor(
            None, self._embed_st_sync, texts
        )

    async def embed_one(self, text: str) -> list[float]:
        """Embed a single text string."""
        results = await self.embed([text])
        return results[0] if results else []

    async def _is_ollama_available(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                self._ollama_available = response.status_code == 200
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    async def _embed_ollama_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using Ollama's /api/embed endpoint."""
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            base_url=self.ollama_base_url,
        ) as client:
            # Ollama supports batch embedding via /api/embed
            response = await client.post(
                "/api/embed",
                json={"model": self.model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()

            # Ollama returns {"embeddings": [[...], [...], ...]}
            embeddings = data.get("embeddings", [])
            if not embeddings:
                raise ValueError(f"Ollama returned empty embeddings for model {self.model}")
            return embeddings

    def _embed_st_sync(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using sentence-transformers (synchronous, runs in thread pool)."""
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                st_model_name = os.getenv("EMBEDDING_ST_MODEL", "nomic-ai/nomic-embed-text-v1.5")
                logger.info(f"Loading sentence-transformers model: {st_model_name}")
                self._st_model = SentenceTransformer(st_model_name, trust_remote_code=True)
            except ImportError:
                raise RuntimeError(
                    "Neither Ollama nor sentence-transformers is available. "
                    "Start Ollama (docker compose up ollama) or install sentence-transformers."
                )

        embeddings = self._st_model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]

    async def health_check(self) -> dict:
        """Check embedding service health."""
        ollama_ok = await self._is_ollama_available()
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "ollama_available": ollama_ok,
            "backend": "ollama" if ollama_ok else "sentence-transformers",
        }


def make_content_hash(text: str) -> str:
    """SHA-256 hash of text content, for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Singleton ──────────────────────────────────────────────────────────────────

_embedder: LocalEmbedder | None = None


def get_embedder() -> LocalEmbedder:
    """Get the global LocalEmbedder singleton."""
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedder()
    return _embedder
