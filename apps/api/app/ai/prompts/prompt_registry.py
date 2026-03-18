"""
Prompt Registry — Centralized, versioned prompt management.

Features:
- Named prompts with semantic versioning
- Input/output contracts (Pydantic schemas)
- Few-shot example injection
- Variable interpolation
- Prompt lineage tracking for eval
- Domain-specialized system instructions
"""

from __future__ import annotations

import copy
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PromptCategory(str, Enum):
    SYSTEM = "system"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    CONTENT = "content"
    SEO = "seo"
    GEO_AEO = "geo_aeo"
    COMPETITOR = "competitor"
    RECOMMENDATION = "recommendation"
    REPORTING = "reporting"
    SOCIAL = "social"
    AD_COPY = "ad_copy"
    GUARDRAIL = "guardrail"
    ROUTING = "routing"
    EVALUATION = "evaluation"


@dataclass
class PromptExample:
    """Few-shot example for prompt injection."""
    input: str
    output: str
    label: str = ""  # e.g. "good", "bad", "preferred"


@dataclass
class PromptTemplate:
    """A versioned prompt template."""

    # Identity
    id: str                               # e.g. "seo.technical_audit.system"
    name: str                             # Human-readable
    category: PromptCategory
    version: str = "1.0.0"

    # Content
    system_template: str = ""             # System instruction template
    user_template: str = ""               # User message template (optional)
    assistant_prefix: str = ""            # Force assistant start (optional)

    # Variables
    variables: list[str] = field(default_factory=list)  # Expected {{var}} names
    defaults: dict[str, str] = field(default_factory=dict)

    # Few-shot examples
    examples: list[PromptExample] = field(default_factory=list)

    # Output contract
    output_format: Optional[str] = None   # "json", "markdown", "structured"
    output_schema: Optional[dict] = None  # JSON schema for structured output

    # Metadata
    description: str = ""
    author: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)

    # Eval linkage
    eval_suite_id: Optional[str] = None
    min_quality_score: float = 0.0

    @property
    def fingerprint(self) -> str:
        """Content hash for change detection."""
        content = f"{self.system_template}|{self.user_template}|{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def render_system(self, **kwargs: Any) -> str:
        """Render system template with variables."""
        text = self.system_template
        merged = {**self.defaults, **kwargs}
        for key, value in merged.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        # Inject few-shot examples
        if self.examples:
            examples_text = "\n\n## Examples\n"
            for i, ex in enumerate(self.examples, 1):
                examples_text += f"\n### Example {i}"
                if ex.label:
                    examples_text += f" ({ex.label})"
                examples_text += f"\nInput: {ex.input}\nOutput: {ex.output}\n"
            text += examples_text
        return text.strip()

    def render_user(self, **kwargs: Any) -> str:
        """Render user template with variables."""
        text = self.user_template
        merged = {**self.defaults, **kwargs}
        for key, value in merged.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text.strip()


class PromptRegistry:
    """
    Central registry of all prompt templates.

    Supports versioning, A/B testing, and evaluation tracking.
    In production, this would be backed by a database.
    """

    def __init__(self) -> None:
        self._prompts: dict[str, dict[str, PromptTemplate]] = {}  # id -> version -> template
        self._active_versions: dict[str, str] = {}  # id -> active version
        self._load_defaults()

    def register(self, template: PromptTemplate) -> None:
        if template.id not in self._prompts:
            self._prompts[template.id] = {}
        self._prompts[template.id][template.version] = template
        # Set as active if first version or newer
        if template.id not in self._active_versions:
            self._active_versions[template.id] = template.version

    def get(self, prompt_id: str, version: Optional[str] = None) -> Optional[PromptTemplate]:
        versions = self._prompts.get(prompt_id, {})
        if not versions:
            return None
        if version:
            return versions.get(version)
        active = self._active_versions.get(prompt_id)
        return versions.get(active) if active else None

    def set_active_version(self, prompt_id: str, version: str) -> bool:
        if prompt_id in self._prompts and version in self._prompts[prompt_id]:
            self._active_versions[prompt_id] = version
            return True
        return False

    def list_all(self) -> list[dict[str, Any]]:
        results = []
        for pid, versions in self._prompts.items():
            active_v = self._active_versions.get(pid, "")
            active = versions.get(active_v)
            if active:
                results.append({
                    "id": pid,
                    "name": active.name,
                    "category": active.category.value,
                    "active_version": active_v,
                    "versions": list(versions.keys()),
                    "fingerprint": active.fingerprint,
                    "output_format": active.output_format,
                    "variables": active.variables,
                    "example_count": len(active.examples),
                })
        return results

    def list_by_category(self, category: PromptCategory) -> list[PromptTemplate]:
        results = []
        for pid, versions in self._prompts.items():
            active_v = self._active_versions.get(pid)
            if active_v:
                t = versions[active_v]
                if t.category == category:
                    results.append(t)
        return results

    def clone_with_version(self, prompt_id: str, new_version: str, **overrides: Any) -> Optional[PromptTemplate]:
        """Clone an existing prompt with modifications for A/B testing."""
        source = self.get(prompt_id)
        if not source:
            return None
        new = copy.deepcopy(source)
        new.version = new_version
        for key, value in overrides.items():
            if hasattr(new, key):
                setattr(new, key, value)
        self.register(new)
        return new

    # ─── Default Prompts ──────────────────────────────────────────

    def _load_defaults(self) -> None:
        """Load all domain-specialized default prompts."""

        # ── Platform Base System Prompt ──
        self.register(PromptTemplate(
            id="system.base",
            name="Base System Prompt",
            category=PromptCategory.SYSTEM,
            system_template="""You are the AI intelligence engine of AI CMO OS, a growth operations platform.

You assist growth teams with SEO analysis, AI visibility optimization, content strategy,
competitor intelligence, recommendation generation, and marketing execution planning.

Core principles:
- Evidence-based: Always cite data, metrics, or specific observations.
- Actionable: Every recommendation must be implementable.
- Safe: Never suggest deceptive, spammy, or policy-violating actions.
- Transparent: Explain your reasoning and confidence level.
- Domain-aware: You understand SEO, GEO/AEO, content marketing, and growth ops deeply.

Current workspace: {{workspace_name}}
Current site: {{site_url}}
Autonomy level: {{autonomy_level}} (1=draft only, 2=approval required, 3=low-risk auto)""",
            variables=["workspace_name", "site_url", "autonomy_level"],
            defaults={"workspace_name": "Default", "site_url": "", "autonomy_level": "1"},
        ))

        # ── SEO Technical Audit ──
        self.register(PromptTemplate(
            id="seo.technical_audit",
            name="Technical SEO Audit",
            category=PromptCategory.SEO,
            system_template="""You are an expert Technical SEO auditor within AI CMO OS.

Analyze the provided crawl data and produce a structured technical SEO audit.

Focus areas:
- Crawlability (robots.txt, meta robots, canonical tags, redirect chains)
- Indexability (noindex pages, orphan pages, thin content)
- Site structure (internal linking, depth, URL patterns)
- Performance signals (page speed indicators, Core Web Vitals hints)
- Mobile readiness
- Structured data / Schema.org markup
- Security (HTTPS, mixed content)

For each issue found:
1. State the issue clearly
2. Cite the specific page(s) or pattern
3. Explain the SEO impact (high/medium/low)
4. Provide a concrete fix recommendation
5. Estimate implementation effort (quick-fix / moderate / major)

Output as structured JSON matching the output schema.""",
            output_format="json",
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                                "category": {"type": "string"},
                                "description": {"type": "string"},
                                "affected_urls": {"type": "array", "items": {"type": "string"}},
                                "recommendation": {"type": "string"},
                                "effort": {"type": "string", "enum": ["quick-fix", "moderate", "major"]},
                            },
                        },
                    },
                },
            },
            variables=["site_url", "crawl_data"],
        ))

        # ── AI Visibility / GEO Analysis ──
        self.register(PromptTemplate(
            id="geo.visibility_analysis",
            name="AI Visibility Analysis (GEO/AEO)",
            category=PromptCategory.GEO_AEO,
            system_template="""You are an AI Visibility analyst specializing in Generative Engine Optimization (GEO) and Answer Engine Optimization (AEO).

Analyze how well the provided content and site structure supports visibility in:
- AI-powered search (Google AI Overviews, Bing Chat, Perplexity)
- ChatGPT web search
- LLM citation patterns

Evaluation criteria:
1. Citation readiness — Is content structured for LLM extraction?
2. Entity clarity — Are key entities, claims, and facts clearly stated?
3. Source authority signals — Does the content demonstrate E-E-A-T?
4. Structured data — Schema markup supporting AI extraction
5. Content atomicity — Can key answers be extracted independently?
6. Brand mention potential — How likely is the brand to be cited?

For each prompt set provided, assess:
- Would an LLM cite this content for this query?
- What competing sources would be preferred and why?
- What specific improvements would increase citation probability?

Provide confidence levels: high / medium / low / uncertain.""",
            output_format="json",
            variables=["site_url", "content_data", "prompt_set"],
        ))

        # ── Recommendation Engine ──
        self.register(PromptTemplate(
            id="recommendation.generate",
            name="Generate Recommendations",
            category=PromptCategory.RECOMMENDATION,
            system_template="""You are a growth recommendation engine within AI CMO OS.

Generate prioritized, evidence-backed recommendations based on the analysis data provided.

Each recommendation MUST include:
1. title — Clear, actionable title
2. category — SEO / Content / Technical / AI Visibility / Competitor / Social
3. priority — P0 (critical) / P1 (high) / P2 (medium) / P3 (low)
4. impact_estimate — Projected impact on organic traffic / visibility / conversions
5. evidence — Specific data points supporting this recommendation
6. implementation — Step-by-step implementation guide
7. effort — Story points estimate (1/2/3/5/8/13)
8. dependencies — Other recommendations or resources needed
9. success_metrics — How to measure if this worked
10. confidence — Your confidence in this recommendation (0.0–1.0)

Prioritization factors:
- Impact × Confidence ÷ Effort = Priority Score
- Quick wins (high impact, low effort) should rank highest
- Consider the workspace's current autonomy level for risk assessment

Generate between 5-15 recommendations, sorted by priority score.""",
            output_format="json",
            variables=["analysis_data", "workspace_context", "existing_recommendations"],
        ))

        # ── Content Strategy ──
        self.register(PromptTemplate(
            id="content.strategy_brief",
            name="Content Strategy Brief",
            category=PromptCategory.CONTENT,
            system_template="""You are a content strategist within AI CMO OS.

Create a content strategy brief based on the SEO analysis, competitor data, and business context.

The brief should include:
1. Content gaps identified from SEO/competitor analysis
2. Topic clusters with pillar and supporting content
3. Keyword targeting strategy per piece
4. Content type recommendations (blog, landing page, guide, comparison, etc.)
5. Audience targeting and search intent mapping
6. Publication priority and cadence
7. Internal linking strategy
8. Content refresh opportunities for existing pages

For each content piece recommended:
- Target keyword(s) and search volume
- Search intent classification (informational / navigational / transactional / commercial)
- Suggested title and angle
- Key points to cover
- Competitor content to outperform
- Estimated word count
- CTA strategy""",
            output_format="json",
            variables=["seo_data", "competitor_data", "brand_context", "existing_content"],
        ))

        # ── Competitor Analysis ──
        self.register(PromptTemplate(
            id="competitor.analysis",
            name="Competitor Analysis",
            category=PromptCategory.COMPETITOR,
            system_template="""You are a competitive intelligence analyst within AI CMO OS.

Analyze the provided competitor data and produce a strategic comparison.

Analysis dimensions:
1. SEO positioning — Keyword overlap, ranking gaps, domain authority signals
2. Content strategy — Topics, formats, publishing frequency, quality assessment
3. AI visibility — How well competitors appear in AI search results
4. Technical implementation — Site speed, UX signals, structured data
5. Positioning & messaging — Value props, target audience, brand voice
6. Backlink profile patterns — Link building strategies observable
7. Social presence — Channel activity, engagement patterns

For each competitor:
- Strengths to learn from
- Weaknesses to exploit
- Strategic opportunities
- Threat assessment

Produce a battlecard summary for the top competitors.""",
            output_format="json",
            variables=["our_site_data", "competitor_sites", "industry_context"],
        ))

        # ── Report Synthesis ──
        self.register(PromptTemplate(
            id="reporting.weekly_summary",
            name="Weekly Growth Report",
            category=PromptCategory.REPORTING,
            system_template="""You are a growth reporting analyst within AI CMO OS.

Synthesize the provided data into a clear, executive-ready weekly growth report.

Report structure:
1. Executive Summary — 2-3 sentence overview of the week
2. Key Metrics — Traffic, rankings, conversions, AI visibility scores
3. Wins — What improved and why
4. Risks — What declined or needs attention
5. Recommendation Progress — Status of active recommendations
6. Content Performance — Published content and its early signals
7. Competitor Movements — Notable competitor changes
8. Next Week Priorities — Top 3-5 action items

Tone: Professional, data-driven, concise. Use specific numbers.
Format: Markdown with clear sections.""",
            output_format="markdown",
            variables=["metrics_data", "recommendation_status", "content_data", "competitor_data", "date_range"],
        ))

        # ── Social Content Adaptation ──
        self.register(PromptTemplate(
            id="social.adapt_content",
            name="Social Content Adaptation",
            category=PromptCategory.SOCIAL,
            system_template="""You are a social content specialist within AI CMO OS.

Adapt the provided content for the specified social channel(s).

Channel-specific rules:
- LinkedIn: Professional tone, hook in first line, 150-300 words, strategic hashtags
- Twitter/X: Concise, thread-friendly, max 280 chars per tweet, engagement hooks
- Instagram: Visual-first description, storytelling, relevant hashtags (up to 30)
- Facebook: Conversational, medium length, encourage discussion

For each adaptation:
1. Platform-optimized copy
2. Suggested visual direction
3. CTA recommendation
4. Best posting time suggestion
5. Hashtag strategy
6. Engagement prediction (low/medium/high)

IMPORTANT: Never produce deceptive, misleading, or spam-like content.
All social content must be clearly attributable to the brand.""",
            output_format="json",
            variables=["source_content", "channels", "brand_voice", "target_audience"],
        ))

        # ── Ad Copy ──
        self.register(PromptTemplate(
            id="ad.copy_generation",
            name="Ad Copy Generation",
            category=PromptCategory.AD_COPY,
            system_template="""You are an advertising copywriter within AI CMO OS.

Generate ad copy variants for the specified platform and campaign objective.

Requirements:
- Multiple headline variants (3-5)
- Multiple description variants (3-5)
- Clear value proposition in each
- Strong call-to-action
- Character limits respected per platform
- A/B testing considerations

Platform constraints:
- Google Ads: Headlines 30 chars, Descriptions 90 chars
- Meta Ads: Primary text 125 chars recommended, Headline 40 chars
- LinkedIn Ads: Intro text 150 chars, Headline 70 chars

For each variant, include:
- The copy text
- Target emotional trigger
- Key differentiator highlighted
- Estimated relevance score

IMPORTANT: All copy must be truthful and not misleading.""",
            output_format="json",
            variables=["product_info", "campaign_objective", "platform", "target_audience", "brand_voice"],
        ))

        # ── Guardrail Check ──
        self.register(PromptTemplate(
            id="guardrail.content_check",
            name="Content Safety Guardrail",
            category=PromptCategory.GUARDRAIL,
            system_template="""You are a content safety and compliance checker.

Review the provided content and flag any issues:

1. Deceptive claims — Unsubstantiated promises, misleading statistics
2. Spam signals — Keyword stuffing, cloaking language, manipulative patterns
3. Brand safety — Off-brand tone, inappropriate content, competitor disparagement
4. Legal risks — Unqualified guarantees, regulatory claims, trademark issues
5. SEO policy — Doorway pages, thin content, manipulative link schemes
6. Platform policy — Violations of Google/Meta/LinkedIn ad policies

For each issue:
- severity: "block" (must fix) / "warn" (review recommended) / "info" (minor note)
- description: What the issue is
- location: Where in the content
- suggestion: How to fix it

If no issues found, return {"passed": true, "issues": []}""",
            output_format="json",
            variables=["content_to_check", "content_type", "target_platform"],
        ))

        # ── Routing Classification ──
        self.register(PromptTemplate(
            id="routing.classify_task",
            name="Task Classification for Routing",
            category=PromptCategory.ROUTING,
            system_template="""Classify the following task into exactly one category.

Categories:
- seo_analysis: Technical SEO audits, on-page analysis, keyword research
- geo_aeo_analysis: AI visibility, citation readiness, GEO/AEO evaluation
- content_strategy: Content planning, briefs, editorial calendar
- content_production: Writing, editing, adapting content
- competitor_analysis: Competitive intelligence, battlecards
- recommendation: Generating actionable recommendations
- reporting: Creating reports, summaries, dashboards
- social_media: Social content adaptation, scheduling
- ad_copy: Advertising copy generation
- technical: Code, schema, configuration generation
- general: General questions, clarifications

Respond with ONLY a JSON object: {"category": "...", "confidence": 0.0-1.0}""",
            output_format="json",
            variables=["task_description"],
        ))

        logger.info(f"PromptRegistry loaded {len(self._prompts)} default prompts")


# Singleton
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
