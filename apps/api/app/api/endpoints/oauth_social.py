"""
Social OAuth Flows — X (OAuth 1.0a), Meta (Instagram + Ads), Google (Ads)

GET  /api/v1/auth/x/authorize             — get X OAuth 1.0a request token + auth URL
GET  /api/v1/auth/x/callback              — exchange oauth_token+verifier, redirect to frontend
GET  /api/v1/auth/meta/authorize          — generate Meta/Facebook OAuth URL
GET  /api/v1/auth/meta/callback           — exchange code, get long-lived token + ad accounts
GET  /api/v1/auth/google/authorize        — generate Google OAuth URL (Ads scope)
POST /api/v1/auth/google/callback         — exchange code, store, fetch ad accounts
GET  /api/v1/auth/connections             — list all connected platforms for current user
DELETE /api/v1/auth/connections/{platform} — revoke a connection

Design:
  All flows return { authorization_url, state } to the caller.
  The frontend redirects the user to authorization_url.
  After authorization, the platform redirects to the callback URL (in .env).
  The frontend callback page sends { code, state } to POST /callback.
  Backend exchanges code for tokens and stores them in credential_store.

X OAuth 2.0 PKCE:
  https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
  Scopes: tweet.write tweet.read users.read offline.access

Meta (Facebook Login):
  https://developers.facebook.com/docs/facebook-login
  Scopes vary: instagram_business_basic, instagram_business_content_publish, instagram_business_manage_insights, ads_management, ads_read

Google OAuth:
  https://developers.google.com/identity/protocols/oauth2/web-server
  Scopes: https://www.googleapis.com/auth/adwords
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.config.settings import get_settings
from app.core.security.oauth1 import build_auth_header as _oauth1_build_header
from app.core.store.credential_store import (
    store_credential,
    get_credential,
    delete_credential,
    list_credentials,
    link_account,
    get_linked_accounts,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ─── In-memory PKCE/state store (persisted to file in production) ─────────────
# Maps state → { code_verifier, user_id, platform }
_oauth_state_store: dict[str, dict] = {}

X_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
X_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
X_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

META_AUTH_URL = "https://www.facebook.com/v20.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v20.0/oauth/access_token"
META_LONG_LIVED_URL = "https://graph.facebook.com/v20.0/oauth/access_token"
META_INSTAGRAM_SCOPES = "pages_show_list,pages_read_engagement,ads_management,business_management"
META_ADS_SCOPES = "ads_management,ads_read,business_management"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _oauth1_auth_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str = "",
    token_secret: str = "",
    additional_oauth_params: Optional[dict] = None,
) -> str:
    return _oauth1_build_header(
        method=method,
        url=url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        token=token,
        token_secret=token_secret,
        additional_oauth_params=additional_oauth_params,
    )


def _save_state(state: str, user_id: str, platform: str, code_verifier: Optional[str] = None) -> None:
    _oauth_state_store[state] = {
        "user_id": user_id,
        "platform": platform,
        "code_verifier": code_verifier,
    }


def _consume_state(state: str) -> Optional[dict]:
    """Return and remove state entry. Returns None if not found."""
    return _oauth_state_store.pop(state, None)


# ─── X / Twitter OAuth 1.0a ──────────────────────────────────────────────────

@router.get("/auth/x/authorize")
async def x_authorize(user=Depends(get_current_user)):
    """
    Step 1: Obtain OAuth 1.0a request token and return Twitter authorization URL.
    Frontend redirects the user to authorization_url.
    """
    if not settings.x_api_key:
        raise HTTPException(
            status_code=400,
            detail="X OAuth not configured. Add X_API_KEY and X_API_SECRET to your .env file.",
        )

    auth_header = _oauth1_auth_header(
        method="POST",
        url=X_REQUEST_TOKEN_URL,
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        additional_oauth_params={"oauth_callback": settings.x_callback_url},
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            X_REQUEST_TOKEN_URL,
            headers={"Authorization": auth_header},
        )

    if resp.status_code != 200:
        logger.error("[x_authorize] request_token failed %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=400, detail=f"X request_token failed: {resp.text[:300]}")

    token_resp = dict(urllib.parse.parse_qsl(resp.text))
    oauth_token = token_resp.get("oauth_token", "")
    oauth_token_secret = token_resp.get("oauth_token_secret", "")

    if not oauth_token:
        raise HTTPException(status_code=400, detail="X did not return oauth_token")

    _oauth_state_store[oauth_token] = {
        "user_id": str(user.id),
        "platform": "x",
        "oauth_token_secret": oauth_token_secret,
    }

    return {"authorization_url": f"{X_AUTHORIZE_URL}?oauth_token={oauth_token}", "oauth_token": oauth_token}


class OAuthCallbackBody(BaseModel):
    code: str
    state: str


@router.get("/auth/x/callback")
async def x_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
):
    """
    Step 2: Exchange oauth_token + oauth_verifier for access tokens (OAuth 1.0a).
    Twitter redirects the browser here after the user authorizes the app.
    Stores tokens then redirects the browser to the frontend connectors page.
    """
    state_data = _oauth_state_store.pop(oauth_token, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth token. Restart the connection flow.")

    user_id = state_data["user_id"]
    oauth_token_secret = state_data["oauth_token_secret"]

    auth_header = _oauth1_auth_header(
        method="POST",
        url=X_ACCESS_TOKEN_URL,
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        token=oauth_token,
        token_secret=oauth_token_secret,
        additional_oauth_params={"oauth_verifier": oauth_verifier},
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            X_ACCESS_TOKEN_URL,
            headers={"Authorization": auth_header},
        )

    if resp.status_code != 200:
        logger.error("[x_callback] access_token exchange failed %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=400, detail=f"X access_token exchange failed: {resp.text[:300]}")

    token_data = dict(urllib.parse.parse_qsl(resp.text))
    access_token = token_data.get("oauth_token", "")
    access_token_secret = token_data.get("oauth_token_secret", "")
    x_user_id = token_data.get("user_id", "")
    x_username = token_data.get("screen_name", "")

    store_credential(
        user_id=user_id,
        platform="x",
        access_token=access_token,
        refresh_token=access_token_secret,  # token_secret stored in refresh_token slot
        scope="tweet.read tweet.write users.read",
        extra={
            "x_user_id": x_user_id,
            "x_username": x_username,
            "token_type": "oauth1",
        },
    )

    logger.info("[x_callback] stored OAuth 1.0a tokens for user=%s x_username=@%s", user_id, x_username)
    return RedirectResponse(url="http://localhost:3000/dashboard/connectors?connected=x", status_code=302)


# ─── Meta (Instagram + Meta Ads) OAuth ───────────────────────────────────────

@router.get("/auth/meta/authorize")
async def meta_authorize(
    scope: str = "instagram",  # "instagram" | "ads" | "all"
    user=Depends(get_current_user),
):
    """
    Generate Meta/Facebook OAuth URL.
    scope="instagram" → Instagram publishing permissions
    scope="ads"       → Meta Ads management permissions
    scope="all"       → Both
    """
    if not settings.meta_app_id:
        raise HTTPException(
            status_code=400,
            detail="Meta OAuth not configured. Add META_APP_ID and META_APP_SECRET to your .env file.",
        )

    state = secrets.token_urlsafe(16)
    _save_state(state, str(user.id), f"meta_{scope}")

    scopes_map = {
        "instagram": META_INSTAGRAM_SCOPES,
        "ads": META_ADS_SCOPES,
        "all": f"{META_INSTAGRAM_SCOPES},{META_ADS_SCOPES}",
    }
    requested_scope = scopes_map.get(scope, META_INSTAGRAM_SCOPES)

    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_callback_url,
        "scope": requested_scope,
        "state": state,
        "response_type": "code",
    }
    url = f"{META_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"authorization_url": url, "state": state, "requested_scope": requested_scope}


@router.get("/auth/meta/callback")
async def meta_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Exchange Meta code for long-lived token. Stores credential and fetches ad accounts.
    Meta redirects here via GET with ?code=...&state=...
    User identity is resolved from the state store.
    """
    state_data = _consume_state(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    # Step 1: Exchange code for short-lived token
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            META_TOKEN_URL,
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": settings.meta_callback_url,
                "code": code,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Meta token exchange failed: {resp.text[:300]}")

    short_lived = resp.json()
    short_token = short_lived.get("access_token", "")

    # Step 2: Exchange for long-lived token (60 days)
    async with httpx.AsyncClient(timeout=15.0) as client:
        ll_resp = await client.get(
            META_LONG_LIVED_URL,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": short_token,
            },
        )

    long_lived_token = short_token  # fallback
    expires_in = 5184000  # 60 days default
    if ll_resp.status_code == 200:
        ll_data = ll_resp.json()
        long_lived_token = ll_data.get("access_token", short_token)
        expires_in = ll_data.get("expires_in", expires_in)

    # Step 3: Fetch user's Facebook pages (needed for Instagram Business API)
    pages = []
    instagram_accounts = []
    ad_accounts = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get linked Instagram business accounts
        ig_resp = await client.get(
            "https://graph.facebook.com/v20.0/me/accounts",
            params={"access_token": long_lived_token, "fields": "id,name,instagram_business_account"},
        )
        if ig_resp.status_code == 200:
            for page in ig_resp.json().get("data", []):
                pages.append({"page_id": page.get("id"), "page_name": page.get("name")})
                ig_biz = page.get("instagram_business_account")
                if ig_biz:
                    instagram_accounts.append({
                        "instagram_account_id": ig_biz["id"],
                        "page_id": page["id"],
                        "page_name": page["name"],
                    })

        # Get ad accounts if ads scope was requested
        platform = state_data.get("platform", "meta_instagram")
        if "ads" in platform:
            ads_resp = await client.get(
                "https://graph.facebook.com/v20.0/me/adaccounts",
                params={"access_token": long_lived_token, "fields": "id,name,currency,account_status"},
            )
            if ads_resp.status_code == 200:
                for acc in ads_resp.json().get("data", []):
                    if acc.get("account_status") == 1:  # 1 = ACTIVE
                        ad_accounts.append({
                            "account_id": acc["id"],
                            "account_name": acc.get("name", ""),
                            "currency": acc.get("currency", "USD"),
                        })

    user_id = state_data["user_id"]

    # Store credential
    record = store_credential(
        user_id=user_id,
        platform="meta",
        access_token=long_lived_token,
        scope=state_data.get("platform", ""),
        extra={
            "pages": pages,
            "instagram_accounts": instagram_accounts,
            "ad_accounts": ad_accounts,
            "expires_in": expires_in,
        },
    )

    # Always store as "instagram" — the publisher checks this key for connection status.
    # If a linked Instagram Business account was found, include its ID; otherwise the
    # long-lived Meta token is still valid and check_status() (/me) will return READY.
    store_credential(
        user_id=user_id,
        platform="instagram",
        access_token=long_lived_token,
        scope=META_INSTAGRAM_SCOPES,
        extra={
            "instagram_account_id": instagram_accounts[0]["instagram_account_id"] if instagram_accounts else "",
            "page_id": instagram_accounts[0]["page_id"] if instagram_accounts else "",
            "instagram_accounts": instagram_accounts,
        },
    )

    # Link ad accounts
    for acc in ad_accounts:
        link_account(
            user_id=user_id,
            platform="meta_ads",
            account_id=acc["account_id"],
            account_name=acc["account_name"],
            currency=acc.get("currency", "USD"),
        )

    logger.info("[meta_callback] stored tokens for user=%s pages=%d ig_accounts=%d", user_id, len(pages), len(instagram_accounts))
    return RedirectResponse(url="http://localhost:3000/dashboard/connectors?connected=meta", status_code=302)


# ─── Google OAuth (for Google Ads) ───────────────────────────────────────────

@router.get("/auth/google/authorize")
async def google_authorize(user=Depends(get_current_user)):
    """Generate Google OAuth URL for Google Ads access."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file.",
        )

    state = secrets.token_urlsafe(16)
    _save_state(state, str(user.id), "google_ads")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_callback_url,
        "response_type": "code",
        "scope": GOOGLE_ADS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"authorization_url": url, "state": state}


@router.post("/auth/google/callback")
async def google_callback(body: OAuthCallbackBody, user=Depends(get_current_user)):
    """Exchange Google code for tokens, fetch accessible ad accounts."""
    state_data = _consume_state(body.state)
    if not state_data or state_data["user_id"] != str(user.id):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": body.code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_callback_url,
                "grant_type": "authorization_code",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {resp.text[:300]}")

    token_data = resp.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

    # Fetch accessible customer accounts via Google Ads API
    ad_accounts = []
    if settings.google_ads_developer_token:
        async with httpx.AsyncClient(timeout=10.0) as client:
            customers_resp = await client.get(
                "https://googleads.googleapis.com/v17/customers:listAccessibleCustomers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.google_ads_developer_token,
                },
            )
            if customers_resp.status_code == 200:
                for resource_name in customers_resp.json().get("resourceNames", []):
                    customer_id = resource_name.split("/")[-1]
                    ad_accounts.append({"customer_id": customer_id, "resource_name": resource_name})

    record = store_credential(
        user_id=str(user.id),
        platform="google_ads",
        access_token=access_token,
        refresh_token=refresh_token,
        scope=GOOGLE_ADS_SCOPE,
        extra={
            "ad_accounts": ad_accounts,
            "expires_in": expires_in,
            "developer_token": settings.google_ads_developer_token,
        },
    )

    for acc in ad_accounts:
        link_account(
            user_id=str(user.id),
            platform="google_ads",
            account_id=acc["customer_id"],
            account_name=f"Google Ads #{acc['customer_id']}",
        )

    return {
        "connected": True,
        "platform": "google_ads",
        "ad_accounts": ad_accounts,
        "credential": record,
    }


# ─── Connection management ────────────────────────────────────────────────────

@router.get("/auth/connections")
async def list_connections(user=Depends(get_current_user)):
    """List all connected platforms with their status."""
    credentials = list_credentials(str(user.id))
    linked = get_linked_accounts(str(user.id))

    platforms = {c["platform"]: c for c in credentials}

    return {
        "connections": [
            {
                "platform": platform,
                "connected": True,
                "has_access_token": info["has_access_token"],
                "has_refresh_token": info["has_refresh_token"],
                "scope": info.get("scope", ""),
                "connected_at": info.get("created_at"),
            }
            for platform, info in platforms.items()
        ],
        "ad_accounts": linked,
        "total_connected": len(platforms),
    }


@router.delete("/auth/connections/{platform}")
async def disconnect_platform(platform: str, user=Depends(get_current_user)):
    """Revoke and delete stored credentials for a platform."""
    deleted = delete_credential(str(user.id), platform)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No connection found for platform '{platform}'")

    # Also remove instagram alias if disconnecting meta
    if platform == "meta":
        delete_credential(str(user.id), "instagram")

    return {"disconnected": True, "platform": platform}
