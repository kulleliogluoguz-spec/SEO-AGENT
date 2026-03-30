"""
Ads Platform Connector endpoints.

GET  /api/v1/ads-connectors              — list all platform statuses for current workspace
GET  /api/v1/ads-connectors/{platform}   — get capability summary for one platform
POST /api/v1/ads-connectors/{platform}/auth-url  — get OAuth2 authorization URL
POST /api/v1/ads-connectors/{platform}/connect   — exchange code, save credentials
GET  /api/v1/ads-connectors/{platform}/accounts  — list accessible ad accounts
POST /api/v1/ads-connectors/{platform}/link-account — link a specific ad account

All writes are gated. No campaigns are created or published from these endpoints.
Campaign creation lives under /api/v1/campaigns (future).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.api.dependencies.auth import get_current_user
from app.adapters.base import AdapterCapabilityStage, AdapterCredentials, AdapterStatus
from app.adapters import ADAPTER_REGISTRY
from app.core.store.credential_store import (
    store_credential, get_credential, delete_credential, list_credentials,
    link_account, get_linked_accounts, unlink_account, get_platform_stage,
)

router = APIRouter()

# ── Platform metadata ─────────────────────────────────────────────────────────

PLATFORM_META = {
    "meta": {
        "name": "Meta (Facebook + Instagram)",
        "description": "Run ads on Facebook Feed, Instagram Feed, Reels, Stories, and Audience Network.",
        "icon": "meta",
        "best_for": ["ecommerce", "fashion", "beauty", "fitness", "food", "general"],
        "ad_formats": ["Image", "Video", "Carousel", "Stories", "Reels", "Collection", "Dynamic Product"],
        "min_daily_budget_usd": 1.0,
        "docs_url": "https://developers.facebook.com/docs/marketing-apis",
        "app_review_required": True,
        "app_review_note": "ads_management scope requires Meta App Review approval (1–5 business days).",
    },
    "google": {
        "name": "Google Ads",
        "description": "Search, Display, YouTube, Shopping, Performance Max, and Demand Gen campaigns.",
        "icon": "google",
        "best_for": ["tech", "b2b", "ecommerce", "travel", "fitness"],
        "ad_formats": ["Text (RSA)", "Display", "Video (YouTube)", "Shopping", "Performance Max"],
        "min_daily_budget_usd": 1.0,
        "docs_url": "https://developers.google.com/google-ads/api/docs/start",
        "app_review_required": True,
        "app_review_note": "Developer token requires Google approval. Basic access granted automatically; standard access requires application.",
    },
    "tiktok": {
        "name": "TikTok for Business",
        "description": "In-Feed Video, Spark Ads, TopView, and Branded Hashtag Challenges.",
        "icon": "tiktok",
        "best_for": ["fashion", "beauty", "fitness", "food", "creator", "ecommerce"],
        "ad_formats": ["In-Feed Video", "Spark Ads", "TopView", "Brand Takeover", "Hashtag Challenge"],
        "min_daily_budget_usd": 20.0,
        "docs_url": "https://ads.tiktok.com/marketing_api/docs",
        "app_review_required": True,
        "app_review_note": "TikTok for Business developer account required. App review typically 3–7 business days.",
    },
    "linkedin": {
        "name": "LinkedIn Marketing Solutions",
        "description": "Sponsored Content, Message Ads, Lead Gen Forms, and Dynamic Ads for B2B.",
        "icon": "linkedin",
        "best_for": ["b2b", "tech"],
        "ad_formats": ["Sponsored Content", "Message Ads", "Lead Gen Forms", "Dynamic Ads", "Text Ads"],
        "min_daily_budget_usd": 10.0,
        "docs_url": "https://learn.microsoft.com/en-us/linkedin/marketing/",
        "app_review_required": True,
        "app_review_note": "Marketing Developer Platform (MDP) access requires LinkedIn application review (1–4 weeks).",
    },
    "pinterest": {
        "name": "Pinterest Ads",
        "description": "Promoted Pins, Shopping Pins, Video Pins for discovery-mode and high-intent audiences.",
        "icon": "pinterest",
        "best_for": ["fashion", "beauty", "food", "travel", "ecommerce"],
        "ad_formats": ["Standard Pin", "Video Pin", "Shopping Pin", "Collection", "Idea Pin"],
        "min_daily_budget_usd": 2.0,
        "docs_url": "https://developers.pinterest.com/docs/api/v5/",
        "app_review_required": False,
        "app_review_note": "Pinterest API v5 available with business account. No extended review required for ads:read/write.",
    },
    "snap": {
        "name": "Snapchat Ads",
        "description": "Story Ads, Single Video, Collection Ads, AR Lenses for Gen Z audiences.",
        "icon": "snap",
        "best_for": ["fashion", "beauty", "creator", "ecommerce"],
        "ad_formats": ["Single Video", "Story Ads", "Collection", "AR Lens", "Filter"],
        "min_daily_budget_usd": 5.0,
        "docs_url": "https://marketingapi.snapchat.com/docs/",
        "app_review_required": True,
        "app_review_note": "Snap Business account + developer application required. Review typically 2–5 business days.",
    },
}

# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthUrlRequest(BaseModel):
    redirect_uri: str
    state: str = "default"


class ConnectRequest(BaseModel):
    """Exchange OAuth2 authorization code for access token."""
    code: str
    redirect_uri: str


class TokenDirectRequest(BaseModel):
    """For platforms that support direct token input (e.g. long-lived tokens)."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None
    scope: Optional[str] = None


class LinkAccountRequest(BaseModel):
    account_id: str
    account_name: str = "My Ad Account"
    currency: str = "USD"
    timezone: str = "UTC"


class DisconnectRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to disconnect")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _planning_adapter(platform: str):
    """Return a planning-only adapter instance (no credentials required)."""
    if platform not in ADAPTER_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")
    cls = ADAPTER_REGISTRY[platform]
    creds = AdapterCredentials(platform=platform)
    return cls(credentials=creds, stage=AdapterCapabilityStage.PLANNING)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_connectors(current_user=Depends(get_current_user)) -> dict:
    """
    List all supported ad platforms with their current connection status,
    capability stage, and platform metadata.
    """
    user_id = str(current_user.id)
    user_creds = {c["platform"]: c for c in list_credentials(user_id)}
    user_accounts = {}
    for acct in get_linked_accounts(user_id):
        user_accounts.setdefault(acct["platform"], []).append(acct)

    platforms = []
    connected_count = 0
    for key, meta in PLATFORM_META.items():
        adapter = _planning_adapter(key)
        capability = adapter.capability_summary()
        real_stage = get_platform_stage(user_id, key)

        # Override stage from credential store if more advanced
        stage_order = ["planning", "credentials_set", "auth_verified", "account_linked"]
        if real_stage in stage_order and stage_order.index(real_stage) > stage_order.index(capability["stage"]):
            display_stage = real_stage
        else:
            display_stage = capability["stage"]

        is_connected = real_stage == "account_linked"
        if is_connected:
            connected_count += 1

        platforms.append({
            "platform": key,
            "name": meta["name"],
            "description": meta["description"],
            "icon": meta["icon"],
            "best_for": meta["best_for"],
            "ad_formats": meta["ad_formats"],
            "min_daily_budget_usd": meta["min_daily_budget_usd"],
            "docs_url": meta["docs_url"],
            "app_review_required": meta["app_review_required"],
            "app_review_note": meta["app_review_note"],
            "stage": display_stage,
            "is_connected": is_connected,
            "linked_accounts": user_accounts.get(key, []),
            "can_read": is_connected or real_stage == "auth_verified",
            "can_create_drafts": is_connected,
            "can_publish": False,  # always requires approval
            "requires_approval_to_publish": True,
            "next_step": capability["next_step"] if not is_connected else "Ready to create campaign drafts.",
            "required_scopes": capability["required_scopes"],
        })
    return {
        "platforms": platforms,
        "total": len(platforms),
        "connected": connected_count,
        "planning_only": len(platforms) - connected_count,
    }


@router.get("/{platform}")
async def get_connector(platform: str, current_user=Depends(get_current_user)) -> dict:
    """Get full capability summary and metadata for a specific ad platform."""
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")
    adapter = _planning_adapter(platform)
    meta = PLATFORM_META[platform]
    return {
        **meta,
        **adapter.capability_summary(),
        "setup_steps": _setup_steps(platform),
    }


@router.post("/{platform}/auth-url")
async def get_auth_url(
    platform: str,
    payload: AuthUrlRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Generate the OAuth2 authorization URL for a platform.
    Redirect the user's browser to this URL to begin the auth flow.

    Note: client_id must be configured in server environment variables.
    """
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")

    import os
    client_id = os.getenv(f"{platform.upper()}_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=422,
            detail=f"{platform.upper()}_CLIENT_ID is not set in environment. "
                   f"Add your {PLATFORM_META[platform]['name']} app credentials to the server .env file.",
        )

    cls = ADAPTER_REGISTRY[platform]
    creds = AdapterCredentials(platform=platform, client_id=client_id)
    adapter = cls(credentials=creds, stage=AdapterCapabilityStage.READ_REPORT)
    url = adapter.get_auth_url(redirect_uri=payload.redirect_uri, state=payload.state)

    return {
        "auth_url": url,
        "platform": platform,
        "redirect_uri": payload.redirect_uri,
        "scopes": ADAPTER_REGISTRY[platform].REQUIRED_SCOPES,
        "note": "Redirect the user to auth_url. After approval, exchange the returned code via POST /{platform}/connect.",
    }


@router.post("/{platform}/connect")
async def connect_platform(
    platform: str,
    payload: ConnectRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Exchange OAuth2 authorization code for access token and store credentials.

    After this call succeeds, the platform advances to READ_REPORT stage.
    Next step: GET /{platform}/accounts to list accessible ad accounts, then
    POST /{platform}/link-account to link a specific account.
    """
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")

    import os
    client_id = os.getenv(f"{platform.upper()}_CLIENT_ID")
    client_secret = os.getenv(f"{platform.upper()}_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"{PLATFORM_META[platform]['name']} OAuth credentials not configured on server.",
                "missing": [v for v in [f"{platform.upper()}_CLIENT_ID", f"{platform.upper()}_CLIENT_SECRET"] if not os.getenv(v)],
                "next_step": f"Add {platform.upper()}_CLIENT_ID and {platform.upper()}_CLIENT_SECRET to server .env file.",
            },
        )

    # Call platform adapter to exchange code
    try:
        cls = ADAPTER_REGISTRY[platform]
        creds = AdapterCredentials(platform=platform, client_id=client_id, client_secret=client_secret)
        adapter = cls(credentials=creds, stage=AdapterCapabilityStage.READ_REPORT)
        token_data = await adapter.exchange_code(code=payload.code, redirect_uri=payload.redirect_uri)
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail={
                "message": f"{PLATFORM_META[platform]['name']} token exchange not yet implemented in adapter.",
                "workaround": f"Use POST /{platform}/connect-token to provide a long-lived token directly.",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(exc)}")

    # Store credentials
    cred_record = store_credential(
        user_id=str(current_user.id),
        platform=platform,
        access_token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token"),
        expires_at=token_data.get("expires_at"),
        scope=token_data.get("scope"),
        extra={k: v for k, v in token_data.items() if k not in ("access_token", "refresh_token", "expires_at", "scope")},
    )

    return {
        "platform": platform,
        "stage": "auth_verified",
        "credential": cred_record,
        "message": f"{PLATFORM_META[platform]['name']} connected successfully. Next: GET /{platform}/accounts to list accessible ad accounts.",
        "next_step": f"GET /api/v1/ads-connectors/{platform}/accounts",
    }


@router.post("/{platform}/connect-token")
async def connect_platform_direct_token(
    platform: str,
    payload: TokenDirectRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Connect a platform using a long-lived access token provided directly.
    Use this when you already have a valid token (e.g. from the platform's UI).
    """
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")

    cred_record = store_credential(
        user_id=str(current_user.id),
        platform=platform,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        expires_at=payload.expires_at,
        scope=payload.scope,
    )
    return {
        "platform": platform,
        "stage": "auth_verified",
        "credential": cred_record,
        "message": f"{PLATFORM_META[platform]['name']} token stored. Next: GET /{platform}/accounts.",
        "next_step": f"GET /api/v1/ads-connectors/{platform}/accounts",
    }


@router.delete("/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Remove stored credentials for a platform. This is irreversible — you will need to re-auth."""
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")
    deleted = delete_credential(str(current_user.id), platform)
    if not deleted:
        raise HTTPException(404, f"No credentials found for platform '{platform}'.")
    return {"platform": platform, "message": f"{PLATFORM_META[platform]['name']} disconnected. Credentials removed."}


@router.get("/{platform}/accounts")
async def list_accounts(platform: str, current_user=Depends(get_current_user)) -> dict:
    """
    List accessible ad accounts for a connected platform.
    Requires the platform to be at auth_verified stage or higher.
    """
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")

    user_id = str(current_user.id)
    real_stage = get_platform_stage(user_id, platform)

    if real_stage == "planning":
        raise HTTPException(
            status_code=403,
            detail={
                "message": f"{PLATFORM_META[platform]['name']} is not connected.",
                "current_stage": "planning",
                "required_stage": "auth_verified",
                "next_step": f"POST /api/v1/ads-connectors/{platform}/auth-url to begin OAuth flow.",
            },
        )

    # Return already-linked accounts
    linked = get_linked_accounts(user_id, platform)

    # If we have credentials, attempt to fetch live accounts from adapter
    cred = get_credential(user_id, platform)
    live_accounts: list[dict] = []
    if cred:
        try:
            cls = ADAPTER_REGISTRY[platform]
            adapter_creds = AdapterCredentials(
                platform=platform,
                access_token=cred.get("access_token", ""),
                refresh_token=cred.get("refresh_token"),
                account_id=cred.get("extra", {}).get("account_id"),
            )
            adapter = cls(credentials=adapter_creds, stage=AdapterCapabilityStage.READ_REPORT)
            live_accounts = await adapter.list_accounts()
        except (NotImplementedError, Exception):
            live_accounts = []

    return {
        "platform": platform,
        "stage": real_stage,
        "linked_accounts": linked,
        "available_accounts": live_accounts,
        "note": "Use POST /{platform}/link-account to link one of the available accounts.",
    }


@router.post("/{platform}/link-account")
async def link_ad_account(
    platform: str,
    payload: LinkAccountRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Link a specific ad account to this workspace.

    After linking, the platform advances to ACCOUNT_LINKED stage and
    campaign draft creation becomes available.
    """
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")

    user_id = str(current_user.id)
    stage = get_platform_stage(user_id, platform)
    if stage == "planning":
        raise HTTPException(
            403,
            detail={
                "message": f"Must connect {PLATFORM_META[platform]['name']} before linking an account.",
                "next_step": f"POST /api/v1/ads-connectors/{platform}/auth-url",
            },
        )

    record = link_account(
        user_id=user_id,
        platform=platform,
        account_id=payload.account_id,
        account_name=payload.account_name,
        currency=payload.currency,
        timezone_name=payload.timezone,
    )
    return {
        "platform": platform,
        "stage": "account_linked",
        "linked_account": record,
        "message": f"Account '{payload.account_name}' linked successfully. You can now create campaign drafts.",
        "next_step": "POST /api/v1/campaigns/drafts to create your first campaign draft.",
    }


@router.delete("/{platform}/accounts/{account_id}")
async def unlink_ad_account(
    platform: str,
    account_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Unlink a specific ad account from this workspace."""
    if platform not in PLATFORM_META:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported.")
    removed = unlink_account(str(current_user.id), platform, account_id)
    if not removed:
        raise HTTPException(404, f"Account '{account_id}' not found for platform '{platform}'.")
    return {"message": f"Account '{account_id}' unlinked from {PLATFORM_META[platform]['name']}."}


# ── Setup step guides ─────────────────────────────────────────────────────────

def _setup_steps(platform: str) -> list[dict]:
    steps_map = {
        "meta": [
            {"step": 1, "title": "Create a Meta Developer App", "detail": "Go to developers.facebook.com/apps and create a Business app type.", "url": "https://developers.facebook.com/apps"},
            {"step": 2, "title": "Add Marketing API product", "detail": "In your app dashboard, add the 'Marketing API' product and enable required permissions.", "url": "https://developers.facebook.com/docs/marketing-apis/get-started"},
            {"step": 3, "title": "Submit for App Review", "detail": "Submit ads_management and ads_read for review. Basic access available immediately for testing with developer account.", "url": "https://developers.facebook.com/docs/app-review"},
            {"step": 4, "title": "Set environment variables", "detail": "Add FACEBOOK_APP_ID and FACEBOOK_APP_SECRET to your server .env file.", "url": None},
            {"step": 5, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/meta/auth-url to start the OAuth flow.", "url": None},
        ],
        "google": [
            {"step": 1, "title": "Apply for a Developer Token", "detail": "Sign in to Google Ads Manager and apply for a developer token under API Center.", "url": "https://ads.google.com/home/tools/manager-accounts/"},
            {"step": 2, "title": "Create OAuth2 credentials", "detail": "Go to Google Cloud Console, create an OAuth2 client ID for web application.", "url": "https://console.cloud.google.com/"},
            {"step": 3, "title": "Enable Google Ads API", "detail": "Enable the Google Ads API in your Google Cloud project.", "url": "https://console.cloud.google.com/apis/library/googleads.googleapis.com"},
            {"step": 4, "title": "Set environment variables", "detail": "Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_DEVELOPER_TOKEN to .env.", "url": None},
            {"step": 5, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/google/auth-url to start the OAuth flow.", "url": None},
        ],
        "tiktok": [
            {"step": 1, "title": "Create TikTok for Business developer account", "detail": "Register at developers.tiktok.com with your TikTok for Business account.", "url": "https://developers.tiktok.com/"},
            {"step": 2, "title": "Create an app and apply for Marketing API access", "detail": "Submit Marketing API application. Review typically takes 3–7 business days.", "url": "https://ads.tiktok.com/marketing_api/docs"},
            {"step": 3, "title": "Set environment variables", "detail": "Add TIKTOK_CLIENT_ID and TIKTOK_CLIENT_SECRET to .env.", "url": None},
            {"step": 4, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/tiktok/auth-url to start the OAuth flow.", "url": None},
        ],
        "linkedin": [
            {"step": 1, "title": "Create a LinkedIn developer application", "detail": "Go to linkedin.com/developers and create an app associated with a LinkedIn Page.", "url": "https://www.linkedin.com/developers/apps"},
            {"step": 2, "title": "Apply for Marketing Developer Platform access", "detail": "Request MDP partnership access. Review typically takes 1–4 weeks.", "url": "https://business.linkedin.com/marketing-solutions/marketing-partners/become-a-partner/marketing-developer-program"},
            {"step": 3, "title": "Set environment variables", "detail": "Add LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET to .env.", "url": None},
            {"step": 4, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/linkedin/auth-url to start the OAuth flow.", "url": None},
        ],
        "pinterest": [
            {"step": 1, "title": "Create a Pinterest Business account", "detail": "Convert to or create a Pinterest Business account.", "url": "https://business.pinterest.com/"},
            {"step": 2, "title": "Register a developer app", "detail": "Go to developers.pinterest.com and create an app. ads:read and ads:write are available without extended review.", "url": "https://developers.pinterest.com/"},
            {"step": 3, "title": "Set environment variables", "detail": "Add PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET to .env.", "url": None},
            {"step": 4, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/pinterest/auth-url to start the OAuth flow.", "url": None},
        ],
        "snap": [
            {"step": 1, "title": "Create a Snapchat Business account", "detail": "Register at business.snapchat.com.", "url": "https://business.snapchat.com/"},
            {"step": 2, "title": "Apply for Marketing API access", "detail": "Apply at kit.snapchat.com. Business and developer accounts must be linked.", "url": "https://kit.snapchat.com/"},
            {"step": 3, "title": "Set environment variables", "detail": "Add SNAP_CLIENT_ID and SNAP_CLIENT_SECRET to .env.", "url": None},
            {"step": 4, "title": "Connect via OAuth", "detail": "Use POST /api/v1/ads-connectors/snap/auth-url to start the OAuth flow.", "url": None},
        ],
    }
    return steps_map.get(platform, [])
