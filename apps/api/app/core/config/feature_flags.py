"""
Feature Flag System — simple, explicit, settings-backed.

Flags are read from settings (env vars). No runtime mutation, no remote config.
For production feature management, replace with LaunchDarkly or equivalent.

Usage:
    from app.core.config.feature_flags import flags

    if flags.geo_agent_enabled:
        # run GEO analysis
"""
from functools import lru_cache
from app.core.config.settings import get_settings


class FeatureFlags:
    """
    Reads feature flags from application settings.
    Designed to be extended with remote feature flag providers.
    """

    def __init__(self) -> None:
        self._s = get_settings()

    # ─── AI / Agent Features ─────────────────────────────────────────────
    @property
    def geo_agent_enabled(self) -> bool:
        """GEO/AEO AI visibility analysis (experimental)."""
        return self._s.feature_geo_agent

    @property
    def experiments_enabled(self) -> bool:
        """Experiment hypothesis and variant generation."""
        return self._s.feature_experiments

    # ─── Publishing Features ─────────────────────────────────────────────
    @property
    def social_publishing_enabled(self) -> bool:
        """
        Social media publishing connectors.
        DISABLED BY DEFAULT — requires explicit human review + approval.
        Enabling this does NOT bypass the approval queue.
        """
        return self._s.feature_social_publishing

    @property
    def cms_publishing_enabled(self) -> bool:
        """CMS publishing connectors (WordPress, Webflow, etc.)."""
        return self._s.feature_cms_publishing

    # ─── Analytics ───────────────────────────────────────────────────────
    @property
    def advanced_analytics_enabled(self) -> bool:
        """Advanced analytics features (cohort analysis, attribution)."""
        return self._s.feature_advanced_analytics

    # ─── Safety Checks ───────────────────────────────────────────────────
    @property
    def autonomy_level(self) -> int:
        """Current workspace autonomy level."""
        return self._s.autonomy_default_level

    @property
    def auto_publish_allowed(self) -> bool:
        """Whether any auto-publishing is permitted at current autonomy level."""
        return self._s.autonomy_default_level >= 3

    def describe(self) -> dict[str, bool]:
        """Return all flags as a dictionary for admin/health endpoints."""
        return {
            "geo_agent": self.geo_agent_enabled,
            "experiments": self.experiments_enabled,
            "social_publishing": self.social_publishing_enabled,
            "cms_publishing": self.cms_publishing_enabled,
            "advanced_analytics": self.advanced_analytics_enabled,
            "auto_publish_allowed": self.auto_publish_allowed,
        }


@lru_cache
def get_flags() -> FeatureFlags:
    """Return cached FeatureFlags instance."""
    return FeatureFlags()


# Module-level convenience
flags = get_flags()
