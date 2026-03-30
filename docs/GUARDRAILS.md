# Guardrails & Safety — AI CMO OS

## Three-Layer Safety

### Layer 1: Input Guardrails
- **Prompt injection detection** — Regex patterns catch "ignore instructions", "you are now", jailbreak attempts
- **PII stripping** — Optional redaction of emails, phone numbers, SSNs, credit cards
- **Length limits** — Blocks inputs over 100K characters

### Layer 2: Output Guardrails
- **Deceptive content detection** — Flags "guaranteed results", urgency manipulation, false scarcity
- **Spam blocking** — Blocks "click here", get-rich-quick, pharmaceutical spam patterns
- **JSON validation** — Validates structured outputs against expected schemas
- **Length checks** — Flags suspiciously short or excessively long outputs

### Layer 3: Action Safety
- **Autonomy-level enforcement** — High-risk actions (publish, send, modify) blocked at low autonomy levels
- **Approval gating** — Tools marked `requires_approval` queue for human review
- **Read-only mode** — Autonomy level 0 blocks all write actions

## Autonomy Levels

| Level | Allowed Actions |
|-------|----------------|
| 0 | Read-only analysis, no AI generation |
| 1 (default) | Draft generation, all outputs go to review |
| 2 | Approval-required, queued actions need explicit approval |
| 3 | Low-risk auto, minor non-content actions can execute |
| 4 | Advanced auto — **disabled by default, requires policy review** |

## Configuration

```bash
AI_GUARDRAILS_ENABLED=true
AI_GUARDRAILS_STRIP_PII=false
AI_GUARDRAILS_BLOCK_SPAM=true
AUTONOMY_DEFAULT_LEVEL=1
AUTONOMY_MAX_ALLOWED_LEVEL=3
```

## API

```bash
# Check input safety
POST /api/v1/ai/guardrails/check-input
{"text": "Your input here"}

# Check output safety
POST /api/v1/ai/guardrails/check-output
{"content": "Generated content", "content_type": "blog_post"}

# Guardrail stats
GET /api/v1/ai/guardrails/stats
```
