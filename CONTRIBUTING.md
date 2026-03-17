# Contributing to AI CMO OS

## Development Setup

```bash
git clone https://github.com/yourorg/ai-cmo-os.git
cd ai-cmo-os
cp .env.example .env
make up && make migrate && make seed
pre-commit install
```

## Standards

- Python: ruff (lint + format), mypy (types), pytest
- TypeScript: ESLint, TypeScript strict
- All new endpoints need tests in `tests/integration/`
- All new agents need unit tests in `tests/unit/`
- All new agents must be registered in `app/agents/registry.py`

## Agent Development

1. Create file in `app/agents/layerN/my_agent.py`
2. Inherit from `LLMAgent[Input, Output]` or `BaseAgent[Input, Output]`
3. Define `metadata: ClassVar[AgentMetadata]`
4. Implement `async def _execute(input_data, context) -> Output`
5. Add demo mode fallback (for when `ANTHROPIC_API_KEY` is not set)
6. Register in `app/agents/registry.py`
7. Add unit tests

## Safety Rules

- Never bypass approval gates
- Never enable Level 4 autonomy by default
- All community/social channel content → `safe_to_auto_publish=False`
- All LLM outputs → compliance scan before storage
- All crawl requests → SSRF check first
