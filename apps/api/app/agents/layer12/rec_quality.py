"""
RecommendationQualityAgent — Layer 12

Evaluates recommendations for quality along multiple dimensions:
- Evidence grounding (is it backed by crawl data?)
- Specificity (is the proposed action actionable?)
- Scoring accuracy (are scores reasonable?)
- Risk flags (are risk flags appropriate?)
- Completeness (are required fields populated?)

Used in evaluation harness and as a quality gate before surfacing recommendations.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class RecommendationQualityInput(BaseModel):
    recommendation_id: uuid.UUID
    title: str
    category: str
    summary: str
    rationale: str
    evidence: list[dict]
    proposed_action: str | None
    impact_score: float
    effort_score: float
    confidence_score: float
    risk_flags: list[str]


class QualityDimension(BaseModel):
    dimension: str
    score: float  # 0.0–1.0
    pass_: bool
    notes: str


class RecommendationQualityOutput(BaseModel):
    recommendation_id: uuid.UUID
    overall_score: float
    passed: bool
    dimensions: list[QualityDimension]
    issues: list[str]
    improvements: list[str]


class RecommendationQualityAgent(LLMAgent[RecommendationQualityInput, RecommendationQualityOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="RecommendationQualityAgent",
        layer=12,
        description="Evaluates recommendation quality across multiple dimensions",
        requires_llm=False,  # Rule-based checks are sufficient for most cases
        timeout_seconds=30,
    )

    async def _execute(
        self,
        input_data: RecommendationQualityInput,
        context: AgentRunContext,
    ) -> RecommendationQualityOutput:
        dimensions: list[QualityDimension] = []
        issues: list[str] = []
        improvements: list[str] = []

        # ── Dimension 1: Evidence Grounding ────────────────────────────────
        has_evidence = len(input_data.evidence) > 0
        evidence_score = 1.0 if has_evidence else 0.0
        if not has_evidence:
            issues.append("Recommendation lacks supporting evidence")
            improvements.append("Add crawl findings or data points as evidence")
        dimensions.append(QualityDimension(
            dimension="evidence_grounding",
            score=evidence_score,
            pass_=has_evidence,
            notes=f"{len(input_data.evidence)} evidence items",
        ))

        # ── Dimension 2: Actionability ─────────────────────────────────────
        has_action = bool(input_data.proposed_action and len(input_data.proposed_action) > 20)
        action_score = 1.0 if has_action else 0.3
        if not has_action:
            issues.append("Missing or vague proposed_action")
            improvements.append("Add a specific, executable proposed_action")
        dimensions.append(QualityDimension(
            dimension="actionability",
            score=action_score,
            pass_=has_action,
            notes="Proposed action evaluated for specificity",
        ))

        # ── Dimension 3: Rationale Quality ────────────────────────────────
        rationale_len = len(input_data.rationale.split())
        rationale_score = min(1.0, rationale_len / 30)
        if rationale_len < 15:
            issues.append("Rationale is too brief")
            improvements.append("Expand rationale to explain why this matters")
        dimensions.append(QualityDimension(
            dimension="rationale_quality",
            score=rationale_score,
            pass_=rationale_len >= 15,
            notes=f"{rationale_len} words in rationale",
        ))

        # ── Dimension 4: Score Consistency ────────────────────────────────
        # Impact and confidence should be consistent: high impact with very low confidence is suspicious
        score_consistent = not (
            input_data.impact_score > 0.85 and input_data.confidence_score < 0.3
        )
        consistency_score = 1.0 if score_consistent else 0.4
        if not score_consistent:
            issues.append("High impact score with low confidence — review scores")
            improvements.append("Reduce impact_score or increase confidence_score with more evidence")
        dimensions.append(QualityDimension(
            dimension="score_consistency",
            score=consistency_score,
            pass_=score_consistent,
            notes=f"impact={input_data.impact_score:.1f}, confidence={input_data.confidence_score:.1f}",
        ))

        # ── Dimension 5: Risk Awareness ────────────────────────────────────
        # High-risk recommendations should have risk flags
        high_impact = input_data.impact_score > 0.7
        has_risk_consideration = len(input_data.risk_flags) > 0 or not high_impact
        risk_score = 1.0 if has_risk_consideration else 0.7
        if high_impact and not input_data.risk_flags:
            improvements.append("Consider adding risk_flags for high-impact recommendations")
        dimensions.append(QualityDimension(
            dimension="risk_awareness",
            score=risk_score,
            pass_=True,  # Not a hard failure
            notes="Risk flags reviewed",
        ))

        # ── Overall Score ─────────────────────────────────────────────────
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        overall = sum(d.score * w for d, w in zip(dimensions, weights))
        passed = overall >= 0.6 and all(d.pass_ for d in dimensions if d.dimension != "risk_awareness")

        return RecommendationQualityOutput(
            recommendation_id=input_data.recommendation_id,
            overall_score=round(overall, 2),
            passed=passed,
            dimensions=dimensions,
            issues=issues,
            improvements=improvements,
        )
