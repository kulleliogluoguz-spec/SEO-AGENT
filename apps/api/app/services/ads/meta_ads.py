"""
Meta Ads Service — Facebook Marketing API v20.0

Supports:
  - Campaign creation (TRAFFIC, CONVERSIONS, BRAND_AWARENESS, LEAD_GENERATION)
  - Ad Set creation with targeting
  - Ad Creative generation from text angles
  - Ad creation and launch
  - Campaign insights ingestion
  - Budget reallocation
  - Campaign pause / resume

Reference: https://developers.facebook.com/docs/marketing-apis

Authentication:
  Long-lived User Access Token stored in credential_store under platform="meta"
  Must have: ads_management, ads_read, business_management scopes
  Ad account ID stored in linked_accounts under platform="meta_ads"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.core.store.credential_store import get_credential, get_linked_accounts
from app.core.store.audit_store import write_audit_event

logger = logging.getLogger(__name__)

META_GRAPH_BASE = "https://graph.facebook.com/v20.0"

# Meta Ads objective mapping (Marketing API names)
OBJECTIVE_MAP = {
    "traffic": "OUTCOME_TRAFFIC",
    "conversions": "OUTCOME_SALES",
    "awareness": "OUTCOME_AWARENESS",
    "leads": "OUTCOME_LEADS",
    "engagement": "OUTCOME_ENGAGEMENT",
    "app_installs": "OUTCOME_APP_PROMOTION",
}

# Billing event by objective
BILLING_EVENT_MAP = {
    "OUTCOME_TRAFFIC": "IMPRESSIONS",
    "OUTCOME_SALES": "IMPRESSIONS",
    "OUTCOME_AWARENESS": "IMPRESSIONS",
    "OUTCOME_LEADS": "IMPRESSIONS",
    "OUTCOME_ENGAGEMENT": "POST_ENGAGEMENT",
    "OUTCOME_APP_PROMOTION": "IMPRESSIONS",
}


@dataclass
class MetaAdsResult:
    success: bool
    campaign_id: Optional[str] = None
    ad_set_id: Optional[str] = None
    ad_id: Optional[str] = None
    creative_id: Optional[str] = None
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)


class MetaAdsService:
    """
    Full Meta Ads campaign lifecycle management.

    Usage:
        service = MetaAdsService(user_id="user-123")
        result = await service.create_campaign(
            name="Summer Traffic Campaign",
            objective="traffic",
            daily_budget_usd=10.0,
            landing_page_url="https://example.com/landing",
            headline="Try Our Product",
            description="Sign up today",
            age_min=25, age_max=55,
        )
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._token: Optional[str] = None
        self._ad_account_id: Optional[str] = None

    def _load_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Return (access_token, ad_account_id) or (None, None) if not configured."""
        cred = get_credential(self.user_id, "meta")
        if not cred:
            return None, None

        token = cred.get("access_token", "")
        if not token:
            return None, None

        # Get the primary linked ad account
        accounts = get_linked_accounts(self.user_id, "meta_ads")
        if not accounts:
            # Try to extract from credential extra field
            extra = cred.get("extra", {})
            ad_accounts = extra.get("ad_accounts", [])
            if ad_accounts:
                account_id = ad_accounts[0]["account_id"]
            else:
                return token, None
        else:
            account_id = accounts[0]["account_id"]

        # Ensure act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        return token, account_id

    async def _api(
        self,
        method: str,
        path: str,
        token: str,
        **kwargs,
    ) -> dict:
        """Make authenticated Meta Graph API call."""
        url = f"{META_GRAPH_BASE}/{path.lstrip('/')}"
        # Always inject access_token
        if "params" not in kwargs:
            kwargs["params"] = {}
        kwargs["params"]["access_token"] = token

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await getattr(client, method.lower())(url, **kwargs)

        if resp.status_code not in (200, 201):
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            error_msg = (
                error_data.get("error", {}).get("message")
                or error_data.get("error")
                or resp.text[:300]
            )
            raise RuntimeError(f"Meta API {resp.status_code}: {error_msg}")

        return resp.json()

    async def check_connection(self) -> dict:
        """Validate Meta credentials and return account info."""
        token, account_id = self._load_credentials()
        if not token:
            return {"connected": False, "reason": "No Meta credentials. Connect via Settings → Connections."}
        if not account_id:
            return {"connected": False, "reason": "No Meta Ads account linked. Complete Meta connection flow."}

        try:
            data = await self._api("GET", f"{account_id}", token, params={"fields": "id,name,currency,account_status"})
            status = data.get("account_status")
            if status == 1:
                return {"connected": True, "account_id": account_id, "account_name": data.get("name"), "currency": data.get("currency", "USD")}
            else:
                return {"connected": False, "reason": f"Ad account status {status} (not active)"}
        except Exception as e:
            return {"connected": False, "reason": str(e)}

    async def create_campaign(
        self,
        *,
        name: str,
        objective: str,
        daily_budget_usd: float,
        landing_page_url: str,
        headline: str,
        description: str,
        age_min: int = 18,
        age_max: int = 65,
        geo_locations: Optional[list[str]] = None,
        interests: Optional[list[str]] = None,
        campaign_user_id: Optional[str] = None,
    ) -> MetaAdsResult:
        """
        Full campaign launch: creates Campaign → Ad Set → Creative → Ad.
        Returns MetaAdsResult with all IDs. The campaign starts in PAUSED state
        for safety; caller can activate via activate_campaign().
        """
        token, account_id = self._load_credentials()
        if not token or not account_id:
            result = MetaAdsResult(
                success=False,
                error="Meta Ads not connected. Go to Connections and link your Meta Ads account."
            )
            write_audit_event(
                user_id=self.user_id, action="ads.meta.create_campaign",
                channel="meta_ads", success=False,
                metadata={"error": result.error, "campaign_name": name},
            )
            return result

        meta_objective = OBJECTIVE_MAP.get(objective.lower(), "OUTCOME_TRAFFIC")
        billing_event = BILLING_EVENT_MAP.get(meta_objective, "IMPRESSIONS")
        daily_budget_cents = int(daily_budget_usd * 100)

        campaign_id = ad_set_id = creative_id = ad_id = None

        try:
            # Step 1: Create Campaign
            camp_data = await self._api(
                "POST", f"{account_id}/campaigns", token,
                json={
                    "name": name,
                    "objective": meta_objective,
                    "status": "PAUSED",
                    "special_ad_categories": [],
                },
            )
            campaign_id = camp_data.get("id")
            logger.info("[meta_ads] campaign created: %s", campaign_id)

            # Step 2: Create Ad Set with targeting
            targeting: dict = {
                "age_min": age_min,
                "age_max": age_max,
                "geo_locations": {
                    "countries": geo_locations or ["US"],
                },
            }
            if interests:
                # interests should be Facebook interest IDs or names
                targeting["flexible_spec"] = [
                    {"interests": [{"name": i} for i in interests[:5]]}
                ]

            ad_set_data = await self._api(
                "POST", f"{account_id}/adsets", token,
                json={
                    "name": f"{name} — Ad Set",
                    "campaign_id": campaign_id,
                    "daily_budget": daily_budget_cents,
                    "billing_event": billing_event,
                    "optimization_goal": "LINK_CLICKS" if meta_objective == "OUTCOME_TRAFFIC" else "OFFSITE_CONVERSIONS",
                    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    "targeting": targeting,
                    "status": "PAUSED",
                    "destination_type": "WEBSITE",
                },
            )
            ad_set_id = ad_set_data.get("id")
            logger.info("[meta_ads] ad set created: %s", ad_set_id)

            # Step 3: Create Ad Creative (link ad)
            creative_data = await self._api(
                "POST", f"{account_id}/adcreatives", token,
                json={
                    "name": f"{name} — Creative",
                    "object_story_spec": {
                        "link_data": {
                            "link": landing_page_url,
                            "message": description,
                            "name": headline,
                            "call_to_action": {
                                "type": "LEARN_MORE",
                                "value": {"link": landing_page_url},
                            },
                        },
                        "page_id": await self._get_page_id(token),
                    },
                },
            )
            creative_id = creative_data.get("id")
            logger.info("[meta_ads] creative created: %s", creative_id)

            # Step 4: Create Ad
            ad_data = await self._api(
                "POST", f"{account_id}/ads", token,
                json={
                    "name": f"{name} — Ad",
                    "adset_id": ad_set_id,
                    "creative": {"creative_id": creative_id},
                    "status": "PAUSED",
                },
            )
            ad_id = ad_data.get("id")
            logger.info("[meta_ads] ad created: %s", ad_id)

        except Exception as e:
            logger.error("[meta_ads] create_campaign failed: %s", e)
            write_audit_event(
                user_id=self.user_id, action="ads.meta.create_campaign",
                channel="meta_ads", success=False,
                metadata={"error": str(e), "campaign_id": campaign_id},
            )
            return MetaAdsResult(success=False, error=str(e), campaign_id=campaign_id)

        write_audit_event(
            user_id=self.user_id, action="ads.meta.create_campaign",
            channel="meta_ads", success=True,
            metadata={
                "campaign_id": campaign_id,
                "ad_set_id": ad_set_id,
                "creative_id": creative_id,
                "ad_id": ad_id,
                "budget_usd": daily_budget_usd,
                "objective": objective,
            },
        )

        return MetaAdsResult(
            success=True,
            campaign_id=campaign_id,
            ad_set_id=ad_set_id,
            creative_id=creative_id,
            ad_id=ad_id,
        )

    async def activate_campaign(self, campaign_id: str) -> bool:
        """Set campaign status to ACTIVE (starts spending)."""
        token, _ = self._load_credentials()
        if not token:
            return False
        try:
            await self._api("POST", f"{campaign_id}", token, json={"status": "ACTIVE"})
            write_audit_event(
                user_id=self.user_id, action="ads.meta.activate_campaign",
                channel="meta_ads", success=True,
                metadata={"campaign_id": campaign_id},
            )
            return True
        except Exception as e:
            logger.error("[meta_ads] activate_campaign failed: %s", e)
            return False

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a running campaign."""
        token, _ = self._load_credentials()
        if not token:
            return False
        try:
            await self._api("POST", f"{campaign_id}", token, json={"status": "PAUSED"})
            write_audit_event(
                user_id=self.user_id, action="ads.meta.pause_campaign",
                channel="meta_ads", success=True,
                metadata={"campaign_id": campaign_id},
            )
            return True
        except Exception as e:
            logger.error("[meta_ads] pause_campaign failed: %s", e)
            return False

    async def get_campaign_insights(
        self,
        campaign_id: str,
        date_preset: str = "last_7d",
    ) -> Optional[dict]:
        """
        Fetch campaign performance metrics.
        date_preset options: today, yesterday, last_7d, last_30d, this_month
        """
        token, _ = self._load_credentials()
        if not token:
            return None
        try:
            data = await self._api(
                "GET",
                f"{campaign_id}/insights",
                token,
                params={
                    "date_preset": date_preset,
                    "fields": "impressions,clicks,spend,cpc,ctr,reach,frequency,actions",
                },
            )
            insights = data.get("data", [{}])[0] if data.get("data") else {}
            actions = {a["action_type"]: int(a["value"]) for a in insights.get("actions", [])}
            return {
                "campaign_id": campaign_id,
                "impressions": int(insights.get("impressions", 0)),
                "clicks": int(insights.get("clicks", 0)),
                "spend_usd": float(insights.get("spend", 0)),
                "cpc": float(insights.get("cpc", 0)),
                "ctr": float(insights.get("ctr", 0)),
                "reach": int(insights.get("reach", 0)),
                "link_clicks": actions.get("link_click", 0),
                "landing_page_views": actions.get("landing_page_view", 0),
                "date_preset": date_preset,
            }
        except Exception as e:
            logger.debug("[meta_ads] get_insights failed: %s", e)
            return None

    async def update_daily_budget(self, ad_set_id: str, new_budget_usd: float) -> bool:
        """Update the daily budget of an ad set (budget reallocation)."""
        token, _ = self._load_credentials()
        if not token:
            return False
        try:
            await self._api(
                "POST", f"{ad_set_id}", token,
                json={"daily_budget": int(new_budget_usd * 100)},
            )
            write_audit_event(
                user_id=self.user_id, action="ads.meta.update_budget",
                channel="meta_ads", success=True,
                metadata={"ad_set_id": ad_set_id, "new_budget_usd": new_budget_usd},
            )
            return True
        except Exception as e:
            logger.error("[meta_ads] update_budget failed: %s", e)
            return False

    async def _get_page_id(self, token: str) -> str:
        """Get the first available Facebook Page ID for creative creation."""
        cred = get_credential(self.user_id, "meta")
        if cred:
            pages = cred.get("extra", {}).get("pages", [])
            if pages:
                return pages[0].get("page_id", "")
        # Fallback: fetch pages
        try:
            data = await self._api("GET", "me/accounts", token, params={"limit": 1})
            pages = data.get("data", [])
            if pages:
                return pages[0]["id"]
        except Exception:
            pass
        return ""
