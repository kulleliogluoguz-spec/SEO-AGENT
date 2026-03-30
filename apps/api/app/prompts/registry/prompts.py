"""
Prompt Registry — centralized, versioned prompt management.

All prompts used by agents should be registered here.
This enables:
  - Version tracking
  - A/B testing
  - Regression evaluation
  - Audit trails
  - Documentation generation
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptVersion:
    version: str
    system: str
    user_template: str
    description: str = ""
    risk_notes: str = ""
    eval_notes: str = ""
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class PromptDefinition:
    name: str
    family: str
    description: str
    input_vars: list[str]
    output_schema: str
    versions: list[PromptVersion] = field(default_factory=list)

    @property
    def latest(self) -> PromptVersion | None:
        active = [v for v in self.versions if not v.deprecated]
        return active[-1] if active else None

    def render(self, version: str | None = None, **kwargs: Any) -> tuple[str, str]:
        """Render (system, user) prompt with provided variables."""
        v = next((pv for pv in self.versions if pv.version == version), self.latest)
        if not v:
            raise ValueError(f"No prompt version found for {self.name}")
        try:
            user = v.user_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing prompt variable: {e}")
        return v.system, user


# ─── Prompt Definitions ───────────────────────────────────────────────────────

PROMPT_REGISTRY: dict[str, PromptDefinition] = {}


def register(prompt: PromptDefinition) -> PromptDefinition:
    PROMPT_REGISTRY[prompt.name] = prompt
    return prompt


# ── Site Summarization ────────────────────────────────────────────────────────

register(PromptDefinition(
    name="site_summarization",
    family="onboarding",
    description="Summarize a website's product, audience, and value proposition",
    input_vars=["url", "page_titles", "content_sample"],
    output_schema="ProductSummary",
    versions=[
        PromptVersion(
            version="1.0",
            system=(
                "You are a senior product analyst. Analyze website content and produce "
                "a structured product summary. Be factual — only state what is evident "
                "from the content. Do not invent claims. Respond in JSON."
            ),
            user_template=(
                "Website: {url}\n\nPage titles found: {page_titles}\n\n"
                "Content sample:\n{content_sample}\n\n"
                "Produce: product_summary, category, value_props (list), icp_summary"
            ),
            risk_notes="May hallucinate product details if content is sparse. Validate output.",
            eval_notes="Check that value_props are grounded in content, not invented.",
            tags=["onboarding", "product", "layer1"],
        )
    ],
))

# ── ICP Inference ─────────────────────────────────────────────────────────────

register(PromptDefinition(
    name="icp_inference",
    family="product_understanding",
    description="Infer ideal customer profiles from product content",
    input_vars=["product_summary", "content_sample", "pricing_signals"],
    output_schema="ICPInferenceOutput",
    versions=[
        PromptVersion(
            version="1.0",
            system=(
                "You are a B2B go-to-market strategist. Infer ideal customer profiles "
                "from the provided product content. Base your analysis only on what is "
                "observable in the content. Respond in JSON."
            ),
            user_template=(
                "Product summary: {product_summary}\n\n"
                "Pricing signals: {pricing_signals}\n\n"
                "Content sample: {content_sample}\n\n"
                "Produce: icps (list of {{name, description, company_size, role, pain_points, "
                "buying_triggers, objections}})"
            ),
            risk_notes="ICPs are inferred — present as hypotheses, not facts.",
            tags=["product", "icp", "layer2"],
        )
    ],
))

# ── SEO Recommendation ────────────────────────────────────────────────────────

register(PromptDefinition(
    name="seo_recommendation",
    family="seo",
    description="Generate prioritized SEO recommendations from audit data",
    input_vars=["site_url", "issues_summary", "page_count", "health_score"],
    output_schema="SEORecommendationList",
    versions=[
        PromptVersion(
            version="1.0",
            system=(
                "You are a senior SEO strategist. Given audit findings, generate "
                "specific, actionable recommendations. Each recommendation must include "
                "a clear rationale, estimated impact, and effort level. "
                "Prioritize by ROI. Respond in JSON."
            ),
            user_template=(
                "Site: {site_url}\n"
                "Health score: {health_score}/100\n"
                "Pages audited: {page_count}\n\n"
                "Issues found:\n{issues_summary}\n\n"
                "Generate: recommendations list with title, category, rationale, "
                "proposed_action, impact_score (0-1), effort_score (0-1), urgency_score (0-1)"
            ),
            risk_notes="Ensure recommendations are based on actual findings, not generic advice.",
            tags=["seo", "recommendations", "layer4"],
        )
    ],
))

# ── Content Brief ─────────────────────────────────────────────────────────────

register(PromptDefinition(
    name="content_brief",
    family="content_strategy",
    description="Generate a detailed content brief",
    input_vars=["topic", "content_type", "target_keyword", "tone", "word_count", "product_context", "icp_context"],
    output_schema="ContentBriefOutput",
    versions=[
        PromptVersion(
            version="1.0",
            system=(
                "You are a senior content strategist. Generate a detailed content brief. "
                "COMPLIANCE: Never suggest fabricated statistics. Flag claims needing evidence. "
                "Do not suggest deceptive or manipulative language. Respond in JSON."
            ),
            user_template=(
                "Topic: {topic}\nType: {content_type}\nKeyword: {target_keyword}\n"
                "Tone: {tone}\nWord count: {word_count}\n"
                "Product context: {product_context}\nICP: {icp_context}\n\n"
                "Generate: title, objective, target_audience, primary_keyword, "
                "secondary_keywords, outline, tone_guidance, compliance_notes, "
                "research_prompts, cta_suggestions"
            ),
            risk_notes="Content briefs guide LLM writers — must not suggest misleading angles.",
            tags=["content", "brief", "layer7"],
        )
    ],
))

# ── Report Synthesis ──────────────────────────────────────────────────────────

register(PromptDefinition(
    name="report_synthesis",
    family="reporting",
    description="Synthesize growth report narrative",
    input_vars=["period", "kpi_summary", "top_opportunities", "top_risks", "completed"],
    output_schema="ReportNarrative",
    versions=[
        PromptVersion(
            version="1.0",
            system=(
                "You are a growth analyst producing a weekly report for a SaaS team. "
                "Write clearly, be specific about numbers, and prioritize what matters. "
                "Do not pad. Respond in JSON with: executive_summary, key_findings (list), "
                "recommended_focus (string)."
            ),
            user_template=(
                "Period: {period}\nKPIs: {kpi_summary}\n\n"
                "Top opportunities: {top_opportunities}\n"
                "Risks: {top_risks}\n"
                "Completed: {completed}"
            ),
            tags=["reporting", "synthesis", "layer11"],
        )
    ],
))


def get_prompt(name: str) -> PromptDefinition:
    """Look up a prompt by name. Raises KeyError if not found."""
    if name not in PROMPT_REGISTRY:
        raise KeyError(f"Prompt '{name}' not registered. Available: {list(PROMPT_REGISTRY.keys())}")
    return PROMPT_REGISTRY[name]


def list_prompts() -> list[str]:
    return list(PROMPT_REGISTRY.keys())
