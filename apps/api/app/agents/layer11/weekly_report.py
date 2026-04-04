"""
WeeklyReportAgent — Layer 11

Synthesizes data from all sources into a structured weekly growth report.
Supports markdown and HTML export.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class WeeklyReportInput(BaseModel):
    workspace_id: uuid.UUID
    site_id: uuid.UUID | None = None
    period_end: datetime | None = None
    include_recommendations: bool = True
    include_experiments: bool = True
    kpis: dict = {}
    top_opportunities: list[dict] = []
    top_risks: list[dict] = []
    pending_approvals_count: int = 0
    active_experiments_count: int = 0
    completed_items: list[str] = []


class ReportSection(BaseModel):
    title: str
    content: str
    data: dict = {}


class WeeklyReportOutput(BaseModel):
    title: str
    period_start: datetime
    period_end: datetime
    executive_summary: str
    kpi_summary: dict
    sections: list[ReportSection]
    content_md: str
    content_html: str
    next_7_day_plan: list[str]
    next_30_day_plan: list[str]
    risk_items: list[str]
    opportunity_items: list[str]


class WeeklyReportAgent(LLMAgent[WeeklyReportInput, WeeklyReportOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="WeeklyReportAgent",
        layer=11,
        description="Generates weekly growth report",
        max_retries=2,
        timeout_seconds=120,
    )

    async def _execute(
        self,
        input_data: WeeklyReportInput,
        context: AgentRunContext,
    ) -> WeeklyReportOutput:
        now = input_data.period_end or datetime.now(UTC)
        period_start = now - timedelta(days=7)
        period_end = now

        title = f"Weekly Growth Report — {period_start.strftime('%b %d')} to {period_end.strftime('%b %d, %Y')}"

        # Build sections
        sections: list[ReportSection] = []

        # KPI section
        kpi_text = self._format_kpis(input_data.kpis)
        sections.append(
            ReportSection(
                title="KPI Summary",
                content=kpi_text,
                data=input_data.kpis,
            )
        )

        # Opportunities
        if input_data.top_opportunities:
            opp_text = "\n".join(
                f"- {o.get('title', str(o))}" for o in input_data.top_opportunities[:5]
            )
            sections.append(ReportSection(title="Top Opportunities", content=opp_text))

        # Risks
        if input_data.top_risks:
            risk_text = "\n".join(f"- {r.get('title', str(r))}" for r in input_data.top_risks[:5])
            sections.append(ReportSection(title="Risks & Blockers", content=risk_text))

        # Approval queue
        sections.append(
            ReportSection(
                title="Pending Approvals",
                content=f"{input_data.pending_approvals_count} items awaiting approval.",
            )
        )

        # LLM narrative
        executive_summary = await self._generate_summary(input_data, sections, context)
        next_7 = await self._generate_next_actions(input_data, 7, context)
        next_30 = await self._generate_next_actions(input_data, 30, context)

        # Render markdown
        md = self._render_markdown(title, executive_summary, sections, next_7, next_30)
        html = self._render_html(title, executive_summary, sections, next_7, next_30)

        return WeeklyReportOutput(
            title=title,
            period_start=period_start,
            period_end=period_end,
            executive_summary=executive_summary,
            kpi_summary=input_data.kpis,
            sections=sections,
            content_md=md,
            content_html=html,
            next_7_day_plan=next_7,
            next_30_day_plan=next_30,
            risk_items=[r.get("title", "") for r in input_data.top_risks[:5]],
            opportunity_items=[o.get("title", "") for o in input_data.top_opportunities[:5]],
        )

    def _format_kpis(self, kpis: dict) -> str:
        if not kpis:
            return "No KPI data available for this period."
        lines = []
        for k, v in kpis.items():
            if isinstance(v, dict):
                delta = v.get("delta", "")
                delta_str = (
                    f" ({'+' if delta > 0 else ''}{delta}%)"
                    if isinstance(delta, int | float)
                    else ""
                )
                lines.append(f"- **{k}**: {v.get('value', 'N/A')}{delta_str}")
            else:
                lines.append(f"- **{k}**: {v}")
        return "\n".join(lines)

    async def _generate_summary(
        self,
        input_data: WeeklyReportInput,
        sections: list[ReportSection],
        context: AgentRunContext,
    ) -> str:
        if context.demo_mode or not self._llm:
            return (
                "This week the team made solid progress on content and SEO initiatives. "
                "Technical SEO issues were identified and are prioritized for resolution. "
                f"There are {input_data.pending_approvals_count} items pending approval."
            )

        context_text = "\n".join(f"{s.title}: {s.content[:200]}" for s in sections[:4])
        system = "You are a growth analyst. Write a 3-sentence executive summary for a weekly growth report. Be specific and data-driven."
        user = f"Weekly report data:\n{context_text}\n\nOpportunities: {len(input_data.top_opportunities)}\nRisks: {len(input_data.top_risks)}"
        text, _ = await self._call_llm(system, user, max_tokens=300)
        return text or "Weekly report generated."

    async def _generate_next_actions(
        self,
        input_data: WeeklyReportInput,
        days: int,
        context: AgentRunContext,
    ) -> list[str]:
        if context.demo_mode or not self._llm:
            return [
                f"Review and approve {input_data.pending_approvals_count} pending items",
                "Complete technical SEO fixes for critical issues",
                "Publish approved content pieces",
            ]

        opps = [o.get("title", "") for o in input_data.top_opportunities[:3]]
        system = f"Generate a prioritized {days}-day action plan as a JSON array of strings."
        user = f"Top opportunities: {opps}\nPending approvals: {input_data.pending_approvals_count}"

        from pydantic import BaseModel as _BaseModel

        class ActionList(_BaseModel):
            actions: list[str]

        result, _ = await self._call_llm_structured(system, user, ActionList)
        return result.actions[:5] if result else []

    def _render_markdown(
        self,
        title: str,
        summary: str,
        sections: list[ReportSection],
        next_7: list[str],
        next_30: list[str],
    ) -> str:
        parts = [f"# {title}\n", f"## Executive Summary\n\n{summary}\n"]
        for s in sections:
            parts.append(f"## {s.title}\n\n{s.content}\n")
        if next_7:
            parts.append("## Next 7 Days\n\n" + "\n".join(f"- {a}" for a in next_7) + "\n")
        if next_30:
            parts.append("## Next 30 Days\n\n" + "\n".join(f"- {a}" for a in next_30) + "\n")
        return "\n".join(parts)

    def _render_html(
        self,
        title: str,
        summary: str,
        sections: list[ReportSection],
        next_7: list[str],
        next_30: list[str],
    ) -> str:
        import html as html_lib

        content = f"<h1>{html_lib.escape(title)}</h1>"
        content += f"<h2>Executive Summary</h2><p>{html_lib.escape(summary)}</p>"
        for s in sections:
            content += f"<h2>{html_lib.escape(s.title)}</h2><p>{html_lib.escape(s.content)}</p>"
        if next_7:
            items = "".join(f"<li>{html_lib.escape(a)}</li>" for a in next_7)
            content += f"<h2>Next 7 Days</h2><ul>{items}</ul>"
        return f"<!DOCTYPE html><html><body style='font-family:sans-serif;max-width:800px;margin:auto;padding:2rem'>{content}</body></html>"
