# Evaluation Strategy — AI CMO OS

## Philosophy

Evaluation-first development: every prompt change, model swap, or adapter must pass quality checks before deployment.

## Eval Suites

Pre-built suites in `app/ai/evaluation/eval_harness.py`:

| Suite | Engine | Tests | What It Checks |
|-------|--------|-------|----------------|
| `eval_seo_technical` | reasoning | SEO audit quality | Structured output, required fields, issue detection |
| `eval_recommendations` | recommendation | Rec generation quality | Prioritization, evidence, actionability |
| `eval_guardrails` | guardrail | Safety checks | Spam detection, clean content pass-through |

## Running Evals

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/ai/evals/run \
  -H "Content-Type: application/json" \
  -d '{"suite_id": "eval_seo_technical"}'

# View results
curl http://localhost:8000/api/v1/ai/evals/runs?suite_id=eval_seo_technical
```

## Eval Metrics

Each test case scores on: **accuracy, relevance, completeness, structured_output, safety, latency**.

Pass threshold: all scores >= 0.5 and no critical errors.

## Regression Detection

Compare two eval runs to detect quality regressions:

```
GET /api/v1/ai/evals/compare?run_a={id}&run_b={id}
```

Returns pass_rate_delta, per-metric score deltas, and a `regression: true/false` flag.

## Adding Custom Evals

```python
from app.ai.evaluation.eval_harness import EvalSuite, EvalCase, get_eval_harness

harness = get_eval_harness()
harness.register_suite(EvalSuite(
    id="eval_custom",
    name="My Custom Eval",
    engine="content_strategy",
    cases=[
        EvalCase(
            id="cs_1",
            name="Generate content brief",
            input_text="Create a content strategy for a B2B SaaS company.",
            expected_contains=["topic cluster", "keyword", "content type"],
            expected_json_keys=["content_pieces", "priority"],
        ),
    ],
))
```
