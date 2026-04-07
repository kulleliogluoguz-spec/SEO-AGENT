"""
AI Synthesis Engine — local Ollama (qwen3:8b)
Converts raw analytics signals into human-readable insights.
100% local, no external API calls.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
TIMEOUT = 120


class AISynthesisEngine:
    """Local Ollama-backed insight generation for ad analytics."""

    async def _call_ollama(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.3,
                        },
                    },
                )
                if resp.status_code != 200:
                    return f"AI unavailable (HTTP {resp.status_code})"
                text = resp.json().get("response", "").strip()
                # Strip <think>...</think> blocks from qwen3 reasoning
                while "<think>" in text and "</think>" in text:
                    s = text.index("<think>")
                    e = text.index("</think>") + len("</think>")
                    text = text[:s] + text[e:]
                return text.strip() or "(no response)"
        except httpx.ConnectError:
            return "AI unavailable: Ollama not running. Start it with: ollama serve"
        except httpx.ReadTimeout:
            return "AI timeout: Ollama is loading the model. Retry in a moment."
        except Exception as e:
            logger.error("[ai_synthesis] ollama call failed: %s", e)
            return f"AI error: {str(e)[:100]}"

    # ── Campaign-level insight ───────────────────────────────────────────────

    async def generate_campaign_insight(
        self,
        campaign_name: str,
        metrics: dict,
        recommendations: list[dict],
    ) -> str:
        """Generate a 2-3 sentence strategic insight for one campaign."""
        recs_text = "\n".join(
            [
                f"- [{r['priority'].upper()}] {r['title']}: {r['description']}"
                for r in recommendations[:3]
            ]
        )
        cpa_text = f"${metrics.get('cpa_7d', 0):.2f}" if metrics.get("cpa_7d") else "N/A"

        prompt = f"""You are an expert paid advertising analyst. Analyze this campaign and write a 2-3 sentence strategic insight.

Campaign: {campaign_name}
7-day ROAS: {metrics.get('roas_7d', 'N/A')}
7-day Spend: ${metrics.get('spend_7d', 0):.0f}
7-day CPA: {cpa_text}
CTR: {float(metrics.get('ctr_7d', 0))*100:.2f}%
Frequency: {metrics.get('frequency', 'N/A')}
ROAS Trend: {'+' if metrics.get('roas_trend', 0) > 0 else ''}{float(metrics.get('roas_trend', 0))*100:.0f}% week-over-week

Issues detected:
{recs_text if recs_text else "No critical issues"}

Write a concise, actionable 2-3 sentence analysis for a non-technical marketing manager. Be direct and specific. Skip preamble."""

        return await self._call_ollama(prompt, max_tokens=200)

    # ── Weekly executive report ──────────────────────────────────────────────

    async def generate_weekly_report(self, account_data: dict) -> str:
        """Generate a 3-paragraph executive weekly performance summary."""
        campaigns_summary = "\n".join(
            [
                f"- {c.get('name','?')}: ROAS {c.get('roas_7d', 0):.2f}x, "
                f"Spend ${c.get('spend_7d', 0):.0f}, "
                f"Status: {c.get('ai_status', 'unknown')}"
                for c in account_data.get("campaigns", [])[:10]
            ]
        )

        prompt = f"""You are a performance marketing consultant. Write a professional weekly ad performance summary.

Account: {account_data.get('account_name', 'Ad Account')}
Period: Last 7 days
Total Spend: ${account_data.get('total_spend_7d', 0):.0f}
Total Revenue: ${account_data.get('total_revenue_7d', 0):.0f}
Overall ROAS: {account_data.get('overall_roas_7d', 0):.2f}x
Total Conversions: {account_data.get('total_conversions_7d', 0):.0f}

Campaign Breakdown:
{campaigns_summary or "No campaign data"}

Top Recommendations:
{json.dumps(account_data.get('top_recommendations', [])[:3], indent=2)}

Write a 3-paragraph executive summary:
1. Overall performance assessment
2. Key wins and critical issues
3. This week's priority actions

Be specific with numbers. Use plain business language. Skip preamble."""

        return await self._call_ollama(prompt, max_tokens=500)

    # ── Budget recommendation explanation ────────────────────────────────────

    async def explain_budget_recommendation(
        self,
        current_allocation: dict,
        optimal_allocation: dict,
        expected_uplift: float,
    ) -> str:
        """Explain MMM budget reallocation in plain English."""
        changes = []
        for cid, optimal_spend in optimal_allocation.items():
            current_spend = float(current_allocation.get(cid, 0) or 0)
            if current_spend > 0:
                change_pct = (optimal_spend - current_spend) / current_spend * 100
            else:
                change_pct = 100
            changes.append(
                f"- Campaign {cid}: ${current_spend:.0f} → ${optimal_spend:.0f} "
                f"({'+' if change_pct > 0 else ''}{change_pct:.0f}%)"
            )

        prompt = f"""Explain this budget reallocation recommendation in plain English for a business owner.

Current vs Recommended Budget Allocation:
{chr(10).join(changes)}

Expected ROAS improvement: +{expected_uplift*100:.0f}%

Write 2-3 sentences explaining: what's being recommended, why, and what the business impact will be. Use simple language. Skip preamble."""

        return await self._call_ollama(prompt, max_tokens=200)

    # ── Quick health classification (rule-based for speed) ──────────────────

    def classify_campaign_health(
        self,
        roas: float,
        cpa: float | None,
        cpa_target: float | None,
        frequency: float,
    ) -> str:
        """Synchronous health classification — no AI needed."""
        if roas < 1.0:
            return "critical"
        if roas < 1.5:
            return "poor"
        if frequency > 8:
            return "fatigued"
        if roas > 4.0:
            return "excellent"
        if roas > 2.5:
            return "good"
        return "average"
