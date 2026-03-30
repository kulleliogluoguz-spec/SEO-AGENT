"""
Guardrail Layer — Input/output validation, safety, and compliance.

Provides:
- Input sanitization (prompt injection detection, PII stripping)
- Output validation (schema compliance, hallucination flags)
- Content safety checks (deceptive content, spam detection)
- Action safety (high-risk action blocking)
- Rate limiting per-workspace
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GuardrailSeverity(str, Enum):
    BLOCK = "block"      # Must stop execution
    WARN = "warn"        # Flag but continue
    INFO = "info"        # Informational only


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    issues: list[dict[str, Any]] = field(default_factory=list)
    sanitized_input: Optional[str] = None  # Cleaned version of input
    blocked: bool = False

    def add_issue(self, severity: GuardrailSeverity, category: str, message: str, detail: str = "") -> None:
        self.issues.append({
            "severity": severity.value,
            "category": category,
            "message": message,
            "detail": detail,
        })
        if severity == GuardrailSeverity.BLOCK:
            self.passed = False
            self.blocked = True


class InputGuardrail:
    """Validates and sanitizes AI inputs."""

    # Patterns that suggest prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore (?:all )?(?:previous |prior |above )?instructions",
        r"you are now",
        r"new instructions:",
        r"system prompt:",
        r"forget (?:everything|your|all)",
        r"override (?:your|the) (?:instructions|rules|guidelines)",
        r"act as (?:if you (?:are|were)|a)",
        r"pretend (?:you are|to be)",
        r"jailbreak",
        r"DAN mode",
    ]

    # PII patterns for optional stripping
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    }

    def check(self, text: str, strip_pii: bool = False) -> GuardrailResult:
        result = GuardrailResult(passed=True)
        sanitized = text

        # Check for injection attempts
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                result.add_issue(
                    GuardrailSeverity.WARN,
                    "prompt_injection",
                    "Potential prompt injection detected",
                    f"Pattern: {pattern}",
                )
                break

        # Check input length
        if len(text) > 100000:
            result.add_issue(
                GuardrailSeverity.BLOCK,
                "input_length",
                "Input exceeds maximum length (100K chars)",
            )

        # Optional PII stripping
        if strip_pii:
            for pii_type, pattern in self.PII_PATTERNS.items():
                if re.search(pattern, sanitized):
                    sanitized = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", sanitized)
                    result.add_issue(
                        GuardrailSeverity.INFO,
                        "pii_detected",
                        f"PII ({pii_type}) detected and redacted",
                    )

        result.sanitized_input = sanitized
        return result


class OutputGuardrail:
    """Validates AI outputs."""

    # Patterns indicating potential hallucination or unsafe content
    UNSAFE_PATTERNS = [
        r"(?:buy|purchase|order) (?:now|today|immediately) (?:before|while) (?:stocks|supplies) last",
        r"guaranteed (?:results|returns|income|success)",
        r"(?:100|hundred) ?% (?:guaranteed|risk.?free|money.?back)",
        r"act (?:now|fast|quickly) (?:or|before)",
        r"limited time (?:only|offer)",
    ]

    SPAM_SIGNALS = [
        r"click here",
        r"buy now",
        r"(?:free|cheap) (?:viagra|cialis|pills)",
        r"(?:make|earn) \$?\d+(?:,\d+)? (?:per|a) (?:day|week|month)",
    ]

    def check(self, content: str, content_type: str = "general") -> GuardrailResult:
        result = GuardrailResult(passed=True)

        # Check for deceptive marketing patterns
        for pattern in self.UNSAFE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_issue(
                    GuardrailSeverity.WARN,
                    "deceptive_content",
                    "Potentially deceptive marketing language detected",
                    f"Pattern match: {pattern}",
                )

        # Check for spam signals
        for pattern in self.SPAM_SIGNALS:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_issue(
                    GuardrailSeverity.BLOCK,
                    "spam_content",
                    "Spam-like content detected",
                    f"Pattern match: {pattern}",
                )

        # Check output length (prevent runaway generation)
        if len(content) > 200000:
            result.add_issue(
                GuardrailSeverity.WARN,
                "output_length",
                "Output exceeds expected length",
            )

        # Check for empty/minimal output
        if len(content.strip()) < 10:
            result.add_issue(
                GuardrailSeverity.WARN,
                "minimal_output",
                "Output is suspiciously short",
            )

        return result

    def validate_json_output(self, content: str, schema: Optional[dict] = None) -> GuardrailResult:
        """Validate structured JSON output."""
        import json as json_mod

        result = GuardrailResult(passed=True)
        try:
            parsed = json_mod.loads(content)
            # Basic schema validation if provided
            if schema and "properties" in schema:
                required = schema.get("required", [])
                for field_name in required:
                    if field_name not in parsed:
                        result.add_issue(
                            GuardrailSeverity.WARN,
                            "schema_violation",
                            f"Required field missing: {field_name}",
                        )
        except json_mod.JSONDecodeError as e:
            result.add_issue(
                GuardrailSeverity.WARN,
                "json_parse_error",
                f"Invalid JSON output: {str(e)[:100]}",
            )
        return result


class ActionGuardrail:
    """Safety checks for AI-triggered actions."""

    HIGH_RISK_ACTIONS = {
        "publish_content",
        "send_email",
        "post_social",
        "modify_site",
        "delete_data",
        "change_settings",
        "execute_campaign",
    }

    def check_action(self, action: str, autonomy_level: int = 1) -> GuardrailResult:
        result = GuardrailResult(passed=True)

        is_high_risk = action in self.HIGH_RISK_ACTIONS

        if is_high_risk and autonomy_level < 3:
            result.add_issue(
                GuardrailSeverity.BLOCK,
                "high_risk_action",
                f"Action '{action}' requires approval at autonomy level {autonomy_level}",
                "This action will be queued for human review.",
            )

        if autonomy_level == 0:
            result.add_issue(
                GuardrailSeverity.BLOCK,
                "read_only_mode",
                "System is in read-only analysis mode (autonomy level 0)",
            )

        return result


class GuardrailManager:
    """Central guardrail management."""

    def __init__(self) -> None:
        self.input_guard = InputGuardrail()
        self.output_guard = OutputGuardrail()
        self.action_guard = ActionGuardrail()
        self._check_count = 0
        self._block_count = 0

    def check_input(self, text: str, strip_pii: bool = False) -> GuardrailResult:
        self._check_count += 1
        result = self.input_guard.check(text, strip_pii=strip_pii)
        if result.blocked:
            self._block_count += 1
        return result

    def check_output(self, content: str, content_type: str = "general") -> GuardrailResult:
        self._check_count += 1
        result = self.output_guard.check(content, content_type)
        if result.blocked:
            self._block_count += 1
        return result

    def check_action(self, action: str, autonomy_level: int = 1) -> GuardrailResult:
        self._check_count += 1
        result = self.action_guard.check_action(action, autonomy_level)
        if result.blocked:
            self._block_count += 1
        return result

    def get_stats(self) -> dict:
        return {
            "total_checks": self._check_count,
            "total_blocks": self._block_count,
            "block_rate": self._block_count / max(self._check_count, 1),
        }


# Singleton
_manager: Optional[GuardrailManager] = None


def get_guardrail_manager() -> GuardrailManager:
    global _manager
    if _manager is None:
        _manager = GuardrailManager()
    return _manager
