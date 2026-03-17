"""
ProductUnderstandingAgent — Layer 2

Synthesizes product intelligence from crawled site content.
Produces structured product profile including value props, ICP, personas, JTBD.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class ProductUnderstandingInput(BaseModel):
    site_id: uuid.UUID
    site_url: str
    page_contents: list[dict]  # [{url, title, content_text, word_count}]
    max_content_chars: int = 8000


class ValueProp(BaseModel):
    headline: str
    description: str
    evidence: str  # Where on the site this was found


class ICP(BaseModel):
    name: str
    description: str
    company_size: str | None
    role: str | None
    pain_points: list[str]
    buying_triggers: list[str]


class Persona(BaseModel):
    name: str
    title: str
    description: str
    goals: list[str]
    frustrations: list[str]


class ProductProfile(BaseModel):
    site_url: str
    product_name: str | None
    product_summary: str
    category: str
    subcategory: str | None
    pricing_model: str | None  # free | freemium | subscription | one_time | usage_based | enterprise
    pricing_signals: list[str]
    value_props: list[ValueProp]
    icps: list[ICP]
    personas: list[Persona]
    jobs_to_be_done: list[str]
    trust_signals: list[str]
    positioning_draft: str
    messaging_framework: dict
    confidence_notes: list[str]  # What we're uncertain about


class ProductUnderstandingAgent(LLMAgent[ProductUnderstandingInput, ProductProfile]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="ProductUnderstandingAgent",
        layer=2,
        description="Synthesizes product intelligence from crawled site content",
        max_retries=2,
        timeout_seconds=120,
    )

    async def _execute(
        self,
        input_data: ProductUnderstandingInput,
        context: AgentRunContext,
    ) -> ProductProfile:
        # Build content digest from crawled pages
        content_digest = self._build_content_digest(
            input_data.page_contents,
            input_data.max_content_chars,
        )

        if context.demo_mode or not self._llm:
            return self._demo_profile(input_data.site_url)

        system = """You are a senior product analyst and GTM strategist.
Analyze the provided website content and produce a structured product intelligence profile.

IMPORTANT RULES:
- Only make claims supported by the actual content
- Mark uncertain inferences in confidence_notes
- Do not fabricate customer quotes or statistics
- If something is unclear, say so rather than guessing

Respond with valid JSON matching the ProductProfile schema."""

        user = f"""Website: {input_data.site_url}

Crawled content from {len(input_data.page_contents)} pages:
{content_digest}

Produce a complete product intelligence profile including:
- product_name, product_summary, category, subcategory
- pricing_model, pricing_signals
- value_props (list with headline, description, evidence)
- icps (2-3 ideal customer profiles)
- personas (2-3 buyer personas)
- jobs_to_be_done (list of 5-8 JTBDs)
- trust_signals (logos, testimonials, certifications found)
- positioning_draft (one clear positioning statement)
- messaging_framework (problem/solution/value/cta structure)
- confidence_notes (what you're uncertain about)"""

        result, tokens = await self._call_llm_structured(system, user, ProductProfile)
        if result:
            return result

        # Fallback
        return self._demo_profile(input_data.site_url)

    def _build_content_digest(
        self, pages: list[dict], max_chars: int
    ) -> str:
        """Build a condensed content digest from crawled pages."""
        parts = []
        total_chars = 0

        # Prioritize home, pricing, features, about pages
        priority_keywords = ["pricing", "features", "about", "product", "solution"]

        def priority_score(page: dict) -> int:
            url = page.get("url", "").lower()
            return sum(1 for kw in priority_keywords if kw in url)

        sorted_pages = sorted(pages, key=priority_score, reverse=True)

        for page in sorted_pages:
            if total_chars >= max_chars:
                break
            url = page.get("url", "")
            title = page.get("title", "")
            content = page.get("content_text", "")[:2000]
            chunk = f"--- {url} ---\nTitle: {title}\n{content}\n\n"
            parts.append(chunk)
            total_chars += len(chunk)

        return "".join(parts)[:max_chars]

    def _demo_profile(self, site_url: str) -> ProductProfile:
        return ProductProfile(
            site_url=site_url,
            product_name="Demo Product",
            product_summary=(
                "This is a demo product profile generated without AI analysis. "
                "Configure ANTHROPIC_API_KEY for real product intelligence."
            ),
            category="B2B SaaS",
            subcategory="Project Management",
            pricing_model="subscription",
            pricing_signals=["Monthly and annual plans mentioned", "Free trial available"],
            value_props=[
                ValueProp(
                    headline="Ship software faster",
                    description="AI-powered sprint planning reduces planning time by 60%",
                    evidence="Homepage hero section",
                )
            ],
            icps=[
                ICP(
                    name="Engineering Leader",
                    description="VP Engineering or CTO at a 50-200 person software company",
                    company_size="50-200",
                    role="VP Engineering / CTO",
                    pain_points=["Sprint planning takes too long", "Hard to track cross-team dependencies"],
                    buying_triggers=["Team scaling past 10 engineers", "Current tool not cutting it"],
                )
            ],
            personas=[
                Persona(
                    name="Alex the Engineering Manager",
                    title="Engineering Manager",
                    description="Manages a team of 8-15 engineers, accountable for sprint delivery",
                    goals=["Hit sprint commitments", "Give team clarity on priorities"],
                    frustrations=["Too much time in planning meetings", "Status reporting is manual"],
                )
            ],
            jobs_to_be_done=[
                "Help me run sprint planning in under 30 minutes",
                "Give my team clear priorities every week",
                "Show stakeholders what engineering is shipping",
            ],
            trust_signals=["SOC 2 Type II", "5,000+ teams", "Customer logos"],
            positioning_draft="For engineering teams that need to ship faster, [Product] is the AI-powered project management tool that cuts sprint planning time in half.",
            messaging_framework={
                "problem": "Sprint planning is slow and repetitive",
                "solution": "AI automates the tedious parts of sprint planning",
                "value": "Ship 2x faster with half the planning overhead",
                "cta": "Start your free trial",
            },
            confidence_notes=[
                "DEMO: All values are illustrative. Run real analysis with ANTHROPIC_API_KEY set."
            ],
        )
