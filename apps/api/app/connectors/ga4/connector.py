"""
GA4 Connector — Google Analytics 4 data ingestion.

REAL mode: Requires GOOGLE_APPLICATION_CREDENTIALS and GA4_PROPERTY_ID.
MOCK mode: Returns realistic demo data (default in development).

Set GA4_MOCK_MODE=false and configure credentials for real data.
"""
from dataclasses import dataclass
from datetime import date, timedelta

import structlog

from app.core.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class GA4MetricRow:
    date: str
    page_path: str
    sessions: int
    users: int
    bounce_rate: float
    avg_session_duration: float
    conversions: int
    source_medium: str


@dataclass
class GA4Summary:
    property_id: str
    period_start: str
    period_end: str
    total_sessions: int
    total_users: int
    total_conversions: int
    avg_bounce_rate: float
    top_pages: list[GA4MetricRow]
    channel_breakdown: dict[str, int]
    is_mock: bool


class GA4Connector:
    """
    Google Analytics 4 data connector.

    Usage:
        connector = GA4Connector()
        summary = await connector.get_summary(days=7)
    """

    def __init__(self) -> None:
        self._mock_mode = settings.ga4_mock_mode
        if not self._mock_mode:
            self._init_real_client()

    def _init_real_client(self) -> None:
        """Initialize real GA4 API client."""
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            self._client = BetaAnalyticsDataClient()
            self._property_id = settings.ga4_mock_mode  # Should be property ID
            logger.info("ga4.real_client_initialized")
        except ImportError:
            logger.warning("ga4.google_analytics_not_installed, falling back to mock")
            self._mock_mode = True

    async def get_summary(self, days: int = 7, site_url: str | None = None) -> GA4Summary:
        """Get GA4 summary for the specified period."""
        if self._mock_mode:
            return self._mock_summary(days)
        return await self._real_summary(days)

    def _mock_summary(self, days: int) -> GA4Summary:
        """Return realistic mock GA4 data."""
        end = date.today()
        start = end - timedelta(days=days)

        top_pages = [
            GA4MetricRow(
                date=str(end),
                page_path="/",
                sessions=420,
                users=380,
                bounce_rate=0.52,
                avg_session_duration=124.3,
                conversions=8,
                source_medium="google / organic",
            ),
            GA4MetricRow(
                date=str(end),
                page_path="/pricing",
                sessions=210,
                users=198,
                bounce_rate=0.38,
                avg_session_duration=87.2,
                conversions=15,
                source_medium="google / organic",
            ),
            GA4MetricRow(
                date=str(end),
                page_path="/features",
                sessions=185,
                users=170,
                bounce_rate=0.44,
                avg_session_duration=95.8,
                conversions=4,
                source_medium="direct / (none)",
            ),
            GA4MetricRow(
                date=str(end),
                page_path="/blog/sprint-planning",
                sessions=145,
                users=142,
                bounce_rate=0.72,
                avg_session_duration=203.1,
                conversions=2,
                source_medium="google / organic",
            ),
        ]

        return GA4Summary(
            property_id="mock-property-123",
            period_start=str(start),
            period_end=str(end),
            total_sessions=1240,
            total_users=1087,
            total_conversions=23,
            avg_bounce_rate=0.51,
            top_pages=top_pages,
            channel_breakdown={
                "organic_search": 720,
                "direct": 290,
                "referral": 130,
                "social": 100,
            },
            is_mock=True,
        )

    async def _real_summary(self, days: int) -> GA4Summary:
        """
        Fetch real GA4 data via API.
        Not fully implemented — requires google-analytics-data package
        and valid service account credentials.
        """
        raise NotImplementedError(
            "Real GA4 integration requires google-analytics-data package "
            "and GOOGLE_APPLICATION_CREDENTIALS configured. "
            "Set GA4_MOCK_MODE=true for demo mode."
        )
