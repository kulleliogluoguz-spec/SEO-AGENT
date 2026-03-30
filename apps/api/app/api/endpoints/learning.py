"""
Learning Loop endpoints.

GET  /api/v1/learning/summary             — learning dashboard summary
GET  /api/v1/learning/strategies          — strategy history
POST /api/v1/learning/strategies          — record a new strategy recommendation
POST /api/v1/learning/strategies/{id}/outcome — record measured outcome
GET  /api/v1/learning/hypotheses          — hypothesis history
POST /api/v1/learning/hypotheses          — propose a new hypothesis
POST /api/v1/learning/hypotheses/{id}/result — record test result
GET  /api/v1/learning/suppressed          — suppressed (failing) strategy patterns
GET  /api/v1/learning/promoted            — promoted (winning) strategy patterns
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.api.dependencies.auth import get_current_user
from app.core.store.learning_store import (
    get_learning_summary,
    record_strategy,
    update_strategy_outcome,
    get_strategy_records,
    record_hypothesis,
    update_hypothesis_result,
    get_hypotheses,
    get_suppressed_strategies,
    get_promoted_strategies,
)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class StrategyRecordCreate(BaseModel):
    strategy_type: str = Field(..., description="channel_recommendation | content_brief | media_plan | audience_hypothesis")
    strategy_title: str
    niche: str
    channel: Optional[str] = None
    recommendation_data: dict = Field(default_factory=dict)
    source: str = "niche_engine"


class StrategyOutcomeUpdate(BaseModel):
    outcome: str = Field(..., description="success | failure | partial")
    outcome_data: dict = Field(default_factory=dict, description="Actual metrics: impressions, clicks, roas, cac, etc.")
    confidence_after: Optional[float] = Field(None, ge=0.0, le=1.0)


class HypothesisCreate(BaseModel):
    hypothesis: str
    rationale: str
    channel: Optional[str] = None
    niche: str
    test_type: str = Field(default="ab_test", description="ab_test | before_after | holdout | multivariate")
    metric_to_track: str = Field(default="ctr", description="ctr | cpa | roas | engagement_rate | follower_growth")
    expected_lift_pct: float = Field(default=10.0, description="Expected percentage improvement")
    test_duration_days: int = Field(default=14, ge=1, le=90)


class HypothesisResultUpdate(BaseModel):
    result: str = Field(..., description="confirmed | rejected | inconclusive")
    actual_lift_pct: float
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    result_data: dict = Field(default_factory=dict)
    notes: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary")
async def learning_summary(
    niche: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
) -> dict:
    """
    Return the learning loop dashboard summary for the current user.
    Shows: strategies recorded, measured, success/failure rate,
    suppressed patterns, promoted patterns, recent outcomes.
    """
    summary = get_learning_summary(str(current_user.id), niche=niche)
    return {
        "summary": summary,
        "status": "active" if summary["total_strategies_recorded"] > 0 else "no_data",
        "message": (
            "Learning loop is active — tracking strategy outcomes and adapting recommendations."
            if summary["total_strategies_recorded"] > 0
            else "No strategies recorded yet. Start by approving recommendations from the dashboard."
        ),
    }


@router.get("/strategies")
async def list_strategies(
    niche: Optional[str] = Query(None),
    strategy_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict:
    """List recorded strategy recommendations with their outcomes."""
    records = get_strategy_records(
        str(current_user.id),
        niche=niche,
        strategy_type=strategy_type,
        outcome=outcome,
        limit=limit,
    )
    return {"items": records, "total": len(records)}


@router.post("/strategies", status_code=201)
async def create_strategy_record(
    payload: StrategyRecordCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Record that a strategy recommendation was generated and surfaced to the user.
    Call this when the system recommends something, not just when it's approved.
    """
    record = record_strategy(
        user_id=str(current_user.id),
        strategy_type=payload.strategy_type,
        strategy_title=payload.strategy_title,
        niche=payload.niche,
        channel=payload.channel,
        recommendation_data=payload.recommendation_data,
        source=payload.source,
    )
    return {"record": record, "message": "Strategy recommendation recorded for outcome tracking."}


@router.post("/strategies/{record_id}/outcome")
async def record_outcome(
    record_id: str,
    payload: StrategyOutcomeUpdate,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Record the measured outcome for a strategy.
    This drives the learning loop — suppressing failures and promoting successes.
    """
    record = update_strategy_outcome(
        record_id=record_id,
        outcome=payload.outcome,
        outcome_data=payload.outcome_data,
        confidence_after=payload.confidence_after,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Strategy record not found.")
    return {
        "record": record,
        "message": f"Outcome recorded as '{payload.outcome}'. System will update pattern weights accordingly.",
    }


@router.get("/hypotheses")
async def list_hypotheses(
    niche: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict:
    """List proposed and completed hypothesis tests."""
    hypotheses = get_hypotheses(
        str(current_user.id),
        niche=niche,
        result=result,
        limit=limit,
    )
    return {"items": hypotheses, "total": len(hypotheses)}


@router.post("/hypotheses", status_code=201)
async def create_hypothesis(
    payload: HypothesisCreate,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Propose a new testable hypothesis.
    Hypotheses are the core of the experimentation layer.
    """
    hyp = record_hypothesis(
        user_id=str(current_user.id),
        hypothesis=payload.hypothesis,
        rationale=payload.rationale,
        channel=payload.channel,
        niche=payload.niche,
        test_type=payload.test_type,
        metric_to_track=payload.metric_to_track,
        expected_lift_pct=payload.expected_lift_pct,
        test_duration_days=payload.test_duration_days,
    )
    return {"hypothesis": hyp, "message": "Hypothesis recorded. Run the test and record results via POST /hypotheses/{id}/result."}


@router.post("/hypotheses/{hypothesis_id}/result")
async def record_hypothesis_result(
    hypothesis_id: str,
    payload: HypothesisResultUpdate,
    current_user=Depends(get_current_user),
) -> dict:
    """Record the result of a completed hypothesis test."""
    hyp = update_hypothesis_result(
        hypothesis_id=hypothesis_id,
        result=payload.result,
        actual_lift_pct=payload.actual_lift_pct,
        confidence_level=payload.confidence_level,
        result_data=payload.result_data,
        notes=payload.notes,
    )
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found.")
    return {
        "hypothesis": hyp,
        "message": f"Result recorded as '{payload.result}'. "
                   + ("Pattern promoted for future recommendations." if payload.result == "confirmed" else
                      "Pattern suppressed to avoid repeating this approach." if payload.result == "rejected" else
                      "Inconclusive — more data needed before making a pattern decision."),
    }


@router.get("/suppressed")
async def suppressed_patterns(
    niche: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
) -> dict:
    """
    List suppressed strategy patterns — approaches that have failed repeatedly
    and should not be recommended again without new evidence.
    """
    patterns = get_suppressed_strategies(niche=niche)
    return {
        "patterns": patterns,
        "total": len(patterns),
        "note": "These patterns will be deprioritized in future recommendations.",
    }


@router.get("/promoted")
async def promoted_patterns(
    niche: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
) -> dict:
    """
    List promoted strategy patterns — approaches with consistent success
    that should be recommended more aggressively.
    """
    patterns = get_promoted_strategies(niche=niche)
    return {
        "patterns": patterns,
        "total": len(patterns),
        "note": "These patterns will be weighted higher in future recommendations.",
    }
