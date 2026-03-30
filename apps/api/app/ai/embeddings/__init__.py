"""Local embedding pipeline. All embeddings computed locally — no external API."""
from app.ai.embeddings.embedder import LocalEmbedder, get_embedder

__all__ = ["LocalEmbedder", "get_embedder"]
