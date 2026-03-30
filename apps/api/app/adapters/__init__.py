"""
Official Ads Platform Adapter Architecture.

Each adapter implements the BaseAdsAdapter interface and handles:
  - Authentication (OAuth2 / API key)
  - Campaign CRUD
  - Audience CRUD
  - Creative CRUD
  - Budget management
  - Reporting pull
  - Error mapping
  - Rate-limit handling
  - Audit logging

Staged capability model:
  Stage A: PLANNING       — intelligence only, no API calls
  Stage B: READ_REPORT    — pull metrics and account structure
  Stage C: DRAFT_CREATE   — create campaigns in PAUSED/DRAFT state
  Stage D: APPROVAL_GATE  — human review required before publish
  Stage E: LIVE_OPTIMIZE  — automated bid/budget optimization loops
"""

from app.adapters.base import BaseAdsAdapter, AdapterCapabilityStage, AdapterStatus
from app.adapters.meta import MetaAdsAdapter
from app.adapters.google import GoogleAdsAdapter
from app.adapters.tiktok import TikTokAdsAdapter
from app.adapters.linkedin import LinkedInAdsAdapter
from app.adapters.pinterest import PinterestAdsAdapter
from app.adapters.snap import SnapAdsAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdsAdapter]] = {
    "meta": MetaAdsAdapter,
    "google": GoogleAdsAdapter,
    "tiktok": TikTokAdsAdapter,
    "linkedin": LinkedInAdsAdapter,
    "pinterest": PinterestAdsAdapter,
    "snap": SnapAdsAdapter,
}

__all__ = [
    "BaseAdsAdapter",
    "AdapterCapabilityStage",
    "AdapterStatus",
    "MetaAdsAdapter",
    "GoogleAdsAdapter",
    "TikTokAdsAdapter",
    "LinkedInAdsAdapter",
    "PinterestAdsAdapter",
    "SnapAdsAdapter",
    "ADAPTER_REGISTRY",
]
