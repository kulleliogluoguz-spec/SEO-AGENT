"""
Recommendation Scoring — transparent, explainable priority scoring.

Formula:
    priority = (impact * w_impact)
              + ((1 - effort) * w_effort)   # low effort = higher priority
              + (confidence * w_confidence)
              + (urgency * w_urgency)
              + (evidence_bonus * w_evidence)

All inputs and weights are logged for auditability.
"""
from dataclasses import dataclass


# Default weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    "impact": 0.35,
    "effort_inverse": 0.20,   # inverted: low effort → high score
    "confidence": 0.20,
    "urgency": 0.15,
    "evidence": 0.10,
}

CATEGORY_MULTIPLIERS = {
    "technical_seo": 1.0,
    "on_page_seo": 0.95,
    "content_gap": 0.90,
    "internal_linking": 0.85,
    "geo_aeo": 0.75,         # Discounted: experimental module
    "experimentation": 0.80,
}


@dataclass
class ScoringResult:
    priority_score: float
    breakdown: dict[str, float]
    explanation: str


def compute_priority(
    impact: float,
    effort: float,
    confidence: float,
    urgency: float,
    evidence_count: int,
    category: str = "technical_seo",
    weights: dict[str, float] | None = None,
) -> ScoringResult:
    """
    Compute a transparent priority score for a recommendation.

    All inputs are 0.0–1.0. evidence_count is a raw integer (capped at 5 for scoring).

    Returns a ScoringResult with the final score, per-dimension breakdown,
    and a human-readable explanation string.
    """
    w = weights or DEFAULT_WEIGHTS

    # Normalize evidence to 0–1 (cap at 5 items = 1.0)
    evidence_score = min(1.0, evidence_count / 5.0)

    components = {
        "impact": impact * w["impact"],
        "effort_inverse": (1.0 - effort) * w["effort_inverse"],
        "confidence": confidence * w["confidence"],
        "urgency": urgency * w["urgency"],
        "evidence": evidence_score * w["evidence"],
    }

    raw_score = sum(components.values())

    # Apply category multiplier
    multiplier = CATEGORY_MULTIPLIERS.get(category, 0.90)
    final_score = round(min(1.0, raw_score * multiplier), 3)

    # Build explanation
    dominant = max(components, key=lambda k: components[k])
    explanation = (
        f"Priority {final_score:.2f}: "
        f"driven by {dominant.replace('_', ' ')} (impact={impact:.1f}, "
        f"effort={effort:.1f}, confidence={confidence:.1f}, "
        f"evidence={evidence_count} items). "
        f"Category multiplier: {multiplier:.2f}."
    )

    return ScoringResult(
        priority_score=final_score,
        breakdown={**components, "category_multiplier": multiplier, "raw_score": raw_score},
        explanation=explanation,
    )


def score_recommendation(
    impact_score: float,
    effort_score: float,
    confidence_score: float,
    urgency_score: float,
    evidence: list,
    category: str,
) -> ScoringResult:
    """Convenience wrapper used by agents when creating recommendations."""
    return compute_priority(
        impact=impact_score,
        effort=effort_score,
        confidence=confidence_score,
        urgency=urgency_score,
        evidence_count=len(evidence),
        category=category,
    )
