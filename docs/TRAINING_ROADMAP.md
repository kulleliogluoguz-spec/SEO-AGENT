# Training Roadmap — Domain Specialization Strategy

## Staged Approach

Do not over-train. Start with prompting, evolve only when data and evidence justify it.

```
Stage 1: Prompt + Routing + Tools          ← YOU ARE HERE
Stage 2: Retrieval + Few-Shot Examples
Stage 3: LoRA Adapters
Stage 4: Supervised Fine-Tuning (SFT)
Stage 5: Direct Preference Optimization (DPO)
Stage 6: GRPO / RL (if justified)
```

## Stage 1: Prompt Engineering (Current)

**What to do now:**
- Use the Prompt Registry with domain-specialized system prompts
- Route tasks to the best model via the AI Router
- Use structured output contracts (JSON schemas) for reliability
- Inject few-shot examples into prompts from curated exemplars
- Let the guardrail engine catch quality issues

**What should stay prompt-only forever:**
- General reasoning and synthesis
- Ad-hoc analysis requests
- Report formatting and summarization
- Simple classification and routing

## Stage 2: Retrieval-Augmented Generation

**When**: After 50+ curated exemplars per category

**What to add:**
- Embed high-quality recommendation-evidence pairs into pgvector
- At inference time, retrieve similar examples and inject as few-shot context
- Embed approved content pieces for style matching
- Embed competitor analyses for consistent framing

**How to implement:**
```python
# Already supported by PromptTemplate.examples
# Add retrieval step before engine.execute()
similar = await vector_store.search(query, top_k=3)
prompt.examples = [PromptExample(input=s.input, output=s.output) for s in similar]
```

## Stage 3: LoRA Adapters

**When**: After 500+ quality examples in a specific domain

**What to adapt:**
- SEO audit output style and structure
- Recommendation generation format and evidence quality
- Content strategy brief format
- Social content adaptation per channel

**How:**
```bash
# Using PEFT / Unsloth / Axolotl
python train_lora.py \
  --base_model Qwen/Qwen3-30B-A3B \
  --dataset exports/sft_seo_audit.jsonl \
  --rank 16 \
  --alpha 32 \
  --target_modules q_proj,v_proj \
  --output adapters/seo_audit_v1/
```

**Loading in vLLM:**
```bash
vllm serve Qwen/Qwen3-30B-A3B \
  --enable-lora \
  --lora-modules seo_audit=adapters/seo_audit_v1/
```

## Stage 4: Supervised Fine-Tuning (SFT)

**When**: After 2000+ gold-quality examples

**What to fine-tune:**
- Domain language and terminology
- Output format consistency
- Evidence citation patterns
- Recommendation quality and actionability

**Data sources:**
- Accepted recommendations (with user approval signal)
- Human-edited content (the edited version is the gold standard)
- High-quality reports that got positive feedback
- Expert-reviewed SEO analyses

## Stage 5: Direct Preference Optimization (DPO)

**When**: After 1000+ preference pairs (accepted vs rejected)

**What it improves:**
- Recommendation ranking quality
- Content tone alignment with brand voice
- Actionability vs vagueness
- Evidence quality vs hallucination

**Data collection (already instrumented):**
```python
# When user accepts one recommendation over another:
dataset_manager.record_preference(
    instruction="Generate SEO recommendations for example.com",
    chosen=accepted_recommendation,
    rejected=rejected_recommendation,
    category="recommendation",
)
```

## Stage 6: GRPO / RL (Future)

**When**: Only if stages 1-5 are insufficient for a specific task

**Possible targets:**
- Recommendation impact prediction (reward = actual traffic change)
- Content quality scoring (reward = engagement metrics)
- Ad copy effectiveness (reward = CTR / conversion data)

## Data Collection Plan

The platform automatically collects training signals:

| Signal | Collection Point | Training Use |
|--------|-----------------|--------------|
| Recommendation approval | Approval queue | SFT + DPO |
| Recommendation rejection | Approval queue | DPO (rejected) |
| Content edits | Content editor | SFT (edited = gold) |
| Content approval | Approval queue | SFT quality filter |
| User thumbs up/down | UI feedback | DPO preference |
| Campaign outcomes | Analytics connectors | Future RL reward |
| Prompt/citation match | GEO tracking | GEO specialization |

### Dataset Schemas (Pre-built)

All schemas are defined in `app/ai/training/training_manager.py`:

- **SFTExample**: instruction + context + output + quality label
- **PreferenceExample**: instruction + chosen + rejected + reason
- **RecommendationTrainingExample**: site context + analysis + recommendation + outcome + impact
- **ContentTrainingExample**: brief + generated + edited + approval + quality score

### Export for Training

```python
from app.ai.training import get_dataset_manager

dm = get_dataset_manager()

# Export SFT dataset
dm.export_to_jsonl(DatasetType.SFT, "exports/sft_all.jsonl")

# Export only gold-quality SEO examples
dm.export_to_jsonl(DatasetType.SFT, "exports/sft_seo_gold.jsonl",
                   min_quality=DataQuality.GOLD, category="seo_audit")

# Export preference pairs for DPO
dm.export_to_jsonl(DatasetType.PREFERENCE, "exports/dpo_recommendations.jsonl",
                   category="recommendation")
```

## Tools for Training

| Tool | Purpose | Stage |
|------|---------|-------|
| PEFT (HuggingFace) | LoRA adapter training | 3 |
| Unsloth | Fast LoRA training (2x speed) | 3 |
| TRL | SFT + DPO + GRPO pipelines | 4-6 |
| Axolotl | Flexible fine-tuning configs | 3-4 |
| Weights & Biases | Experiment tracking | All |
| vLLM LoRA serving | Production adapter loading | 3+ |
