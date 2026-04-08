"""
True Profitability Engine

Calculates real ad profit accounting for COGS, shipping, returns, and
retargeting double-counting. Generates kill / scale signals beyond simple
ROAS thresholds.

Why platform ROAS is misleading:
- Doesn't account for COGS or shipping
- Includes organic conversions (especially retargeting)
- Double-counts across platforms
- Ignores return rates

This engine applies contribution margin logic to surface real profit
and emits conservative but actionable kill / scale signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProductCost:
    cogs: float = 0.0  # Cost of goods sold per unit
    shipping_cost: float = 0.0  # Shipping per order
    return_rate: float = 0.05  # 5% return rate default
    currency: str = "USD"


@dataclass
class TrueProfitAnalysis:
    campaign_id: str
    campaign_name: str
    reported_roas: float
    estimated_true_roas: float
    contribution_margin: float
    gross_profit: float
    break_even_roas: float
    kill_signal: bool
    scale_signal: bool
    signal_reason: str
    confidence: float
    period_days: int


class ProfitabilityEngine:
    """Transforms raw ROAS metrics into true profitability signals."""

    KILL_THRESHOLDS = {
        "roas_below_breakeven": True,
        "roas_declining_pct": 0.20,
        "cpa_overrun_pct": 0.50,
        "min_days_before_kill": 5,
        "frequency_fatigue": 7.0,
        "budget_waste_utilization": 0.40,
    }

    SCALE_THRESHOLDS = {
        "min_true_roas_to_scale": 2.5,
        "max_frequency_to_scale": 4.0,
        "min_budget_headroom": 0.15,
        "roas_improving_pct": 0.10,
    }

    def calculate_break_even_roas(self, product_cost: ProductCost, avg_order_value: float) -> float:
        """Minimum ROAS needed to cover all costs."""
        if avg_order_value <= 0:
            return 3.0  # Conservative default

        net_revenue_per_order = (
            avg_order_value
            - product_cost.cogs
            - product_cost.shipping_cost
            - (avg_order_value * product_cost.return_rate)
        )
        contribution_margin = net_revenue_per_order / avg_order_value

        if contribution_margin <= 0:
            return 10.0

        return round(1.0 / contribution_margin, 2)

    def calculate_true_roas(
        self,
        reported_roas: float,
        product_cost: ProductCost,
        avg_order_value: float,
        is_retargeting: bool = False,
    ) -> float:
        """Estimate true incremental ROAS from reported ROAS."""
        if avg_order_value <= 0 or reported_roas <= 0:
            return 0.0

        adjusted_roas = reported_roas
        if is_retargeting:
            # Industry average: 50-75% of retargeted conversions would have
            # happened organically. Conservative discount.
            adjusted_roas *= 0.35

        net_per_order = (
            avg_order_value
            - product_cost.cogs
            - product_cost.shipping_cost
            - (avg_order_value * product_cost.return_rate)
        )
        margin = net_per_order / avg_order_value if avg_order_value > 0 else 0
        true_roas = adjusted_roas * margin
        return round(max(true_roas, 0), 3)

    def analyze_campaign(
        self,
        campaign_id: str,
        campaign_name: str,
        metrics_7d: dict,
        metrics_prev_7d: dict,
        product_cost: ProductCost,
        avg_order_value: float,
        target_cpa: float | None = None,
        is_retargeting: bool = False,
        days_active: int = 14,
    ) -> TrueProfitAnalysis:
        """Full profitability analysis for a campaign."""
        reported_roas = float(metrics_7d.get("roas", 0) or 0)
        spend = float(metrics_7d.get("spend", 0) or 0)
        revenue = float(metrics_7d.get("revenue", 0) or 0)
        conversions = float(metrics_7d.get("conversions", 0) or 0)
        frequency = float(metrics_7d.get("frequency", 0) or 0)
        budget_util = float(metrics_7d.get("budget_utilization", 0.8) or 0.8)

        prev_roas = float(metrics_prev_7d.get("roas", reported_roas) or reported_roas)
        roas_trend = (reported_roas - prev_roas) / prev_roas if prev_roas > 0 else 0

        break_even = self.calculate_break_even_roas(product_cost, avg_order_value)
        true_roas = self.calculate_true_roas(
            reported_roas, product_cost, avg_order_value, is_retargeting
        )

        # Contribution margin & gross profit
        net_rev = (
            revenue
            - (conversions * product_cost.cogs)
            - (conversions * product_cost.shipping_cost)
            - (revenue * product_cost.return_rate)
        )
        contrib_margin = net_rev / revenue if revenue > 0 else 0
        gross_profit = net_rev - spend

        kill = False
        scale = False
        reasons: list[str] = []

        if days_active >= self.KILL_THRESHOLDS["min_days_before_kill"]:
            if true_roas < break_even and true_roas > 0:
                kill = True
                reasons.append(f"True ROAS {true_roas:.2f}x below break-even {break_even:.2f}x")
            elif reported_roas < break_even * 0.8:
                kill = True
                reasons.append(f"Reported ROAS {reported_roas:.2f}x critically low")

        if frequency > self.KILL_THRESHOLDS["frequency_fatigue"]:
            reasons.append(f"Creative fatigue: frequency {frequency:.1f}x (limit: 7.0)")
            if not kill:
                kill = True

        if roas_trend <= -self.KILL_THRESHOLDS["roas_declining_pct"]:
            reasons.append(f"ROAS declining {abs(roas_trend) * 100:.0f}% week-over-week")

        # Scale signals
        if (
            true_roas >= break_even * self.SCALE_THRESHOLDS["min_true_roas_to_scale"]
            and frequency < self.SCALE_THRESHOLDS["max_frequency_to_scale"]
            and budget_util < (1 - self.SCALE_THRESHOLDS["min_budget_headroom"])
            and not kill
        ):
            scale = True
            reasons.append(
                f"True ROAS {true_roas:.2f}x "
                f"({self.SCALE_THRESHOLDS['min_true_roas_to_scale']}x break-even), "
                f"frequency {frequency:.1f}x, budget headroom available"
            )
        elif (
            roas_trend >= self.SCALE_THRESHOLDS["roas_improving_pct"]
            and reported_roas > break_even
            and not kill
        ):
            reasons.append(f"Improving trend +{roas_trend * 100:.0f}% WoW with profitable ROAS")

        # Confidence
        confidence = 0.5
        if days_active >= 14:
            confidence += 0.2
        if conversions >= 10:
            confidence += 0.2
        if spend >= 100:
            confidence += 0.1
        confidence = min(confidence, 0.95)

        return TrueProfitAnalysis(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            reported_roas=round(reported_roas, 3),
            estimated_true_roas=true_roas,
            contribution_margin=round(contrib_margin, 4),
            gross_profit=round(gross_profit, 2),
            break_even_roas=break_even,
            kill_signal=kill,
            scale_signal=scale,
            signal_reason="; ".join(reasons) if reasons else "No significant signal",
            confidence=round(confidence, 3),
            period_days=7,
        )

    def analyze_portfolio(
        self,
        campaigns: list[dict],
        product_cost: ProductCost,
        avg_order_value: float,
        total_budget: float,
    ) -> dict:
        """Portfolio-level analysis with budget reallocation suggestion."""
        analyses: list[tuple[dict, TrueProfitAnalysis]] = []
        for camp in campaigns:
            analysis = self.analyze_campaign(
                campaign_id=str(camp.get("id", "")),
                campaign_name=camp.get("name", ""),
                metrics_7d=camp,
                metrics_prev_7d=camp.get("prev", {}),
                product_cost=product_cost,
                avg_order_value=avg_order_value,
                is_retargeting="retarget" in (camp.get("name", "") or "").lower(),
            )
            analyses.append((camp, analysis))

        winners = [(c, a) for c, a in analyses if a.scale_signal and not a.kill_signal]
        losers = [(c, a) for c, a in analyses if a.kill_signal]

        loser_budget = sum(float(c.get("spend", 0) or 0) for c, _ in losers)

        allocation: dict[str, float] = {}
        winner_roas_sum = sum(a.estimated_true_roas for _, a in winners) or 1
        for camp, analysis in analyses:
            if analysis.kill_signal:
                allocation[str(camp.get("id", ""))] = 0.0
            elif analysis.scale_signal:
                extra = loser_budget * (analysis.estimated_true_roas / winner_roas_sum)
                current = float(camp.get("spend", 0) or 0)
                allocation[str(camp.get("id", ""))] = round(current + extra, 2)
            else:
                allocation[str(camp.get("id", ""))] = float(camp.get("spend", 0) or 0)

        return {
            "winners": [(c.get("name"), a.estimated_true_roas) for c, a in winners],
            "losers": [(c.get("name"), a.signal_reason) for c, a in losers],
            "budget_freed": round(loser_budget, 2),
            "recommended_allocation": allocation,
            "analyses": [
                {
                    "campaign_id": a.campaign_id,
                    "campaign_name": a.campaign_name,
                    "reported_roas": a.reported_roas,
                    "true_roas": a.estimated_true_roas,
                    "break_even_roas": a.break_even_roas,
                    "gross_profit": a.gross_profit,
                    "contribution_margin": a.contribution_margin,
                    "kill": a.kill_signal,
                    "scale": a.scale_signal,
                    "reason": a.signal_reason,
                    "confidence": a.confidence,
                }
                for _, a in analyses
            ],
        }
