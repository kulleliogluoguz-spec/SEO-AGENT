# Routing Strategy — AI CMO OS

## How Routing Works

Every AI call goes through `AIRouter.execute()` which selects the optimal model in this priority order:

1. **Role overrides** — Admin-configured forced assignments (e.g., "always use claude-sonnet-4 for reports")
2. **Explicit model** — If the request specifies a model_id, use it directly
3. **Role-based routing** — Map the AI role to its best available model
4. **Capability-based routing** — Infer required capabilities from the request (tool_use → needs function_calling)
5. **Default reasoning** — Fall back to the core reasoning model
6. **Absolute fallback** — Anthropic API if everything else fails

## Scoring Function

When multiple models can serve a role, the router scores them:

| Factor | Weight | Logic |
|--------|--------|-------|
| Profile match | +100 | Model available in current deployment profile (local/prod) |
| Non-fallback | +50 | Prefer primary models over API fallbacks |
| Free (self-hosted) | +30 | Prefer zero-cost self-hosted models |
| Latency fit | +20 | Lower latency = higher score |
| Not shadow | +10 | Active models preferred over shadow/eval models |

## Shadow Mode

Enable shadow mode to run a candidate model in parallel without serving its output:
```
PUT /api/v1/ai/router/policy
{"enable_shadow": true}

POST /api/v1/ai/models/shadow
{"model_id": "qwen3-235b-a22b", "shadow": true}
```
Shadow results are recorded in traces for offline comparison.

## Cost Control

- `prefer_free: true` (default) — Router always prefers self-hosted models
- `max_cost_per_request: 0.10` — Block requests that would exceed budget
- Anthropic fallback only fires on self-hosted failure, not by default
- Cost tracking in `/api/v1/ai/metrics/cost`
