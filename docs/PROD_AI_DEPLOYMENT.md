# Production AI Deployment Guide

## Architecture Overview

Production deployment uses **vLLM** for GPU model serving with the AI Router handling model selection and fallback.

```
                    ┌─────────────────────┐
                    │   Load Balancer      │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │   AI CMO OS API     │
                    │   (AI Router)        │
                    └──┬──────┬──────┬────┘
                       │      │      │
              ┌────────▼┐ ┌──▼────┐ ┌▼──────────┐
              │ vLLM #1  │ │vLLM #2│ │ Anthropic  │
              │ Reasoning│ │ Tools │ │ (Fallback) │
              │ 4×A100   │ │ 1×A100│ │            │
              └──────────┘ └───────┘ └────────────┘
```

## vLLM Deployment

### Single-GPU Setup (1× A100 80GB or equivalent)

```bash
# Serve the tool/structured model
docker run --gpus all \
  -p 8001:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-30B-A3B \
  --max-model-len 32768 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --gpu-memory-utilization 0.85
```

### Multi-GPU Setup (4× A100 for full reasoning model)

```bash
# Serve the core reasoning model
docker run --gpus '"device=0,1,2,3"' \
  -p 8001:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-235B-A22B-AWQ \
  --quantization awq \
  --tensor-parallel-size 4 \
  --max-model-len 32768 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --gpu-memory-utilization 0.90

# Serve the tool model on a separate GPU
docker run --gpus '"device=4"' \
  -p 8002:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-30B-A3B \
  --max-model-len 65536 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes

# Small router model (can run on CPU or cheap GPU)
docker run --gpus '"device=5"' \
  -p 8003:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-8B \
  --max-model-len 32768
```

### Environment Configuration

```bash
AI_MODE=production
VLLM_BASE_URL=http://vllm-reasoning:8000/v1
VLLM_API_KEY=your-secure-key

ANTHROPIC_API_KEY=sk-ant-...  # Fallback only
AI_ROUTER_PROFILE=production
AI_ROUTER_PREFER_FREE=true
AI_ROUTER_ENABLE_FALLBACK=true
AI_ROUTER_FALLBACK_TO_ANTHROPIC=true
```

## Cloud GPU Options

| Provider | GPU | Cost/hr | Good for |
|----------|-----|---------|----------|
| RunPod | A100 80GB | ~$1.50 | Full reasoning model |
| Lambda | H100 | ~$2.50 | Maximum throughput |
| Together.ai | Serverless | Per-token | No GPU management |
| AWS | p4d.24xlarge | ~$32 | Enterprise, 8×A100 |

## Scaling Considerations

- **Horizontal**: Run multiple vLLM instances behind a load balancer
- **Vertical**: Use tensor parallelism for larger models across GPUs
- **Cost optimization**: Route cheap tasks to small models, expensive tasks to large models
- **Burst handling**: Anthropic API as overflow during traffic spikes

## Health Monitoring

```bash
# Check vLLM health
curl http://vllm-host:8001/v1/models

# Check AI system status
curl http://api-host:8000/api/v1/ai/status

# Check provider health
curl http://api-host:8000/api/v1/ai/providers/health

# Monitor cost
curl http://api-host:8000/api/v1/ai/metrics/cost
```

## Model Updates (Zero-Downtime)

1. Register new model version in registry
2. Enable shadow mode — runs new model in parallel without serving
3. Run eval suites against shadow model
4. Compare results: `GET /api/v1/ai/evals/runs?suite_id=...`
5. If quality is equal or better: promote new model, retire old
6. If regression: disable shadow, investigate

## Security

- vLLM instances should not be publicly accessible
- Use API keys for vLLM authentication
- Anthropic API key stored as secret (not in config files)
- All AI calls go through the guardrail layer
- Tool executions respect autonomy levels
