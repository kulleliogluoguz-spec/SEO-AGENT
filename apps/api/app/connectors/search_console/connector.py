"""
Google Search Console Connector.

REAL mode: Requires google-auth and Search Console API access.
MOCK mode: Returns realistic demo data (default in development).
"""
from dataclasses import dataclass
from datetime import date, timedelta

import structlog

from app.core.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class GSCQueryRow:
    query: str
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


@dataclass
class GSCSummary:
    site_url: str
    period_start: str
    period_end: str
    total_clicks: int
    total_impressions: int
    avg_ctr: float
    avg_position: float
    top_queries: list[GSCQueryRow]
    top_pages: list[dict]
    opportunity_queries: list[GSCQueryRow]  # High impressions, low CTR
    is_mock: bool


class SearchConsoleConnector:
    """Google Search Console data connector."""

    def __init__(self) -> None:
        self._mock_mode = settings.gsc_mock_mode

    async def get_summary(self, site_url: str, days: int = 28) -> GSCSummary:
        """Get Search Console summary."""
        if self._mock_mode:
            return self._mock_summary(site_url, days)
        return await self._real_summary(site_url, days)

    def _mock_summary(self, site_url: str, days: int) -> GSCSummary:
        end = date.today()
        start = end - timedelta(days=days)

        top_queries = [
            GSCQueryRow("project management software", f"{site_url}/", 124, 3200, 0.039, 8.2),
            GSCQueryRow("sprint planning tool", f"{site_url}/features", 89, 1800, 0.049, 6.4),
            GSCQueryRow("agile project tracking", f"{site_url}/", 67, 2100, 0.032, 11.3),
            GSCQueryRow("engineering team software", f"{site_url}/features", 45, 980, 0.046, 5.8),
            GSCQueryRow("software delivery tracking", f"{site_url}/features", 38, 760, 0.050, 7.1),
        ]

        # High impressions, low CTR = opportunities to improve title/meta
        opportunity_queries = [
            GSCQueryRow("best project management tools 2025", f"{site_url}/", 4, 1200, 0.003, 14.2),
            GSCQueryRow("jira alternative for small teams", f"{site_url}/", 6, 890, 0.007, 12.8),
            GSCQueryRow("asana vs monday comparison", f"{site_url}/pricing", 2, 650, 0.003, 18.4),
        ]

        return GSCSummary(
            site_url=site_url,
            period_start=str(start),
            period_end=str(end),
            total_clicks=1180,
            total_impressions=45200,
            avg_ctr=0.026,
            avg_position=18.4,
            top_queries=top_queries,
            top_pages=[
                {"page": f"{site_url}/", "clicks": 380, "impressions": 12400},
                {"page": f"{site_url}/features", "clicks": 290, "impressions": 8900},
                {"page": f"{site_url}/pricing", "clicks": 210, "impressions": 6200},
            ],
            opportunity_queries=opportunity_queries,
            is_mock=True,
        )

    async def _real_summary(self, site_url: str, days: int) -> GSCSummary:
        raise NotImplementedError(
            "Real GSC integration requires google-auth package and Search Console API access. "
            "Set GSC_MOCK_MODE=true for demo mode."
        )
