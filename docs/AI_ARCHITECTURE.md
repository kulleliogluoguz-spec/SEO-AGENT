# AI Architecture — AI CMO OS Custom AI Subsystem

## Overview

AI CMO OS runs a **custom, multi-model, open-source-first AI subsystem** that serves as the intelligence layer behind all platform operations: SEO analysis, AI visibility reasoning, recommendation generation, content strategy, competitor intelligence, marketing planning, and safe execution workflows.

This is **not** a simple API wrapper. It is a layered, routed, observable, domain-specialized AI system designed for production evolution.

## Design Principles

1. **Open-source first** — Prefer self-hosted open-weight models (Qwen3, Llama4, DeepSeek)
2. **Multi-model** — Different models for different tasks (reasoning vs tools vs routing)
3. **Self-hostable** — Runs entirely on your infrastructure via Ollama (dev) or vLLM (prod)
4. **Provider-agnostic** — Anthropic API available as fallback, not a dependency
5. **Domain-specialized** — Prompts, evaluation, and future fine-tuning for SEO/growth
6. **Safe by default** — Guardrails, approval gates, autonomy levels
7. **Observable** — Full tracing, cost tracking, quality metrics
8. **Evolvable** — Staged path from prompting to LoRA to SFT to DPO

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Admin UI (Next.js)                         │
│  Models · Providers · Routing · Prompts · Evals · Traces · Cost │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   AI Admin API (/api/v1/ai/)                    │
│  /models · /providers · /router · /prompts · /evals · /traces   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Integration Bridge                            │
│        AIClient · LangGraphLLMAdapter · Feedback hooks           │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│ │  Guardrails  │ │   Context    │ │  Training   │ │   Tracer   │ │
│ │ Input/Output │ │   Manager    │ │  Data Coll. │ │  Metrics   │ │
│ └─────────────┘ └──────────────┘ └────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     Engine Manager (15 Engines)                  │
│  Reasoning · ToolUse · ContentStrategy · Recommendation ·       │
│  Evidence · Competitor · Visibility · Marketing · Social ·      │
│  AdCopy · Report · Guardrail · Routing · Eval · StructuredOut   │
├─────────────────────────────────────────────────────────────────┤
│               ┌──────────────────────────┐                      │
│               │     Prompt Registry      │                      │
│               │  Versioned · Templated   │                      │
│               │  Few-shot · Contracted   │                      │
│               └──────────────────────────┘                      │
├─────────────────────────────────────────────────────────────────┤
│                      AI Router / Gateway                        │
│   Role routing · Capability routing · Cost-aware · Fallback     │
│   Shadow mode · Latency-aware · Profile-aware (local/prod)      │
├─────────────────────────────────────────────────────────────────┤
│                      Model Registry                             │
│  8 models · 18 roles · 11 capabilities · 3 deployment profiles  │
├──────────┬──────────────────┬──────────────────┬────────────────┤
│  Ollama  │      vLLM        │    Anthropic     │  (LiteLLM)     │
│  (Local) │   (Production)   │   (Fallback)     │  (Future)      │
└──────────┴──────────────────┴──────────────────┴────────────────┘
     │              │                    │
  Qwen3-8B    Qwen3-235B-A22B    Claude Sonnet 4
  Qwen3-30B   Qwen2.5-Coder      Claude Haiku
  Llama4      Nomic Embed
```

## Model Strategy

| Role | Primary Model | Fallback | Why |
|------|--------------|----------|-----|
| Core Reasoning | Qwen3-235B-A22B (MoE) | Claude Sonnet 4 | Best open reasoning, 22B active params |
| Tool Execution | Qwen3-30B-A3B | Qwen3-8B | Fast MoE, excellent structured output |
| Coding/Systems | Qwen2.5-Coder-32B | Qwen3-30B | Top code model, schema generation |
| Routing/Guard | Qwen3-8B | Qwen3-1.7B | Fast classification, low VRAM |
| Classification | Qwen3-1.7B | Qwen3-8B | Minimal resources, high throughput |
| Multimodal | Llama4-Scout-17B | Claude Sonnet 4 | Vision + reasoning for future use |
| Embedding | Nomic Embed v1.5 | — | Efficient, local, good quality |

## Component Reference

### Model Registry (`app/ai/registry/`)
Central catalog of all models with capabilities, costs, latencies, deployment profiles, and role assignments. Each model is a `ModelCard` with full metadata.

### Provider Layer (`app/ai/providers/`)
Unified interface for model serving backends:
- **OllamaProvider** — Local development, OpenAI-compatible API
- **VLLMProvider** — Production GPU serving with guided decoding
- **AnthropicProvider** — API fallback preserving existing setup

### AI Router (`app/ai/router/`)
Central routing brain that selects the optimal model based on:
- Task type (AI role)
- Required capabilities (tool use, JSON mode, etc.)
- Cost constraints (prefers free self-hosted)
- Latency requirements
- Deployment profile (local vs production)
- Fallback chains with automatic failover
- Shadow mode for A/B evaluation

### Engine Manager (`app/ai/engines/`)
15 logical AI engines that separate "what to do" from "which model does it":

1. **ReasoningEngine** — Deep analysis, synthesis, strategy
2. **StructuredOutputEngine** — JSON/schema-compliant generation
3. **ToolUseEngine** — Function calling, API interactions
4. **ContentStrategyEngine** — Content planning, briefs, editorial
5. **RecommendationEngine** — Prioritized, evidence-backed recommendations
6. **EvidenceSynthesisEngine** — Data-to-insight reasoning
7. **CompetitorReasoningEngine** — Competitive intelligence
8. **VisibilityReasoningEngine** — GEO/AEO analysis
9. **MarketingPlanningEngine** — Campaign strategy, channel planning
10. **SocialAdaptationEngine** — Cross-platform content adaptation
11. **AdCopyEngine** — Ad copy variants per platform
12. **ReportSynthesisEngine** — Executive report generation
13. **GuardrailEngine** — AI-powered content safety checks
14. **RoutingEngine** — Task classification for smart routing
15. **EvalEngine** — Quality assessment

### Prompt Registry (`app/ai/prompts/`)
Versioned prompt templates with variable interpolation, few-shot examples, output contracts (JSON schemas), and evaluation linkage. 12+ domain-specialized prompts pre-loaded.

### Tool Registry (`app/ai/tools/`)
Structured tool definitions in OpenAI function-calling format with permission boundaries, retry logic, timeout handling, and approval integration.

### Context Manager (`app/ai/memory/`)
Assembles context from workspace, site, brand, competitor, recommendation, and conversation state for injection into AI calls.

### Guardrails (`app/ai/guardrails/`)
Three-layer safety: input sanitization (injection detection, PII), output validation (spam, deception), and action safety (high-risk blocking by autonomy level).

### Observability (`app/ai/observability/`)
Full tracing with per-model, per-provider, per-engine metrics. Cost tracking, latency histograms, error rates, fallback counts, and validation failure rates.

### Evaluation (`app/ai/evaluation/`)
Eval harness with named test suites, automated quality scoring, regression detection across prompt versions, and model comparison.

### Training (`app/ai/training/`)
Dataset scaffolding for SFT, DPO, recommendation-evidence, and content quality training. Data collection hooks, export utilities, and LoRA adapter management stubs.

## Data Flow: AI-Powered SEO Audit

```
Agent requests SEO audit
    → AIClient.complete(engine="reasoning", message="...", site_id=X)
        → InputGuardrail.check() — sanitize input
        → ContextManager.get_context() — load site/workspace context
        → Engine selects prompt: "seo.technical_audit" v1.0.0
        → Engine renders prompt with context variables
        → AIRouter.route(role="core_reasoning")
            → Selects: qwen3-235b-a22b (production) or qwen3-8b (local)
            → Fallback: claude-sonnet-4
        → ProviderManager.complete() — Ollama/vLLM/Anthropic
        → OutputGuardrail.check() — validate response
        → AITracer.record() — log trace with metrics
        → DatasetManager.record_sft_example() — collect training data
    → Returns EngineResult with structured JSON
```

## Integration with Existing Platform

The AI subsystem integrates via:

1. **AIClient** (`app/ai/integration.py`) — High-level client replacing direct Anthropic calls
2. **LangGraphLLMAdapter** — Drop-in replacement for ChatAnthropic in LangGraph graphs
3. **AI Admin API** (`/api/v1/ai/`) — REST endpoints for management
4. **FastAPI startup** — Provider initialization on app start

### Migration path for existing agents:
```python
# Before:
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514")

# After:
from app.ai.integration import get_ai_client
ai = get_ai_client()
result = await ai.complete(message="...", engine="reasoning")
```
