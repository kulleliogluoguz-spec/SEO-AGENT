"""
Memory / Context Layer — Manages context for AI operations.

Context types:
- Workspace context (settings, preferences, autonomy level)
- Site context (crawl data, pages, technical profile)
- Brand context (voice, positioning, ICP, personas)
- Competitor context (known competitors, battlecards)
- Recommendation context (active recs, history, outcomes)
- Conversation context (multi-turn agent sessions)
- Campaign context (active campaigns, performance)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceContext:
    """Context about the current workspace."""
    workspace_id: str = ""
    workspace_name: str = ""
    autonomy_level: int = 1
    features_enabled: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteContext:
    """Context about the site being analyzed."""
    site_id: str = ""
    url: str = ""
    domain: str = ""
    page_count: int = 0
    last_crawl_date: str = ""
    technical_profile: dict[str, Any] = field(default_factory=dict)
    top_pages: list[dict] = field(default_factory=list)
    keyword_profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandContext:
    """Context about the brand."""
    brand_name: str = ""
    tagline: str = ""
    value_propositions: list[str] = field(default_factory=list)
    target_audience: str = ""
    icp: dict[str, Any] = field(default_factory=dict)
    brand_voice: str = ""
    positioning_statement: str = ""
    competitors: list[str] = field(default_factory=list)


@dataclass
class CompetitorContext:
    """Context about known competitors."""
    competitors: list[dict[str, Any]] = field(default_factory=list)
    keyword_overlap: dict[str, Any] = field(default_factory=dict)
    content_gaps: list[str] = field(default_factory=list)
    battlecards: list[dict] = field(default_factory=list)


@dataclass
class RecommendationContext:
    """Context about active recommendations."""
    active_recommendations: list[dict] = field(default_factory=list)
    completed_recommendations: list[dict] = field(default_factory=list)
    rejected_recommendations: list[dict] = field(default_factory=list)
    success_patterns: list[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Multi-turn conversation context for agent sessions."""
    session_id: str = ""
    turns: list[ConversationTurn] = field(default_factory=list)
    max_turns: int = 50  # Prevent unbounded context growth

    def add_turn(self, role: str, content: str, **metadata: Any) -> None:
        self.turns.append(ConversationTurn(role=role, content=content, metadata=metadata))
        # Trim old turns if over limit (keep system + recent)
        if len(self.turns) > self.max_turns:
            system_turns = [t for t in self.turns if t.role == "system"]
            recent = self.turns[-(self.max_turns - len(system_turns)):]
            self.turns = system_turns + recent

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": t.role, "content": t.content} for t in self.turns]


@dataclass
class AIContext:
    """Aggregated context passed to AI engines."""
    workspace: WorkspaceContext = field(default_factory=WorkspaceContext)
    site: SiteContext = field(default_factory=SiteContext)
    brand: BrandContext = field(default_factory=BrandContext)
    competitors: CompetitorContext = field(default_factory=CompetitorContext)
    recommendations: RecommendationContext = field(default_factory=RecommendationContext)
    conversation: ConversationContext = field(default_factory=ConversationContext)

    def to_system_context(self) -> str:
        """Render context as a system prompt section."""
        parts = []

        if self.workspace.workspace_name:
            parts.append(f"Workspace: {self.workspace.workspace_name}")
            parts.append(f"Autonomy Level: {self.workspace.autonomy_level}")

        if self.site.url:
            parts.append(f"\nSite: {self.site.url}")
            parts.append(f"Pages: {self.site.page_count}")
            if self.site.last_crawl_date:
                parts.append(f"Last Crawl: {self.site.last_crawl_date}")

        if self.brand.brand_name:
            parts.append(f"\nBrand: {self.brand.brand_name}")
            if self.brand.brand_voice:
                parts.append(f"Voice: {self.brand.brand_voice}")
            if self.brand.target_audience:
                parts.append(f"Target Audience: {self.brand.target_audience}")

        if self.competitors.competitors:
            comp_names = [c.get("name", c.get("url", "unknown")) for c in self.competitors.competitors[:5]]
            parts.append(f"\nKey Competitors: {', '.join(comp_names)}")

        if self.recommendations.active_recommendations:
            parts.append(f"\nActive Recommendations: {len(self.recommendations.active_recommendations)}")

        return "\n".join(parts) if parts else ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for prompt injection."""
        return {
            "workspace_name": self.workspace.workspace_name,
            "workspace_id": self.workspace.workspace_id,
            "autonomy_level": str(self.workspace.autonomy_level),
            "site_url": self.site.url,
            "site_id": self.site.site_id,
            "brand_name": self.brand.brand_name,
            "brand_voice": self.brand.brand_voice,
            "target_audience": self.brand.target_audience,
        }


class ContextManager:
    """
    Manages context assembly for AI operations.

    In production, this loads context from the database.
    Currently provides a structured interface with in-memory defaults.
    """

    def __init__(self) -> None:
        self._contexts: dict[str, AIContext] = {}

    async def get_context(
        self,
        workspace_id: str,
        site_id: Optional[str] = None,
    ) -> AIContext:
        """Assemble context for an AI operation."""
        cache_key = f"{workspace_id}:{site_id or 'none'}"
        if cache_key in self._contexts:
            return self._contexts[cache_key]

        # In production: load from DB
        # For now: return a structured empty context
        ctx = AIContext(
            workspace=WorkspaceContext(workspace_id=workspace_id),
            site=SiteContext(site_id=site_id or ""),
        )
        self._contexts[cache_key] = ctx
        return ctx

    async def update_workspace_context(self, workspace_id: str, **updates: Any) -> None:
        for key, contexts in self._contexts.items():
            if key.startswith(f"{workspace_id}:"):
                for k, v in updates.items():
                    if hasattr(contexts.workspace, k):
                        setattr(contexts.workspace, k, v)

    async def update_site_context(self, site_id: str, **updates: Any) -> None:
        for key, contexts in self._contexts.items():
            if contexts.site.site_id == site_id:
                for k, v in updates.items():
                    if hasattr(contexts.site, k):
                        setattr(contexts.site, k, v)

    def clear_cache(self, workspace_id: Optional[str] = None) -> None:
        if workspace_id:
            self._contexts = {
                k: v for k, v in self._contexts.items()
                if not k.startswith(f"{workspace_id}:")
            }
        else:
            self._contexts.clear()


# Singleton
_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    global _manager
    if _manager is None:
        _manager = ContextManager()
    return _manager
