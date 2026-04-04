"""
Qdrant Vector Store Client

Provides semantic search, document indexing, and similarity retrieval
via a locally-running Qdrant instance.

Collections:
  - brand_documents    : brand/site content embeddings
  - trend_documents    : trend + social document embeddings
  - audience_signals   : audience behavior signal embeddings
  - content_assets     : content piece embeddings

See: docs/architecture/adrs/ADR-006-vector-store-qdrant.md
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CollectionName(str, Enum):
    BRAND_DOCUMENTS = "brand_documents"
    TREND_DOCUMENTS = "trend_documents"
    AUDIENCE_SIGNALS = "audience_signals"
    CONTENT_ASSETS = "content_assets"


@dataclass
class VectorPoint:
    """A single vector point to store in Qdrant."""

    id: str  # UUID string
    vector: list[float]  # Embedding vector
    payload: dict[str, Any] = field(default_factory=dict)  # Metadata for filtering


@dataclass
class SearchResult:
    """A single result from a similarity search."""

    id: str
    score: float  # Cosine similarity score (0-1)
    payload: dict[str, Any] = field(default_factory=dict)


class QdrantStore:
    """
    Wrapper around the Qdrant vector database client.

    Handles:
    - Collection management (create, ensure exists)
    - Document upsert (create or update)
    - Semantic search with payload filters
    - Health checking
    - Graceful degradation if Qdrant is unavailable
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY", "")
        self.dimensions = dimensions or int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        self._client = None
        self._available: bool | None = None

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.models import Distance, VectorParams  # noqa: F401

                kwargs: dict[str, Any] = {"url": self.url}
                if self.api_key:
                    kwargs["api_key"] = self.api_key

                self._client = QdrantClient(**kwargs)
                logger.info(f"Qdrant client initialized at {self.url}")
            except ImportError:
                raise RuntimeError("qdrant-client is not installed. Run: pip install qdrant-client")
        return self._client

    async def ensure_collections(self) -> None:
        """Create all required collections if they don't exist."""
        try:
            client = self._get_client()
            from qdrant_client.http.models import Distance, VectorParams

            existing = {c.name for c in client.get_collections().collections}

            for collection in CollectionName:
                if collection.value not in existing:
                    client.create_collection(
                        collection_name=collection.value,
                        vectors_config=VectorParams(
                            size=self.dimensions,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info(f"Created Qdrant collection: {collection.value}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collections: {e}")
            raise

    async def upsert(
        self,
        collection: CollectionName | str,
        points: list[VectorPoint],
    ) -> int:
        """
        Upsert vector points into a collection.
        Returns number of points upserted.
        """
        if not points:
            return 0

        collection_name = collection.value if isinstance(collection, CollectionName) else collection

        try:
            client = self._get_client()
            from qdrant_client.http.models import PointStruct

            qdrant_points = [
                PointStruct(
                    id=p.id,
                    vector=p.vector,
                    payload=p.payload,
                )
                for p in points
            ]

            client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )
            return len(points)
        except Exception as e:
            logger.error(f"Qdrant upsert failed in {collection_name}: {e}")
            raise

    async def search(
        self,
        collection: CollectionName | str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        """
        Semantic similarity search.

        Args:
            collection: Target collection
            query_vector: Query embedding
            limit: Max results to return
            filters: Qdrant payload filter conditions (e.g. {"workspace_id": "uuid"})
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of SearchResult ordered by descending similarity
        """
        collection_name = collection.value if isinstance(collection, CollectionName) else collection

        try:
            client = self._get_client()

            qdrant_filter = None
            if filters:
                from qdrant_client.http.models import FieldCondition, Filter, MatchValue

                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()
                ]
                qdrant_filter = Filter(must=conditions)

            results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                score_threshold=score_threshold,
            )

            return [
                SearchResult(
                    id=str(r.id),
                    score=r.score,
                    payload=r.payload or {},
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed in {collection_name}: {e}")
            return []

    async def delete(
        self,
        collection: CollectionName | str,
        ids: list[str],
    ) -> None:
        """Delete points by ID."""
        collection_name = collection.value if isinstance(collection, CollectionName) else collection
        try:
            client = self._get_client()
            from qdrant_client.http.models import PointIdsList

            client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=ids),
            )
        except Exception as e:
            logger.error(f"Qdrant delete failed in {collection_name}: {e}")
            raise

    async def count(self, collection: CollectionName | str) -> int:
        """Count points in a collection."""
        collection_name = collection.value if isinstance(collection, CollectionName) else collection
        try:
            client = self._get_client()
            result = client.count(collection_name=collection_name, exact=True)
            return result.count
        except Exception as e:
            logger.warning(f"Qdrant count failed for {collection_name}: {e}")
            return 0

    async def health_check(self) -> dict[str, Any]:
        """Check Qdrant connectivity and collection health."""
        try:
            client = self._get_client()
            collections = client.get_collections().collections
            collection_info = {
                c.name: client.count(collection_name=c.name, exact=False).count for c in collections
            }
            return {
                "status": "healthy",
                "url": self.url,
                "collections": collection_info,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "url": self.url,
                "error": str(e),
            }


def make_stable_id(namespace: str, key: str) -> str:
    """Generate a stable deterministic UUID from a namespace + key pair."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}:{key}"))


# ── Singleton ──────────────────────────────────────────────────────────────────

_store: QdrantStore | None = None


def get_vector_store() -> QdrantStore:
    """Get the global QdrantStore singleton."""
    global _store
    if _store is None:
        _store = QdrantStore()
    return _store
