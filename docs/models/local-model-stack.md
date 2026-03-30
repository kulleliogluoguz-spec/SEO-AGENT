# Local Model Stack

This document describes the complete local AI model stack for the AI Growth OS platform.
All models run locally via Ollama or vLLM. No external LLM API is required.

---

## Quick Start

```bash
# Start Ollama (included in docker-compose)
docker compose up ollama -d

# Pull recommended models
make models-pull

# Or pull individually:
docker exec aicmo-ollama ollama pull nomic-embed-text
docker exec aicmo-ollama ollama pull qwen3:8b
docker exec aicmo-ollama ollama pull qwen3:30b-a3b
```

---

## Model Tiers

### Tier 1 — Minimum (CPU-only, any machine)

| Model | Size | RAM Required | Purpose |
|-------|------|-------------|---------|
| `qwen3:8b` | ~5GB | 8GB RAM | Core reasoning, all tasks |
| `nomic-embed-text` | ~0.5GB | 1GB RAM | Embeddings |

All async pipeline tasks work with this tier. Response quality is good but not frontier-level.

### Tier 2 — Recommended (Consumer GPU, 8-16GB VRAM)

| Model | VRAM | Purpose |
|-------|------|---------|
| `qwen3:30b-a3b` | 8GB | Tool execution, structured output |
| `qwen3:8b` | 5GB | Fast classification, routing |
| `nomic-embed-text` | 0.5GB | Embeddings |

### Tier 3 — Full Stack (Production GPU, 48GB+ VRAM)

| Model | VRAM | Purpose |
|-------|------|---------|
| `qwen3:235b-a22b` | 48GB | Core reasoning, deep analysis |
| `qwen3:30b-a3b` | 8GB | Tool execution |
| `qwen3:8b` | 5GB | Classification, guardrails |
| `qwen3:1.7b` | 1.5GB | Ultra-fast routing |
| `nomic-embed-text` | 0.5GB | Embeddings |
| `llama4:scout` | 24GB | Vision/multimodal tasks |

---

## Model Roles

Each agent task is mapped to a logical AI role, which maps to a physical model:

| AI Role | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| `core_reasoning` | qwen3:8b | qwen3:30b-a3b | qwen3:235b-a22b |
| `tool_execution` | qwen3:8b | qwen3:30b-a3b | qwen3:30b-a3b |
| `structured_output` | qwen3:8b | qwen3:30b-a3b | qwen3:30b-a3b |
| `classification` | qwen3:8b | qwen3:8b | qwen3:1.7b |
| `routing` | qwen3:8b | qwen3:8b | qwen3:1.7b |
| `summarization` | qwen3:8b | qwen3:8b | qwen3:8b |
| `content_strategy` | qwen3:8b | qwen3:30b-a3b | qwen3:235b-a22b |
| `report_synthesis` | qwen3:8b | qwen3:30b-a3b | qwen3:235b-a22b |
| `guardrail` | qwen3:8b | qwen3:8b | qwen3:8b |

---

## Embedding Models

### Primary: nomic-embed-text (via Ollama)
- **Dimensions:** 768
- **Context:** 8192 tokens
- **License:** Apache 2.0
- **Quality:** Excellent for English, good for multilingual
- **Pull:** `ollama pull nomic-embed-text`

### Alternative: bge-m3 (via sentence-transformers)
- **Dimensions:** 1024
- **Context:** 8192 tokens
- **License:** MIT
- **Quality:** State-of-the-art multilingual
- **Use when:** Better multilingual coverage needed
- **Python:** `from sentence_transformers import SentenceTransformer; SentenceTransformer("BAAI/bge-m3")`

### Reranker: bge-reranker-v2-m3 (via sentence-transformers)
- Used for re-ranking search results after initial vector retrieval
- Improves precision significantly
- **Python:** `from sentence_transformers import CrossEncoder; CrossEncoder("BAAI/bge-reranker-v2-m3")`

---

## Serving Configuration

### Ollama (development + production)

Ollama runs as a Docker service:
```yaml
ollama:
  image: ollama/ollama:latest
  container_name: aicmo-ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama_models:/root/.ollama
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

Ollama exposes an OpenAI-compatible API at `http://ollama:11434/v1`.

### vLLM (production, multi-GPU)

For production GPU servers, vLLM provides better throughput:
```bash
docker run --gpus all \
  -p 8001:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-30B-A3B \
  --quantization awq \
  --max-model-len 32768
```

Set `VLLM_BASE_URL=http://vllm:8001/v1` in `.env`.

---

## Environment Configuration

```bash
# .env — Local AI settings

# Primary LLM provider (ollama | vllm | anthropic)
LLM_PRIMARY_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434

# Default models
LLM_DEFAULT_MODEL=qwen3:8b
LLM_FAST_MODEL=qwen3:8b
LLM_REASONING_MODEL=qwen3:8b

# Embedding
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768

# Anthropic (opt-in only, disabled by default)
ANTHROPIC_ENABLED=false
# ANTHROPIC_API_KEY=your-key-here
```

---

## Health Checks

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Check available models
curl http://localhost:11434/v1/models

# Check embedding model
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}'
```

Via API:
```bash
GET /api/v1/ai/health
```

---

## Model Pull Automation

The `make models-pull` command pulls all required models for the configured tier:

```makefile
models-pull:
	docker exec aicmo-ollama ollama pull nomic-embed-text
	docker exec aicmo-ollama ollama pull qwen3:8b

models-pull-tier2:
	$(MAKE) models-pull
	docker exec aicmo-ollama ollama pull qwen3:30b-a3b

models-pull-tier3:
	$(MAKE) models-pull-tier2
	docker exec aicmo-ollama ollama pull qwen3:235b-a22b
```

---

## GPU vs CPU Performance

| Task | CPU (qwen3:8b) | GPU 8B | GPU 30B | GPU 235B |
|------|---------------|--------|---------|---------|
| Brand profile build | ~3 min | ~20s | ~45s | ~90s |
| Trend analysis | ~2 min | ~15s | ~30s | ~60s |
| GEO audit | ~5 min | ~40s | ~80s | ~180s |
| Embedding (100 docs) | ~30s | ~3s | ~3s | ~3s |
| Report generation | ~10 min | ~90s | ~150s | ~240s |

CPU-only mode is functional for development and light production workloads. All pipeline jobs are async, so latency is acceptable even on CPU.
