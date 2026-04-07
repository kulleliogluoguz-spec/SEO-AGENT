"""Ads platform integrations — Meta Ads (Marketing API) and Google Ads."""

from app.services.ads.google_ads import GoogleAdsService
from app.services.ads.meta_ads import MetaAdsService

__all__ = ["MetaAdsService", "GoogleAdsService"]
