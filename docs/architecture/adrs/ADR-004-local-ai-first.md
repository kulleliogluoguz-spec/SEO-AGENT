# ADR-004: Local AI First — No External LLM APIs Required

**Status:** Accepted
**Date:** 2026-03-28
**Deciders:** Principal Architect

---

## Context

The platform was originally scaffolded with Anthropic Claude as the primary LLM provider. The `.env.example` defaults to `LLM_DEFAULT_MODEL=claude-sonnet-4-20250514`, which requires an Anthropic API key and sends user data to Anthropic's servers.

The platform vision explicitly prohibits this:
- "The platform must NOT depend on OpenAI, Anthropic, or any external proprietary LLM API."
- "All intelligence must run locally or on user-controlled infrastructure."

The AI provider abstraction already supports Ollama and vLLM. The model registry already defines local models (Qwen3, Llama4, nomic-embed-text) as primaries. The Anthropic model is already marked `enabled=False` in the registry.

## Decision

1. **Default LLM is Ollama serving qwen3:8b** (CPU-compatible, 5GB VRAM).
2. **Default embedding model is nomic-embed-text via Ollama.**
3. **Anthropic provider remains in code as an optional, opt-in fallback** — disabled by default.
4. **`.env.example` will reflect local-first defaults.** No Anthropic API key in defaults.
5. **Ollama is added to `docker-compose.yml`** as a first-class service.
6. **The system must degrade gracefully if Ollama is unavailable** (queue tasks, return health warnings).
7. **vLLM is the production GPU serving option** for teams with dedicated GPU hardware.

## Recommended Local Model Stack

| Role | Model | VRAM Required |
|------|-------|--------------|
| Core reasoning (GPU) | qwen3:235b-a22b | 48GB |
| Tool execution (GPU) | qwen3:30b-a3b | 8GB |
| Default dev/CPU | qwen3:8b | 5GB (or CPU) |
| Classification/routing | qwen3:1.7b | 1.5GB |
| Embedding | nomic-embed-text | 0.5GB |

## Consequences

### Positive
- No data leaves the deployment boundary
- No API costs
- No rate limits from external providers
- Full auditability of all inference
- Works in air-gapped environments

### Negative
- Initial setup requires pulling models (1-50GB download)
- Quality on qwen3:8b (CPU fallback) is lower than frontier models
- GPU hardware is needed for best quality
- Anthropic/OpenAI users who want to optionally use their API keys need to opt in

## Optional API Provider Support

Users who want to optionally use external LLM APIs can:
1. Set `LLM_EXTERNAL_PROVIDER=anthropic` (or `openai`)
2. Provide the appropriate API key in `.env`
3. Set `ANTHROPIC_ENABLED=true`

The system will NEVER require this. It must always work with local models only.
