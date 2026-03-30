# Local AI Setup Guide

## Quick Start (5 minutes)

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download
```

### 2. Pull the minimum required model

```bash
# Small fast model for routing + basic reasoning (~5GB)
ollama pull qwen3:8b

# Embedding model (~275MB)
ollama pull nomic-embed-text:latest
```

### 3. Configure environment

Add to your `.env`:
```bash
AI_MODE=local
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Start the platform

```bash
make up
# Ollama should already be running from step 1
```

The AI subsystem auto-detects Ollama and routes all AI calls through local models.

## Recommended Local Setup (14GB VRAM)

If you have a GPU with 14GB+ VRAM (RTX 4080, RTX 3090, etc.):

```bash
# Tool/structured output model (excellent quality, 8GB)
ollama pull qwen3:30b-a3b

# Router/classifier (5GB)
ollama pull qwen3:8b

# Embeddings (275MB)
ollama pull nomic-embed-text:latest
```

## Full Local Setup (50GB+ VRAM)

For development with the full model lineup:

```bash
ollama pull qwen3:8b           # Router/classifier
ollama pull qwen3:30b-a3b      # Tool use / structured output
ollama pull qwen2.5-coder:32b  # Code generation
ollama pull llama4:scout        # Multimodal (vision)
ollama pull nomic-embed-text    # Embeddings
# qwen3:235b-a22b requires ~48GB VRAM — only for serious GPU setups
```

## Docker-based Local Setup

If you prefer Docker for everything:

```bash
docker compose -f docker-compose.yml -f docker-compose.ai.yml up
```

This starts Ollama as a Docker service and auto-pulls `qwen3:8b` and `nomic-embed-text`.

## CPU-Only Mode

Ollama works on CPU (slower but functional):

```bash
ollama pull qwen3:1.7b    # Tiny model, fast even on CPU
ollama pull nomic-embed-text
```

Set in `.env`:
```bash
AI_MODE=local
# The router will use qwen3:1.7b for everything
```

## Verify Setup

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check AI subsystem health (after platform is running)
curl http://localhost:8000/api/v1/ai/providers/health

# Check available models
curl http://localhost:8000/api/v1/ai/providers/models
```

## Hybrid Mode (Local + API Fallback)

For local development with Anthropic API as fallback:

```bash
AI_MODE=local
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=sk-ant-...
AI_ROUTER_FALLBACK_TO_ANTHROPIC=true
```

The router will use local Ollama models first, falling back to Claude Sonnet 4 on errors.

## Troubleshooting

**Ollama not responding**: Check `ollama serve` is running. Default port is 11434.

**Out of VRAM**: Use smaller models. `qwen3:8b` works in 5GB, `qwen3:1.7b` in 1.5GB.

**Slow generation**: Expected on CPU. Use GPU for interactive workloads, or set higher timeouts.

**Model not found**: Run `ollama list` to see pulled models. Pull missing ones with `ollama pull <name>`.
