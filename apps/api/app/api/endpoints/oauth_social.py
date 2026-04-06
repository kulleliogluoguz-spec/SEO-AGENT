"""
Social OAuth Flows — X (OAuth 1.0a), Meta (Instagram + Ads), Google (Ads)

GET  /api/v1/auth/x/authorize             — get X OAuth 1.0a request token + auth URL
GET  /api/v1/auth/x/callback              — exchange oauth_token+verifier, redirect to frontend
POST /api/v1/auth/x/callback              — JSON API exchange (used by frontend callback page)
GET  /api/v1/auth/meta/authorize          — generate Meta/Facebook OAuth URL
GET  /api/v1/auth/meta/callback           — exchange code, get long-lived token + ad accounts
GET  /api/v1/auth/google/authorize        — generate Google OAuth URL (Ads scope)
POST /api/v1/auth/google/callback         — exchange code, store, fetch ad accounts
GET  /api/v1/auth/connections             — list all connected platforms for current user
DELETE /api/v1/auth/connections/{platform} — revoke a connection
"""

from __future__ import annotations

import json
import logging
import secrets
import urllib.parse
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.config.settings import get_settings
from app.core.security.oauth1 import build_auth_header as _oauth1_build_header
from app.core.store.credential_store import (
    delete_credential,
    get_linked_accounts,
    link_account,
    list_credentials,
    store_credential,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

FRONTEND_URL = settings.frontend_url

# ─── Persistent state store (survives server restarts) ───────────────────────
# Previous implementation used in-memory dict which was lost on every uvicorn
# --reload cycle, causing "Invalid or expired OAuth token" errors.

_STATE_FILE = Path(__file__).resolve().parents[3] / "storage" / "oauth_state.json"
_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state_store() -> dict:
    if not _STATE_FILE.exists():
        return {}
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state_store(store: dict) -> None:
    with open(_STATE_FILE, "w") as f:
        json.dump(store, f, indent=2)


def _save_state(state: str, user_id: str, platform: str, **extra) -> None:
    """Persist an OAuth state entry to disk."""
    store = _load_state_store()
    store[state] = {"user_id": user_id, "platform": platform, **extra}
    _save_state_store(store)


def _consume_state(state: str) -> dict | None:
    """Pop and return state entry. Persists removal to disk. Returns None if missing."""
    store = _load_state_store()
    entry = store.pop(state, None)
    if entry is not None:
        _save_state_store(store)
        logger.info("[oauth] consumed state key=%s… (%d remaining)", state[:15], len(store))
    else:
        logger.warning(
            "[oauth] state key=%s… NOT FOUND. File=%s exists=%s keys=%s",
            state[:15], _STATE_FILE, _STATE_FILE.exists(),
            list(store.keys())[:3] if store else "[]",
        )
    return entry


# ─── OAuth 1.0a URLs ─────────────────────────────────────────────────────────

X_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
X_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
X_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
X_VERIFY_URL = "https://api.twitter.com/2/users/me"

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
    additional_oauth_params: dict | None = None,
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


def _redirect_with_error(platform: str, error: str) -> RedirectResponse:
    """Redirect to frontend connectors page with error message in query param."""
    encoded = urllib.parse.quote(error)
    return RedirectResponse(
        url=f"{FRONTEND_URL}/dashboard/connectors?error={encoded}&platform={platform}",
        status_code=302,
    )


async def _x_exchange_tokens(oauth_token: str, oauth_verifier: str, oauth_token_secret: str) -> dict:
    """Exchange OAuth 1.0a request token + verifier for access tokens.
    Returns dict with tokens + user info on success, or error string."""
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
        logger.error("[x] access_token exchange failed %s: %s", resp.status_code, resp.text[:300])
        return {"error": f"X token exchange failed ({resp.status_code}). Please try again."}

    token_data = dict(urllib.parse.parse_qsl(resp.text))
    access_token = token_data.get("oauth_token", "")
    access_token_secret = token_data.get("oauth_token_secret", "")
    x_user_id = token_data.get("user_id", "")
    x_username = token_data.get("screen_name", "")

    if not access_token:
        return {"error": "X did not return access tokens. Check app permissions (Read+Write)."}

    return {
        "access_token": access_token,
        "access_token_secret": access_token_secret,
        "x_user_id": x_user_id,
        "x_username": x_username,
    }


async def _x_verify_credentials(access_token: str, access_token_secret: str) -> dict | None:
    """Verify tokens by calling GET /2/users/me. Returns user info or None."""
    qp = {"user.fields": "public_metrics,name"}
    auth_header = _oauth1_auth_header(
        method="GET",
        url=X_VERIFY_URL,
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        token=access_token,
        token_secret=access_token_secret,
        additional_oauth_params=None,
    )
    # OAuth 1.0a requires query params in the signature — use the updated helper
    from app.core.security.oauth1 import build_auth_header as _build
    auth_header = _build(
        method="GET",
        url=X_VERIFY_URL,
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        token=access_token,
        token_secret=access_token_secret,
        query_params=qp,
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                X_VERIFY_URL,
                headers={"Authorization": auth_header},
                params=qp,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                metrics = data.get("public_metrics", {})
                return {
                    "username": data.get("username", ""),
                    "display_name": data.get("name", ""),
                    "x_user_id": data.get("id", ""),
                    "followers": metrics.get("followers_count", 0),
                }
    except Exception as e:
        logger.debug("[x] verify_credentials failed: %s", e)
    return None


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

    # Persist to file (survives --reload)
    _save_state(
        oauth_token,
        user_id=str(user.id),
        platform="x",
        oauth_token_secret=oauth_token_secret,
    )

    logger.info(
        "[x_authorize] saved state key=%s… file=%s callback=%s",
        oauth_token[:15], _STATE_FILE, settings.x_callback_url,
    )

    return {
        "authorization_url": f"{X_AUTHORIZE_URL}?oauth_token={oauth_token}",
        "oauth_token": oauth_token,
    }


class XCallbackBody(BaseModel):
    oauth_token: str
    oauth_verifier: str


@router.get("/auth/x/callback")
async def x_callback_get(
    request: Request,
    oauth_token: str = Query(None),
    oauth_verifier: str = Query(None),
    denied: str = Query(None),
):
    """
    Step 2 (GET): Twitter redirects the browser here after authorization.
    Exchanges tokens, stores credentials, redirects to frontend.
    All errors redirect to frontend with ?error= instead of returning JSON.
    """
    # ── Debug: print ALL incoming params to terminal ──
    print(f"\n{'='*60}")
    print(f"[X CALLBACK] HIT at {__import__('datetime').datetime.now().isoformat()}")
    print(f"[X CALLBACK] Full URL: {request.url}")
    print(f"[X CALLBACK] Query params: {dict(request.query_params)}")
    print(f"[X CALLBACK] oauth_token={oauth_token}")
    print(f"[X CALLBACK] oauth_verifier={oauth_verifier}")
    print(f"[X CALLBACK] denied={denied}")
    print(f"[X CALLBACK] State file: {_STATE_FILE}")
    print(f"[X CALLBACK] State file exists: {_STATE_FILE.exists()}")
    if _STATE_FILE.exists():
        import json as _json
        try:
            _contents = _json.load(open(_STATE_FILE))
            print(f"[X CALLBACK] State file keys: {list(_contents.keys())}")
            print(f"[X CALLBACK] Token in state: {oauth_token in _contents if oauth_token else 'N/A'}")
        except Exception as _e:
            print(f"[X CALLBACK] State file read error: {_e}")
    print(f"{'='*60}\n")

    # User denied authorization
    if denied:
        print("[X CALLBACK] User denied. Redirecting with error.")
        return _redirect_with_error("x", "Authorization was denied.")

    if not oauth_token or not oauth_verifier:
        print(f"[X CALLBACK] Missing params! token={oauth_token} verifier={oauth_verifier}")
        return _redirect_with_error("x", "Missing OAuth parameters. Please try connecting again.")

    # Look up state
    state_data = _consume_state(oauth_token)
    if not state_data:
        print(f"[X CALLBACK] STATE NOT FOUND for token={oauth_token}")
        print(f"[X CALLBACK] This means the token was not in {_STATE_FILE}")
        return _redirect_with_error(
            "x",
            "OAuth session expired. Please click 'Connect X Account' again to restart.",
        )

    print(f"[X CALLBACK] State found! user_id={state_data.get('user_id')}")

    user_id = state_data["user_id"]
    oauth_token_secret = state_data.get("oauth_token_secret", "")

    # Exchange for access tokens
    print("[X CALLBACK] Exchanging tokens with Twitter API...")
    result = await _x_exchange_tokens(oauth_token, oauth_verifier, oauth_token_secret)
    if "error" in result:
        print(f"[X CALLBACK] TOKEN EXCHANGE FAILED: {result['error']}")
        return _redirect_with_error("x", result["error"])
    print(f"[X CALLBACK] Token exchange SUCCESS! username=@{result.get('x_username')}")

    # Verify the new tokens actually work
    verified = await _x_verify_credentials(result["access_token"], result["access_token_secret"])

    username = verified["username"] if verified else result.get("x_username", "")
    x_user_id = verified["x_user_id"] if verified else result.get("x_user_id", "")

    # Store credentials
    store_credential(
        user_id=user_id,
        platform="x",
        access_token=result["access_token"],
        refresh_token=result["access_token_secret"],
        scope="tweet.read tweet.write users.read",
        extra={
            "x_user_id": x_user_id,
            "x_username": username,
            "token_type": "oauth1",
            "followers": verified.get("followers", 0) if verified else 0,
        },
    )

    # Also save to twitter_accounts table for multi-account support
    try:
        from app.api.endpoints.twitter_engine import _db as tw_db

        existing = tw_db(
            "SELECT id FROM twitter_accounts WHERE twitter_user_id=? AND is_active=1",
            (x_user_id,),
        )
        if existing:
            tw_db(
                """UPDATE twitter_accounts
                   SET access_token=?, access_token_secret=?, username=?,
                       display_name=?, followers=?, connected_at=?
                   WHERE id=?""",
                (
                    result["access_token"],
                    result["access_token_secret"],
                    username,
                    verified.get("display_name", "") if verified else "",
                    verified.get("followers", 0) if verified else 0,
                    __import__("datetime").datetime.now().isoformat(),
                    existing[0]["id"],
                ),
                fetch=False,
            )
        else:
            tw_db(
                """INSERT INTO twitter_accounts
                   (workspace_id, twitter_user_id, username, display_name,
                    access_token, access_token_secret, followers, connected_at)
                   VALUES ('default', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    x_user_id,
                    username,
                    verified.get("display_name", "") if verified else "",
                    result["access_token"],
                    result["access_token_secret"],
                    verified.get("followers", 0) if verified else 0,
                    __import__("datetime").datetime.now().isoformat(),
                ),
                fetch=False,
            )
    except Exception as e:
        logger.debug("[x_callback] twitter_accounts sync skipped: %s", e)

    redirect_url = f"{FRONTEND_URL}/dashboard/connectors?connected=x&username={urllib.parse.quote(username)}"
    print(f"[X CALLBACK] ALL DONE! Tokens saved. Redirecting to: {redirect_url}")
    logger.info("[x_callback] stored tokens for user=%s @%s", user_id, username)

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/auth/x/callback")
async def x_callback_post(request: Request):
    """
    Step 2 (POST): Frontend callback page sends tokens via JSON.
    Handles both OAuth 1.0a params (oauth_token, oauth_verifier)
    and any legacy OAuth 2.0 params (code, state).
    Returns JSON with username for the frontend to display.
    """
    body = await request.json()

    oauth_token = body.get("oauth_token") or body.get("code", "")
    oauth_verifier = body.get("oauth_verifier") or body.get("state", "")

    if not oauth_token or not oauth_verifier:
        raise HTTPException(400, "Missing oauth_token and oauth_verifier.")

    state_data = _consume_state(oauth_token)
    if not state_data:
        raise HTTPException(
            400,
            "OAuth session expired. This happens if the server restarted during login. "
            "Please go back to Connections and try again.",
        )

    user_id = state_data["user_id"]
    oauth_token_secret = state_data.get("oauth_token_secret", "")

    result = await _x_exchange_tokens(oauth_token, oauth_verifier, oauth_token_secret)
    if "error" in result:
        raise HTTPException(400, result["error"])

    verified = await _x_verify_credentials(result["access_token"], result["access_token_secret"])
    username = verified["username"] if verified else result.get("x_username", "")
    x_user_id = verified["x_user_id"] if verified else result.get("x_user_id", "")

    store_credential(
        user_id=user_id,
        platform="x",
        access_token=result["access_token"],
        refresh_token=result["access_token_secret"],
        scope="tweet.read tweet.write users.read",
        extra={
            "x_user_id": x_user_id,
            "x_username": username,
            "token_type": "oauth1",
            "followers": verified.get("followers", 0) if verified else 0,
        },
    )

    # Sync to twitter_accounts
    try:
        from app.api.endpoints.twitter_engine import _db as tw_db

        existing = tw_db(
            "SELECT id FROM twitter_accounts WHERE twitter_user_id=? AND is_active=1",
            (x_user_id,),
        )
        if not existing:
            tw_db(
                """INSERT INTO twitter_accounts
                   (workspace_id, twitter_user_id, username, display_name,
                    access_token, access_token_secret, followers, connected_at)
                   VALUES ('default', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    x_user_id,
                    username,
                    verified.get("display_name", "") if verified else "",
                    result["access_token"],
                    result["access_token_secret"],
                    verified.get("followers", 0) if verified else 0,
                    __import__("datetime").datetime.now().isoformat(),
                ),
                fetch=False,
            )
    except Exception as e:
        logger.debug("[x_callback_post] twitter_accounts sync skipped: %s", e)

    logger.info("[x_callback] POST: stored tokens for user=%s @%s", user_id, username)

    return {
        "connected": True,
        "username": username,
        "x_user_id": x_user_id,
        "followers": verified.get("followers", 0) if verified else 0,
    }


# ─── Meta (Instagram + Meta Ads) OAuth ───────────────────────────────────────


@router.get("/auth/meta/authorize")
async def meta_authorize(
    scope: str = "instagram",
    user=Depends(get_current_user),
):
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
    state_data = _consume_state(state)
    if not state_data:
        return _redirect_with_error("meta", "OAuth session expired. Please try connecting again.")

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
        return _redirect_with_error("meta", f"Meta token exchange failed: {resp.text[:200]}")

    short_lived = resp.json()
    short_token = short_lived.get("access_token", "")

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

    long_lived_token = short_token
    expires_in = 5184000
    if ll_resp.status_code == 200:
        ll_data = ll_resp.json()
        long_lived_token = ll_data.get("access_token", short_token)
        expires_in = ll_data.get("expires_in", expires_in)

    pages = []
    instagram_accounts = []
    ad_accounts = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        ig_resp = await client.get(
            "https://graph.facebook.com/v20.0/me/accounts",
            params={
                "access_token": long_lived_token,
                "fields": "id,name,instagram_business_account",
            },
        )
        if ig_resp.status_code == 200:
            for page in ig_resp.json().get("data", []):
                pages.append({"page_id": page.get("id"), "page_name": page.get("name")})
                ig_biz = page.get("instagram_business_account")
                if ig_biz:
                    instagram_accounts.append(
                        {
                            "instagram_account_id": ig_biz["id"],
                            "page_id": page["id"],
                            "page_name": page["name"],
                        }
                    )

        platform = state_data.get("platform", "meta_instagram")
        if "ads" in platform:
            ads_resp = await client.get(
                "https://graph.facebook.com/v20.0/me/adaccounts",
                params={
                    "access_token": long_lived_token,
                    "fields": "id,name,currency,account_status",
                },
            )
            if ads_resp.status_code == 200:
                for acc in ads_resp.json().get("data", []):
                    if acc.get("account_status") == 1:
                        ad_accounts.append(
                            {
                                "account_id": acc["id"],
                                "account_name": acc.get("name", ""),
                                "currency": acc.get("currency", "USD"),
                            }
                        )

    user_id = state_data["user_id"]

    store_credential(
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

    store_credential(
        user_id=user_id,
        platform="instagram",
        access_token=long_lived_token,
        scope=META_INSTAGRAM_SCOPES,
        extra={
            "instagram_account_id": instagram_accounts[0]["instagram_account_id"]
            if instagram_accounts
            else "",
            "page_id": instagram_accounts[0]["page_id"] if instagram_accounts else "",
            "instagram_accounts": instagram_accounts,
        },
    )

    for acc in ad_accounts:
        link_account(
            user_id=user_id,
            platform="meta_ads",
            account_id=acc["account_id"],
            account_name=acc["account_name"],
            currency=acc.get("currency", "USD"),
        )

    logger.info(
        "[meta_callback] stored tokens for user=%s pages=%d ig_accounts=%d",
        user_id, len(pages), len(instagram_accounts),
    )
    return RedirectResponse(
        url=f"{FRONTEND_URL}/dashboard/connectors?connected=meta", status_code=302,
    )


# ─── Google OAuth (for Google Ads) ───────────────────────────────────────────


class OAuthCallbackBody(BaseModel):
    code: str
    state: str


@router.get("/auth/google/authorize")
async def google_authorize(user=Depends(get_current_user)):
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
    state_data = _consume_state(body.state)
    if not state_data or state_data["user_id"] != str(user.id):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

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
        raise HTTPException(
            status_code=400, detail=f"Google token exchange failed: {resp.text[:300]}"
        )

    token_data = resp.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

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
    deleted = delete_credential(str(user.id), platform)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"No connection found for platform '{platform}'"
        )
    if platform == "meta":
        delete_credential(str(user.id), "instagram")
    return {"disconnected": True, "platform": platform}
