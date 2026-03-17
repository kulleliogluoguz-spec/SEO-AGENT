"""
Compliance & Safety Service
Enforces: no spam, no fake engagement, no deceptive claims,
          approval-gated publishing, risk scoring, policy warnings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PolicyViolation(str, Enum):
    SPAM = "spam"
    FAKE_ENGAGEMENT = "fake_engagement"
    DECEPTIVE_CLAIMS = "deceptive_claims"
    EXCESSIVE_HASHTAGS = "excessive_hashtags"
    RATE_LIMIT_RISK = "rate_limit_risk"
    PROHIBITED_CONTENT = "prohibited_content"
    BRAND_SAFETY = "brand_safety"
    PLATFORM_TOS = "platform_tos"


@dataclass
class ComplianceResult:
    passed: bool
    risk_score: float  # 0.0 = safe, 1.0 = critical
    risk_level: str    # low, medium, high, critical
    violations: list[dict]
    warnings: list[str]
    recommendations: list[str]


# ─── Spam Patterns ───────────────────────────────────────────────────────────

SPAM_PATTERNS = [
    r"follow\s+for\s+follow",
    r"f4f",
    r"buy\s+followers",
    r"get\s+\d+\s+followers",
    r"free\s+money",
    r"click\s+the\s+link\s+in\s+(my\s+)?bio",  # Overused, not always spam, but flagged
    r"dm\s+me\s+(for|to)\s+",
    r"guaranteed\s+results",
    r"make\s+\$\d+.*per\s+(day|hour|week)",
    r"limited\s+time\s+offer.*act\s+now",
]

DECEPTIVE_PATTERNS = [
    r"100%\s+guaranteed",
    r"instant\s+results",
    r"get\s+rich\s+quick",
    r"no\s+risk",
    r"secret\s+(method|formula|hack)",
    r"doctors?\s+hate",
    r"one\s+weird\s+trick",
]

PROHIBITED_TERMS = [
    "buy followers", "fake reviews", "botted", "click farm",
    "guaranteed ROI", "pyramid scheme",
]


class ComplianceService:
    """Central compliance gate for all marketing content."""

    def check_content(self, body: str, channel: str,
                      hashtags: list[str] = None,
                      channel_metadata: dict = None) -> ComplianceResult:
        violations = []
        warnings = []
        recommendations = []
        risk_score = 0.0

        text = body.lower()
        hashtags = hashtags or []
        channel_metadata = channel_metadata or {}

        # ── Spam Check ──
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "type": PolicyViolation.SPAM.value,
                    "detail": f"Spam pattern detected: {pattern}",
                    "severity": 0.4,
                })
                risk_score += 0.4

        # ── Deceptive Claims ──
        for pattern in DECEPTIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "type": PolicyViolation.DECEPTIVE_CLAIMS.value,
                    "detail": f"Potentially deceptive claim: {pattern}",
                    "severity": 0.5,
                })
                risk_score += 0.5

        # ── Prohibited Content ──
        for term in PROHIBITED_TERMS:
            if term.lower() in text:
                violations.append({
                    "type": PolicyViolation.PROHIBITED_CONTENT.value,
                    "detail": f"Prohibited term: '{term}'",
                    "severity": 0.8,
                })
                risk_score += 0.8

        # ── Hashtag Limits ──
        if channel == "instagram" and len(hashtags) > 30:
            violations.append({
                "type": PolicyViolation.EXCESSIVE_HASHTAGS.value,
                "detail": f"Instagram allows max 30 hashtags, got {len(hashtags)}",
                "severity": 0.3,
            })
            risk_score += 0.3
        elif channel == "instagram" and len(hashtags) > 20:
            warnings.append(f"Consider reducing hashtags to 10-15 for optimal reach (currently {len(hashtags)}).")

        # ── Content Length Checks ──
        if channel == "twitter":
            thread = channel_metadata.get("thread", [])
            for i, tweet in enumerate(thread):
                if len(tweet) > 280:
                    warnings.append(f"Thread tweet #{i+1} exceeds 280 chars ({len(tweet)}).")
                    risk_score += 0.1

        if channel == "instagram" and len(body) > 2200:
            warnings.append(f"Caption exceeds Instagram's 2200 char limit ({len(body)}).")
            risk_score += 0.2

        if channel == "linkedin" and len(body) > 3000:
            warnings.append(f"Post exceeds LinkedIn's 3000 char limit ({len(body)}).")
            risk_score += 0.2

        if channel == "tiktok" and len(body) > 2200:
            warnings.append(f"Caption exceeds TikTok's 2200 char limit ({len(body)}).")
            risk_score += 0.2

        # ── Platform-Specific Checks ──
        if channel == "meta_ads":
            headline = channel_metadata.get("headline", "")
            if headline and len(headline) > 40:
                warnings.append(f"Ad headline exceeds recommended 40 chars ({len(headline)}).")
            primary = channel_metadata.get("primary_text", body)
            if len(primary) > 125:
                warnings.append("Primary text exceeds recommended 125 chars for Meta Ads.")

        # ── All-Caps Check ──
        caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
        if caps_ratio > 0.5 and len(body) > 20:
            warnings.append("Excessive use of capital letters may trigger spam filters.")
            risk_score += 0.15

        # ── Emoji Overload ──
        emoji_count = len(re.findall(r'[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0000200D]', body))
        if emoji_count > 15:
            warnings.append(f"Excessive emoji usage ({emoji_count}) may reduce professionalism.")
            risk_score += 0.1

        # ── URL / Link Density (spam signal) ──
        url_count = len(re.findall(r'https?://\S+', body))
        if url_count > 3:
            violations.append({
                "type": PolicyViolation.SPAM.value,
                "detail": f"Too many links ({url_count}) — likely spam on most platforms.",
                "severity": 0.4,
            })
            risk_score += 0.4
        elif url_count > 1 and channel in ("instagram", "tiktok"):
            warnings.append(f"{url_count} links detected. {channel.title()} posts rarely need multiple links.")
            risk_score += 0.05

        # ── Empty Content Guard ──
        if len(body.strip()) < 10:
            violations.append({
                "type": PolicyViolation.PROHIBITED_CONTENT.value,
                "detail": "Content is too short to be meaningful.",
                "severity": 0.3,
            })
            risk_score += 0.3

        # ── Recommendations ──
        if not any(v["type"] == PolicyViolation.SPAM.value for v in violations):
            recommendations.append("Content passes spam check.")
        if len(hashtags) == 0 and channel in ["instagram", "tiktok"]:
            recommendations.append(f"Consider adding relevant hashtags for {channel} discoverability.")
        if channel == "linkedin" and not body.endswith("?"):
            recommendations.append("End LinkedIn posts with a question to boost engagement.")

        # ── Final Score ──
        risk_score = min(risk_score, 1.0)
        risk_level = (
            "low" if risk_score < 0.2 else
            "medium" if risk_score < 0.5 else
            "high" if risk_score < 0.8 else
            "critical"
        )

        return ComplianceResult(
            passed=risk_score < 0.5,
            risk_score=round(risk_score, 3),
            risk_level=risk_level,
            violations=violations,
            warnings=warnings,
            recommendations=recommendations,
        )

    def check_publishing_allowed(self, automation_level: int, risk_level: str) -> tuple[bool, str]:
        """Check if auto-publishing is allowed given automation level and risk."""
        if automation_level <= 0:
            return False, "Draft only mode — manual publishing required."
        if automation_level == 1:
            return False, "Approval required — content must be reviewed before publishing."
        if automation_level == 2:
            if risk_level in ("high", "critical"):
                return False, f"Risk level '{risk_level}' too high for auto-publish."
            if risk_level == "medium":
                return False, "Medium-risk content requires manual approval at level 2."
            return True, "Low-risk content approved for auto-publish."
        if automation_level >= 3:
            if risk_level == "critical":
                return False, "Critical risk content cannot be auto-published at any level."
            return True, f"Advanced automation: auto-publishing with risk level '{risk_level}'."
        return False, "Publishing not allowed."


# Singleton
compliance_service = ComplianceService()
