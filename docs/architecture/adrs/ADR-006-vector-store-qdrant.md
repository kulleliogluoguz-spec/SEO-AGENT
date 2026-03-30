# ADR-006: Qdrant as Primary Vector Store

**Status:** Accepted
**Date:** 2026-03-28

---

## Context

The platform requires vector similarity search for:
- Brand document retrieval
- Trend document clustering
- Audience signal similarity
- Content similarity and deduplication
- Semantic recommendation ranking

The existing stack uses `pgvector` (PostgreSQL extension). While pgvector is excellent for co-located queries and small-to-medium scale, it has limitations:
- No dedicated ANN index optimized for high-dimensional semantic search at scale
- No built-in payload filtering on the vector index
- Cannot run as an independent service with a rich REST API
- HNSW index must be rebuilt on schema changes

## Decision

**Add Qdrant as the primary dedicated vector store**, while keeping pgvector for:
- Small embedding operations tightly coupled to SQL queries
- Entity-level embeddings stored on relational records

### Qdrant Collections

| Collection | Dimensions | Purpose |
|-----------|-----------|---------|
| `brand_documents` | 768 | Brand/site content embeddings |
| `trend_documents` | 768 | Trend + social document embeddings |
| `audience_signals` | 768 | Audience behavior signal embeddings |
| `content_assets` | 768 | Content piece embeddings |

Dimension: 768 matches `nomic-embed-text` output. If model changes, collections are rebuilt.

### Embedding Model

Default: **nomic-embed-text:latest** via Ollama
- 768 dimensions
- 8192 token context
- Self-hosted, no external API
- Strong multilingual support

### Qdrant Configuration

```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports: ["6333:6333", "6334:6334"]  # REST + gRPC
  volumes:
    - qdrant_data:/qdrant/storage
  environment:
    QDRANT__SERVICE__HTTP_PORT: 6333
    QDRANT__SERVICE__GRPC_PORT: 6334
```

### Access Pattern

All vector operations go through `VectorStoreClient` at `apps/api/app/ai/vectorstore/qdrant_store.py`:
```python
client = VectorStoreClient()
await client.upsert(collection="brand_documents", points=[...])
results = await client.search(collection="brand_documents", query_vector=embedding, limit=10)
```

## Consequences

### Positive
- Dedicated, high-performance ANN search
- Rich payload filtering (filter by workspace_id, source_type, etc.)
- REST + gRPC APIs
- Snapshots for backup
- Horizontal scaling when needed
- Active open-source development

### Negative
- Additional Docker service (minor overhead)
- Separate health check required
- Collections must be managed (creation, schema, reindexing)

## Rejected Alternatives

- **pgvector only:** Adequate for MVP but limits scale and query richness
- **Weaviate:** More complex, heavier memory footprint
- **Chroma:** Less production-ready, no distributed mode
- **Milvus:** Production-grade but significantly heavier to operate
