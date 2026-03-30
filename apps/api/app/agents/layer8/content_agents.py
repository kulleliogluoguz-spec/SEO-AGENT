"""
Content production agents: ContentBriefAgent + LongFormWriterAgent

These agents produce content assets with compliance awareness.
All output goes to REVIEW status — never auto-published.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


# ─── Content Brief Agent ──────────────────────────────────────────────────────

class ContentBriefInput(BaseModel):
    site_id: uuid.UUID
    content_type: str
    topic: str
    target_keyword: str | None = None
    tone: str = "professional"
    word_count_target: int | None = None
    notes: str | None = None
    product_context: str | None = None
    icp_context: str | None = None


class ContentBriefOutput(BaseModel):
    title: str
    content_type: str
    objective: str
    target_audience: str
    primary_keyword: str | None
    secondary_keywords: list[str]
    outline: list[dict]  # [{heading, description, word_count}]
    tone_guidance: str
    word_count_target: int
    compliance_notes: list[str]
    research_prompts: list[str]
    cta_suggestions: list[str]


class ContentBriefAgent(LLMAgent[ContentBriefInput, ContentBriefOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="ContentBriefAgent",
        layer=7,
        description="Generates detailed content briefs with SEO and compliance guidance",
        max_retries=2,
        timeout_seconds=90,
    )

    async def _execute(
        self,
        input_data: ContentBriefInput,
        context: AgentRunContext,
    ) -> ContentBriefOutput:
        if context.demo_mode or not self._llm:
            return self._demo_brief(input_data)

        system = """You are a senior content strategist. Generate a detailed content brief.

COMPLIANCE RULES:
- Never suggest fabricated statistics or unverified claims
- Flag any claims that require evidence in compliance_notes
- Do not suggest deceptive or manipulative language

Respond with valid JSON matching the required schema."""

        user = f"""Create a content brief for:
Topic: {input_data.topic}
Content type: {input_data.content_type}
Target keyword: {input_data.target_keyword or 'infer from topic'}
Tone: {input_data.tone}
Word count target: {input_data.word_count_target or 'appropriate for type'}
Product context: {input_data.product_context or 'not provided'}
ICP context: {input_data.icp_context or 'not provided'}
Additional notes: {input_data.notes or 'none'}"""

        result, _ = await self._call_llm_structured(system, user, ContentBriefOutput)
        return result or self._demo_brief(input_data)

    def _demo_brief(self, input_data: ContentBriefInput) -> ContentBriefOutput:
        wc = input_data.word_count_target or (
            1800 if input_data.content_type == "blog" else 800
        )
        return ContentBriefOutput(
            title=f"[Demo] {input_data.topic}",
            content_type=input_data.content_type,
            objective=f"Drive awareness and conversions for {input_data.topic}",
            target_audience="B2B decision makers and practitioners",
            primary_keyword=input_data.target_keyword,
            secondary_keywords=["related term 1", "related term 2"],
            outline=[
                {"heading": "Introduction", "description": "Hook and problem statement", "word_count": 200},
                {"heading": "Main Section", "description": "Core content", "word_count": wc - 400},
                {"heading": "Conclusion & CTA", "description": "Summary and next step", "word_count": 200},
            ],
            tone_guidance=f"{input_data.tone}, clear, evidence-based",
            word_count_target=wc,
            compliance_notes=["Verify all statistics before publishing", "Do not make comparative claims without evidence"],
            research_prompts=["What are the top 3 challenges this audience faces?"],
            cta_suggestions=["Start free trial", "Book a demo", "Download the guide"],
        )


# ─── Long Form Writer Agent ───────────────────────────────────────────────────

class LongFormWriterInput(BaseModel):
    brief: ContentBriefOutput
    additional_context: str | None = None


class LongFormWriterOutput(BaseModel):
    title: str
    content_markdown: str
    word_count: int
    compliance_flags: list[str]
    risk_score: float  # 0.0 (safe) to 1.0 (risky)
    review_required: bool = True  # Always true by default


class LongFormWriterAgent(LLMAgent[LongFormWriterInput, LongFormWriterOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="LongFormWriterAgent",
        layer=8,
        description="Writes long-form content from a structured brief",
        max_retries=1,
        timeout_seconds=180,
        autonomy_min_level=1,
    )

    async def _execute(
        self,
        input_data: LongFormWriterInput,
        context: AgentRunContext,
    ) -> LongFormWriterOutput:
        brief = input_data.brief

        if context.demo_mode or not self._llm:
            return LongFormWriterOutput(
                title=brief.title,
                content_markdown=self._demo_content(brief),
                word_count=brief.word_count_target,
                compliance_flags=["DEMO: Content is placeholder. Review before use."],
                risk_score=0.0,
                review_required=True,
            )

        outline_text = "\n".join(
            f"## {s['heading']}\n{s.get('description', '')} (~{s.get('word_count', 200)} words)"
            for s in brief.outline
        )

        system = f"""You are a skilled content writer. Write high-quality, factual content.

CRITICAL COMPLIANCE RULES:
- Only make claims you can support with the provided context
- Never fabricate statistics, quotes, or customer stories
- Do not use deceptive language or dark patterns
- If you want to include a specific claim that needs verification, wrap it in [VERIFY: claim]
- Tone: {brief.tone_guidance}

Write in clean Markdown format."""

        user = f"""Write a {brief.content_type} on: {brief.title}

Target keyword: {brief.primary_keyword or 'none'}
Target word count: {brief.word_count_target}

OUTLINE TO FOLLOW:
{outline_text}

Additional context: {input_data.additional_context or 'none'}"""

        content, _ = await self._call_llm(system, user, max_tokens=4096)

        # Scan for compliance issues
        flags = self._scan_compliance(content)
        risk_score = min(1.0, len(flags) * 0.2)

        return LongFormWriterOutput(
            title=brief.title,
            content_markdown=content,
            word_count=len(content.split()),
            compliance_flags=flags,
            risk_score=risk_score,
            review_required=True,  # Always requires review
        )

    def _scan_compliance(self, content: str) -> list[str]:
        """Simple rule-based compliance scan."""
        flags = []
        verify_count = content.count("[VERIFY:")
        if verify_count:
            flags.append(f"{verify_count} claims marked for verification")

        suspicious_phrases = [
            "guaranteed", "100% proven", "risk-free", "number one",
            "best in the world", "scientifically proven",
        ]
        for phrase in suspicious_phrases:
            if phrase.lower() in content.lower():
                flags.append(f"Review claim: '{phrase}'")

        return flags

    def _demo_content(self, brief: ContentBriefOutput) -> str:
        return f"""# {brief.title}

> **DEMO CONTENT** — This is placeholder content generated in demo mode.
> Replace with AI-generated or human-written content before publishing.

## Introduction

This is where your introduction would appear. It would hook the reader,
establish the problem, and preview the value the article delivers.

## Main Content

Your primary content sections would appear here, covering:
{chr(10).join(f"- {s['heading']}" for s in brief.outline[1:-1])}

## Conclusion

A strong conclusion summarizes key takeaways and includes a clear CTA.

**CTA:** {brief.cta_suggestions[0] if brief.cta_suggestions else 'Learn more'}
"""
