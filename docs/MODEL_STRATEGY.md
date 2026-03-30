# Model Strategy — AI CMO OS

## Philosophy

We use **multiple specialized models** rather than a single general-purpose model. This gives us:
- Better quality per task (right-sized model for the job)
- Lower cost (small models for simple tasks)
- Lower latency (fast models for routing/classification)
- Self-hosting independence (no API vendor lock-in)
- Fine-tuning flexibility (adapt the right model for the right domain)

## Model Lineup (March 2026)

### Tier 1: Core Reasoning — Qwen3-235B-A22B (MoE)
- **Role**: Deep analysis, strategy, recommendations, long-form generation
- **Why**: Best open-weight reasoning model. 235B total params, only 22B active per token (MoE efficiency). Competitive with frontier API models on reasoning benchmarks.
- **Serving**: vLLM with AWQ quantization (production), Ollama (dev — requires 48GB+ VRAM)
- **Context**: 131K tokens
- **Use cases**: SEO audits, recommendation generation, competitor analysis, report synthesis, content strategy

### Tier 2: Tool/Structured — Qwen3-30B-A3B (MoE)
- **Role**: Tool calling, structured output, function execution, JSON generation
- **Why**: Extremely fast MoE (3B active), excellent tool-calling accuracy, fits in 8GB VRAM quantized.
- **Serving**: Ollama (local), vLLM (production)
- **Use cases**: API planning, connector interactions, social content adaptation, ad copy

### Tier 3: Coding — Qwen2.5-Coder-32B
- **Role**: Code generation, schema creation, workflow logic, rule writing
- **Why**: Top-performing open code model. Strong at structured generation.
- **Serving**: Ollama (Q4_K_M), vLLM (production)
- **Use cases**: Schema markup generation, automation rules, prompt engineering support

### Tier 4: Fast/Router — Qwen3-8B
- **Role**: Classification, routing, guardrails, quick summarization
- **Why**: Fast, capable, 5GB VRAM. Handles routing/classification with high accuracy.
- **Serving**: Ollama (always available locally)
- **Use cases**: Task routing, sentiment checks, content triage, guardrail decisions

### Tier 5: Tiny — Qwen3-1.7B
- **Role**: Ultra-fast classification and binary decisions
- **Why**: 1.5GB VRAM, sub-100ms latency. For high-throughput, low-complexity tasks.
- **Use cases**: Binary classification, simple routing, candidate pre-filtering

### Tier 6: Multimodal — Llama4-Scout-17B-16E (MoE)
- **Role**: Vision tasks, screenshot analysis, UI understanding (future)
- **Why**: Best open multimodal MoE. 17B active from 109B total. Strong vision + reasoning.
- **Use cases**: Competitor site screenshots, content review, SERP analysis

### Tier 7: Embedding — Nomic Embed Text v1.5
- **Role**: Text embedding for vector search and retrieval
- **Why**: Small (275MB), fast, competitive quality, runs on CPU.
- **Use cases**: pgvector similarity search, content deduplication, recommendation retrieval

### Fallback: Claude Sonnet 4 (Anthropic API)
- **Role**: Universal fallback when self-hosted models are unavailable
- **Why**: Preserves existing platform functionality during transition
- **Cost**: $3/$15 per million input/output tokens

## Model Selection Matrix

| Task Type | Primary | Fallback | Temperature | Max Tokens |
|-----------|---------|----------|-------------|------------|
| SEO Audit | qwen3-235b-a22b | claude-sonnet-4 | 0.3 | 8192 |
| Recommendations | qwen3-235b-a22b | claude-sonnet-4 | 0.3 | 4096 |
| Competitor Analysis | qwen3-235b-a22b | claude-sonnet-4 | 0.3 | 8192 |
| GEO/AEO Analysis | qwen3-235b-a22b | claude-sonnet-4 | 0.3 | 4096 |
| Content Strategy | qwen3-235b-a22b | claude-sonnet-4 | 0.4 | 8192 |
| Report Generation | qwen3-235b-a22b | claude-sonnet-4 | 0.2 | 16384 |
| Tool Calls | qwen3-30b-a3b | qwen3-8b | 0.1 | 4096 |
| Social Adaptation | qwen3-30b-a3b | claude-sonnet-4 | 0.5 | 2048 |
| Ad Copy | qwen3-30b-a3b | claude-sonnet-4 | 0.6 | 2048 |
| Schema Generation | qwen2.5-coder-32b | qwen3-30b-a3b | 0.1 | 4096 |
| Task Routing | qwen3-8b | qwen3-1.7b | 0.0 | 256 |
| Guardrail Check | qwen3-8b | qwen3-1.7b | 0.0 | 512 |
| Classification | qwen3-1.7b | qwen3-8b | 0.0 | 128 |
| Embedding | nomic-embed-text | — | — | — |

## VRAM Requirements

| Setup | Models | VRAM Needed |
|-------|--------|-------------|
| Minimal Local Dev | qwen3-8b + nomic-embed | ~6 GB |
| Standard Local Dev | qwen3-30b-a3b + qwen3-8b + nomic | ~14 GB |
| Full Local Dev | All local models | ~50 GB |
| Production (1 GPU) | qwen3-30b-a3b + qwen3-8b | ~14 GB |
| Production (4 GPU) | qwen3-235b-a22b + qwen3-30b-a3b + qwen3-8b | ~60 GB |

## Upgrade Path

The model lineup should be re-evaluated quarterly. Watch for:
- Qwen3 larger variants or improved MoE configurations
- DeepSeek-R1 v2 or R2 releases
- Llama 4 Behemoth open-weight release
- Mistral Large v3 open-weight
- New efficient MoE architectures

Model upgrades are zero-downtime: register new model → shadow mode → evaluate → promote → retire old model.
