# AI Integration Guide

## For Existing Agents and Services

The AI subsystem provides `AIClient` as the single entry point for all AI operations. It replaces direct Anthropic API calls.

### Basic Usage

```python
from app.ai.integration import get_ai_client

ai = get_ai_client()

# Simple reasoning task
result = await ai.complete(
    message="Analyze this site's technical SEO based on the crawl data.",
    engine="reasoning",
    context={"crawl_data": crawl_json},
    workspace_id=workspace_id,
    site_id=site_id,
)

if result.success:
    audit = result.data  # Parsed JSON if structured output
    print(f"Model: {result.model_used}, Latency: {result.latency_ms}ms")
```

### Engine Selection

| Engine | Use For |
|--------|---------|
| `reasoning` | Deep analysis, strategy, synthesis |
| `structured_output` | JSON generation, schema-compliant output |
| `tool_use` | Function calling, API interactions |
| `content_strategy` | Content briefs, editorial planning |
| `recommendation` | Growth recommendations |
| `competitor_reasoning` | Competitive analysis |
| `visibility_reasoning` | GEO/AEO analysis |
| `social_adaptation` | Social content adaptation |
| `ad_copy` | Ad copy variants |
| `report_synthesis` | Report generation |
| `guardrail` | Content safety checks |
| `routing` | Task classification |

### Specialized Engine Methods

```python
from app.ai.engines import get_engine_manager

engines = get_engine_manager()

# Generate recommendations
result = await engines.recommendation.generate_recommendations(
    analysis_data={"traffic_decline": True, "missing_meta": 15},
    workspace_context={"industry": "SaaS"},
)

# Check content safety
result = await engines.guardrail.check_content(
    content="Our product guarantees #1 rankings...",
    content_type="blog_post",
)

# Classify a task for routing
result = await engines.routing.classify_task("Analyze competitor backlinks")
```

### LangGraph Integration

```python
from app.ai.integration import get_langgraph_llm

# Drop-in replacement for ChatAnthropic
llm = get_langgraph_llm(engine="reasoning")

# Use in LangGraph graphs
response = await llm.ainvoke([
    {"role": "system", "content": "You are an SEO analyst."},
    {"role": "user", "content": "Audit this site."},
])
```

### Recording Training Feedback

```python
ai = get_ai_client()

# When user accepts/edits AI output
ai.record_feedback(
    instruction="Generate SEO recommendations",
    accepted_output=user_approved_text,
    rejected_output=original_ai_text,  # optional
    category="recommendation",
)
```

### Raw API Access (Low-Level)

```python
from app.ai.providers.base import AIRequest

result = await ai.complete_raw(
    messages=[{"role": "user", "content": "Hello"}],
    system="You are a helpful assistant.",
    role="core_reasoning",
    temperature=0.3,
)
```

## FastAPI Router Registration

Add to your `app/main.py`:

```python
from app.api.endpoints.ai_admin import router as ai_router

app.include_router(ai_router, prefix="/api/v1")
```

## Startup Hook

Add to your FastAPI lifespan or startup event:

```python
from app.ai.providers.provider_manager import get_provider_manager

@app.on_event("startup")
async def startup():
    manager = await get_provider_manager()
    # Providers are now initialized
```
