"""
ComplianceGuardianAgent — Layer 0

Reviews content and proposed actions for compliance violations.
Checks for: deceptive claims, unverified statistics, misleading comparisons,
spam patterns, community rule violations, and platform policy violations.
"""
from typing import ClassVar

from pydantic import BaseModel

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class ComplianceInput(BaseModel):
    content: str
    content_type: str  # blog | landing_page | social_post | email | comparison_page
    claims: list[str] = []  # Specific claims to verify
    channel: str = "owned"  # owned | reddit | hackernews | linkedin | twitter | email


class ComplianceFlag(BaseModel):
    severity: str  # critical | warning | info
    flag_type: str
    description: str
    location: str | None = None
    recommendation: str


class ComplianceOutput(BaseModel):
    passed: bool
    risk_score: float  # 0.0 (clean) to 1.0 (high risk)
    flags: list[ComplianceFlag]
    summary: str
    safe_to_auto_publish: bool  # Always False for community channels


# Rule-based patterns that always trigger flags
DECEPTIVE_PATTERNS = [
    ("guaranteed results", "warning", "Absolute guarantees are often misleading"),
    ("100% proven", "critical", "Absolute proof claims require strong evidence"),
    ("risk-free", "warning", "No business action is entirely risk-free"),
    ("#1 in the world", "critical", "Superlative claims require citation"),
    ("scientifically proven", "warning", "Requires specific study citation"),
    ("customers love us", "info", "Testimonial claims need specifics"),
    ("everyone is switching", "warning", "Bandwagon claims can be misleading"),
]

# Channels that always require human review (never auto-publish)
HUMAN_REVIEW_REQUIRED_CHANNELS = {
    "reddit", "hackernews", "twitter", "linkedin",
    "facebook", "instagram", "producthunt",
}


class ComplianceGuardianAgent(LLMAgent[ComplianceInput, ComplianceOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="ComplianceGuardianAgent",
        layer=0,
        description="Reviews content and actions for compliance violations",
        requires_llm=True,
        timeout_seconds=60,
    )

    async def _execute(
        self,
        input_data: ComplianceInput,
        context: AgentRunContext,
    ) -> ComplianceOutput:
        flags: list[ComplianceFlag] = []
        content_lower = input_data.content.lower()

        # Rule-based checks (fast, no LLM)
        for pattern, severity, description in DECEPTIVE_PATTERNS:
            if pattern.lower() in content_lower:
                flags.append(ComplianceFlag(
                    severity=severity,
                    flag_type="deceptive_language",
                    description=f"Found potentially deceptive phrase: '{pattern}'",
                    location=pattern,
                    recommendation=description,
                ))

        # Check for unverified statistics
        import re
        stat_pattern = re.compile(r'\b\d+%|\b\d+x\b|\$\d+[MBK]', re.IGNORECASE)
        stats_found = stat_pattern.findall(input_data.content)
        if stats_found:
            flags.append(ComplianceFlag(
                severity="info",
                flag_type="unverified_statistic",
                description=f"Found {len(stats_found)} numeric claim(s) that require source citation: {', '.join(stats_found[:5])}",
                recommendation="Ensure all statistics have verifiable sources. Add citation or remove.",
            ))

        # Channel-specific rules
        safe_to_auto = True
        if input_data.channel in HUMAN_REVIEW_REQUIRED_CHANNELS:
            safe_to_auto = False
            flags.append(ComplianceFlag(
                severity="info",
                flag_type="channel_requires_review",
                description=f"Content for '{input_data.channel}' always requires human review before posting.",
                recommendation="Review content for authenticity, community norms, and platform rules before submitting.",
            ))

        # LLM-enhanced compliance review
        if self._llm and not context.demo_mode and input_data.content:
            llm_flags = await self._llm_review(input_data, context)
            flags.extend(llm_flags)

        # Compute risk score
        critical_count = sum(1 for f in flags if f.severity == "critical")
        warning_count = sum(1 for f in flags if f.severity == "warning")
        risk_score = min(1.0, critical_count * 0.3 + warning_count * 0.1)

        passed = critical_count == 0

        summary = self._build_summary(flags, risk_score, passed)

        return ComplianceOutput(
            passed=passed,
            risk_score=round(risk_score, 2),
            flags=flags,
            summary=summary,
            safe_to_auto_publish=safe_to_auto and passed and risk_score < 0.2,
        )

    async def _llm_review(
        self,
        input_data: ComplianceInput,
        context: AgentRunContext,
    ) -> list[ComplianceFlag]:
        """Use LLM for nuanced compliance review."""
        system = """You are a compliance reviewer for a B2B SaaS marketing team.
Review the content for:
1. Deceptive or misleading claims
2. Unverified statistics or comparisons
3. Dark patterns or manipulative language
4. Platform/community rule violations
5. Claims that could expose the company to legal risk

Respond with JSON: {"flags": [{"severity": "critical|warning|info", "flag_type": "string", "description": "string", "recommendation": "string"}]}
If no issues, return {"flags": []}"""

        user = f"Content type: {input_data.content_type}\nChannel: {input_data.channel}\n\nContent:\n{input_data.content[:3000]}"

        from pydantic import BaseModel as PBM
        class LLMFlags(PBM):
            flags: list[ComplianceFlag]

        result, _ = await self._call_llm_structured(system, user, LLMFlags)
        return result.flags if result else []

    def _build_summary(
        self, flags: list[ComplianceFlag], risk_score: float, passed: bool
    ) -> str:
        if not flags:
            return "No compliance issues detected. Content appears clean."
        critical = sum(1 for f in flags if f.severity == "critical")
        warnings = sum(1 for f in flags if f.severity == "warning")
        info = sum(1 for f in flags if f.severity == "info")
        parts = []
        if critical:
            parts.append(f"{critical} critical issue(s) must be resolved before publishing")
        if warnings:
            parts.append(f"{warnings} warning(s) should be reviewed")
        if info:
            parts.append(f"{info} informational note(s)")
        status = "BLOCKED" if not passed else "REVIEW RECOMMENDED"
        return f"{status}: {'; '.join(parts)}. Risk score: {risk_score:.0%}."
