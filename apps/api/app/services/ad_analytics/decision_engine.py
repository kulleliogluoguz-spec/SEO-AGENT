"""
Rule-Based + Statistical Decision Engine
Analyzes campaign performance signals and emits actionable recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CampaignSignal:
    campaign_id: str
    campaign_name: str
    platform: str
    roas_7d: float
    roas_30d: float
    roas_trend: float  # week-over-week change, +ve = improving
    cpa_7d: float | None
    cpa_target: float | None
    spend_7d: float
    spend_30d: float
    ctr_7d: float
    frequency: float
    impressions_7d: int
    budget_utilization: float  # actual_spend / budget
    days_active: int


@dataclass
class Recommendation:
    type: str
    priority: str  # critical, high, medium, low
    title: str
    description: str
    expected_impact: str
    action_data: dict
    confidence: float
    reasoning: str


class DecisionEngine:
    """
    Multi-level decision engine for ad optimization.

    Level 1: Hard rules (immediate action)
    Level 2: Statistical rules (pattern-based)
    Level 3: Trend signals (week-over-week analysis)
    """

    RULES = {
        "roas_critical_low": 0.8,
        "roas_poor": 1.5,
        "roas_good": 3.0,
        "roas_excellent": 5.0,
        "cpa_overrun_pct": 0.5,
        "ctr_warning_search": 0.02,
        "ctr_warning_display": 0.003,
        "frequency_fatigue": 7.0,
        "budget_waste_utilization": 0.5,
        "budget_cap_hit": 0.95,
        "roas_trend_decline": -0.15,
        "roas_trend_improve": 0.20,
        "minimum_spend_days": 7,
    }

    def analyze_campaign(self, signal: CampaignSignal) -> list[Recommendation]:
        """Run all rules against a campaign signal."""
        if signal.days_active < self.RULES["minimum_spend_days"]:
            return []

        recs: list[Recommendation] = []
        recs.extend(self._check_critical_roas(signal))
        recs.extend(self._check_cpa_overrun(signal))
        recs.extend(self._check_creative_fatigue(signal))
        recs.extend(self._check_budget_constraints(signal))
        recs.extend(self._check_scaling_opportunity(signal))
        recs.extend(self._check_roas_trend(signal))

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recs.sort(key=lambda r: priority_order.get(r.priority, 99))
        return recs

    # ── Level 1: Critical ROAS ───────────────────────────────────────────────

    def _check_critical_roas(self, s: CampaignSignal) -> list[Recommendation]:
        if s.roas_7d < self.RULES["roas_critical_low"]:
            return [
                Recommendation(
                    type="pause_campaign",
                    priority="critical",
                    title=f"STOP: {s.campaign_name} is losing money",
                    description=(
                        f"Campaign ROAS is {s.roas_7d:.2f}x over the last 7 days — "
                        f"spending ${s.spend_7d:.0f} and returning less than invested."
                    ),
                    expected_impact="Stop immediate budget loss",
                    action_data={"action": "pause", "campaign_id": s.campaign_id},
                    confidence=0.95,
                    reasoning=(
                        f"ROAS of {s.roas_7d:.2f} is below break-even. For every $1 "
                        f"spent only ${s.roas_7d:.2f} returned. Pause and review "
                        "targeting/creative."
                    ),
                )
            ]
        if s.roas_7d < self.RULES["roas_poor"]:
            return [
                Recommendation(
                    type="reduce_budget",
                    priority="high",
                    title=f"Reduce budget: {s.campaign_name} underperforming",
                    description=(
                        f"7-day ROAS: {s.roas_7d:.2f}x. Consider reducing budget by "
                        "30-50% until performance improves."
                    ),
                    expected_impact="Reduce wasted spend by 30-50%",
                    action_data={
                        "action": "reduce_budget",
                        "campaign_id": s.campaign_id,
                        "reduce_pct": 0.40,
                    },
                    confidence=0.82,
                    reasoning=(
                        f"ROAS {s.roas_7d:.2f} is below the poor threshold of "
                        f"{self.RULES['roas_poor']}. Cutting budget preserves cash "
                        "while debugging."
                    ),
                )
            ]
        return []

    # ── Level 1: CPA overrun ─────────────────────────────────────────────────

    def _check_cpa_overrun(self, s: CampaignSignal) -> list[Recommendation]:
        if s.cpa_7d is None or s.cpa_target is None or s.cpa_target <= 0:
            return []
        overrun_pct = (s.cpa_7d - s.cpa_target) / s.cpa_target
        if overrun_pct > self.RULES["cpa_overrun_pct"]:
            return [
                Recommendation(
                    type="reduce_budget",
                    priority="high",
                    title=f"CPA overrun: {s.campaign_name}",
                    description=(
                        f"Current CPA: ${s.cpa_7d:.2f} vs target ${s.cpa_target:.2f} "
                        f"(+{overrun_pct*100:.0f}% over target)"
                    ),
                    expected_impact=f"Realign CPA toward ${s.cpa_target:.2f} target",
                    action_data={
                        "action": "reduce_budget",
                        "campaign_id": s.campaign_id,
                        "reduce_pct": 0.30,
                    },
                    confidence=0.78,
                    reasoning=(
                        f"CPA is {overrun_pct*100:.0f}% above target. Likely audience "
                        "exhaustion, weak creative, or landing page issues."
                    ),
                )
            ]
        return []

    # ── Level 2: Creative fatigue ────────────────────────────────────────────

    def _check_creative_fatigue(self, s: CampaignSignal) -> list[Recommendation]:
        if s.frequency >= self.RULES["frequency_fatigue"]:
            return [
                Recommendation(
                    type="creative_refresh",
                    priority="high",
                    title=f"Creative fatigue: {s.campaign_name}",
                    description=(
                        f"Average frequency: {s.frequency:.1f}x — your audience has "
                        "seen this ad too many times. CTR likely declining."
                    ),
                    expected_impact="+20-35% CTR improvement with fresh creative",
                    action_data={
                        "action": "refresh_creative",
                        "campaign_id": s.campaign_id,
                        "current_frequency": s.frequency,
                    },
                    confidence=0.88,
                    reasoning=(
                        f"Frequency of {s.frequency:.1f} exceeds the fatigue threshold "
                        f"of {self.RULES['frequency_fatigue']}."
                    ),
                )
            ]
        return []

    # ── Level 2: Budget constraints ──────────────────────────────────────────

    def _check_budget_constraints(self, s: CampaignSignal) -> list[Recommendation]:
        recs: list[Recommendation] = []
        if (
            s.budget_utilization >= self.RULES["budget_cap_hit"]
            and s.roas_7d >= self.RULES["roas_good"]
        ):
            recs.append(
                Recommendation(
                    type="increase_budget",
                    priority="high",
                    title=(f"Budget constrained: {s.campaign_name} hitting daily cap"),
                    description=(
                        f"Campaign is hitting its budget cap with {s.roas_7d:.2f}x "
                        "ROAS. Increasing budget could unlock more profitable conversions."
                    ),
                    expected_impact="Estimated +25% more conversions with 25% budget bump",
                    action_data={
                        "action": "increase_budget",
                        "campaign_id": s.campaign_id,
                        "increase_pct": 0.25,
                    },
                    confidence=0.80,
                    reasoning=(
                        f"Budget utilization {s.budget_utilization*100:.0f}% with "
                        f"healthy ROAS {s.roas_7d:.2f}. Profitable but throttled."
                    ),
                )
            )
        elif (
            s.budget_utilization <= self.RULES["budget_waste_utilization"]
            and s.roas_7d < self.RULES["roas_poor"]
        ):
            recs.append(
                Recommendation(
                    type="reduce_budget",
                    priority="medium",
                    title=f"Budget wasted: {s.campaign_name} not spending",
                    description=(
                        f"Only {s.budget_utilization*100:.0f}% of budget used with "
                        "poor ROAS. Reallocate to better campaigns."
                    ),
                    expected_impact="Reallocate wasted budget to higher-ROAS campaigns",
                    action_data={
                        "action": "reduce_budget",
                        "campaign_id": s.campaign_id,
                        "reduce_pct": 0.50,
                    },
                    confidence=0.70,
                    reasoning=(
                        "Low delivery + low ROAS = the campaign isn't earning its "
                        "budget — reallocate."
                    ),
                )
            )
        return recs

    # ── Level 3: Scaling opportunity ────────────────────────────────────────

    def _check_scaling_opportunity(self, s: CampaignSignal) -> list[Recommendation]:
        if (
            s.roas_7d >= self.RULES["roas_excellent"]
            and s.budget_utilization < self.RULES["budget_cap_hit"]
            and s.frequency < 4.0
        ):
            return [
                Recommendation(
                    type="scale_budget",
                    priority="high",
                    title=f"Scale opportunity: {s.campaign_name}",
                    description=(
                        f"Excellent ROAS of {s.roas_7d:.2f}x with room to grow. "
                        "Recommend increasing budget by 30-50%."
                    ),
                    expected_impact=(
                        f"Estimated ${s.spend_7d * 0.4:.0f} additional profitable " "spend per week"
                    ),
                    action_data={
                        "action": "increase_budget",
                        "campaign_id": s.campaign_id,
                        "increase_pct": 0.40,
                    },
                    confidence=0.85,
                    reasoning=(
                        f"ROAS {s.roas_7d:.2f} exceeds excellent threshold; frequency "
                        f"{s.frequency:.1f} is healthy; budget headroom available. "
                        "Prime scaling candidate."
                    ),
                )
            ]
        if (
            s.roas_7d >= self.RULES["roas_good"]
            and s.roas_trend >= self.RULES["roas_trend_improve"]
        ):
            return [
                Recommendation(
                    type="scale_budget",
                    priority="medium",
                    title=f"Scale candidate: {s.campaign_name} improving",
                    description=(
                        f"ROAS {s.roas_7d:.2f}x and trending up "
                        f"{s.roas_trend*100:.0f}%. Consider 15-20% budget increase."
                    ),
                    expected_impact="Capture improving trend before saturation",
                    action_data={
                        "action": "increase_budget",
                        "campaign_id": s.campaign_id,
                        "increase_pct": 0.20,
                    },
                    confidence=0.72,
                    reasoning=(
                        f"Positive ROAS trend of {s.roas_trend*100:.0f}% week-over-"
                        "week with solid base performance."
                    ),
                )
            ]
        return []

    # ── Level 3: ROAS trend ──────────────────────────────────────────────────

    def _check_roas_trend(self, s: CampaignSignal) -> list[Recommendation]:
        if (
            s.roas_trend <= self.RULES["roas_trend_decline"]
            and s.roas_7d >= self.RULES["roas_poor"]
        ):
            return [
                Recommendation(
                    type="monitor",
                    priority="medium",
                    title=f"ROAS declining: {s.campaign_name}",
                    description=(
                        f"ROAS dropped {abs(s.roas_trend)*100:.0f}% week-over-week. "
                        "Still profitable but watch closely."
                    ),
                    expected_impact="Early warning — act before it becomes critical",
                    action_data={
                        "action": "monitor",
                        "campaign_id": s.campaign_id,
                        "roas_trend": s.roas_trend,
                    },
                    confidence=0.75,
                    reasoning=(
                        f"Decline of {abs(s.roas_trend)*100:.0f}% is significant. "
                        "Common causes: audience fatigue, increased competition, "
                        "creative staleness."
                    ),
                )
            ]
        return []

    # ── Portfolio-level allocation ───────────────────────────────────────────

    def compute_portfolio_allocation(self, campaigns: list[dict], total_budget: float) -> dict:
        """
        Redistribute total budget across campaigns based on ROAS efficiency.
        Returns {campaign_id: recommended_spend}.
        """
        if not campaigns:
            return {}

        df = pd.DataFrame(campaigns)
        df = df[df["roas_7d"] > 0].copy()
        if df.empty:
            return {}

        # Convex weighting — favor higher ROAS but don't go all-in on a single campaign
        df["roas_weight"] = np.maximum(df["roas_7d"] - 1, 0) ** 1.5
        total_weight = df["roas_weight"].sum()

        if total_weight == 0:
            n = len(df)
            return {str(row["campaign_id"]): round(total_budget / n, 2) for _, row in df.iterrows()}

        allocation = {}
        for _, row in df.iterrows():
            share = row["roas_weight"] / total_weight
            allocation[str(row["campaign_id"])] = round(total_budget * share, 2)
        return allocation
