"""
Integrations API — Dashboard-driven Meta + Google Ads connection.

No env-file manual setup needed once Meta/Google credentials are in
.env: companies connect their own ad accounts through the dashboard
via OAuth or by pasting a system-user / refresh token.

Important: this module writes synced campaign + performance data to
`analytics_ad_campaigns` and `ad_performance_daily` (the Phase 2 ad
analytics tables), NOT the mktg_001 `ad_campaigns` table that holds
creative copy.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.integrations.google_ads_service import (
    GoogleAdsDataFetcher,
    GoogleAdsOAuthService,
)
from app.services.integrations.meta_ads_fetcher import MetaAdsFetcher
from app.services.integrations.meta_oauth import MetaOAuthService
from app.services.security.encryption import decrypt

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3001")
DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out: dict = {}
    for k, v in row._mapping.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ─── CONNECTIONS LIST ─────────────────────────────────────────────


@router.get("/connections")
async def list_connections(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all ad account connections for this workspace."""
    r = await db.execute(
        text(
            """
            SELECT id, platform, account_id, account_name, currency, timezone,
                   is_active, last_sync_status, last_sync_error,
                   connected_at, last_synced_at
            FROM ad_account_connections
            WHERE workspace_id = :wid
            ORDER BY platform, connected_at DESC
            """
        ),
        {"wid": _wid(current_user)},
    )
    connections = [_row_to_dict(row) for row in r.fetchall()]
    return {"connections": connections}


@router.delete("/connections/{connection_id}")
async def disconnect_account(
    connection_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and delete an ad account connection."""
    await db.execute(
        text(
            """
            DELETE FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid
            """
        ),
        {"id": connection_id, "wid": _wid(current_user)},
    )
    await db.commit()
    return {"success": True, "message": "Account disconnected"}


# ─── META ADS ─────────────────────────────────────────────────────


@router.get("/meta/authorize")
async def meta_authorize(current_user=Depends(get_current_user)):
    """Step 1 — return the Meta OAuth authorization URL the frontend should open."""
    state = f"{_wid(current_user)}:{uuid.uuid4()}"
    redirect_uri = f"{BACKEND_URL}/api/v1/integrations/meta/callback"
    oauth = MetaOAuthService()
    auth_url = oauth.get_oauth_url(redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}


@router.get("/meta/callback")
async def meta_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2 — Meta redirects here with the OAuth code. We exchange it
    for a long-lived token, fetch ad accounts, save them, and redirect
    the user back to the integrations page.
    """
    workspace_id = state.split(":")[0]
    redirect_base = f"{FRONTEND_URL}/dashboard/integrations"

    try:
        redirect_uri = f"{BACKEND_URL}/api/v1/integrations/meta/callback"
        oauth = MetaOAuthService()

        token_data = oauth.exchange_code_for_token(code, redirect_uri)
        short_token = token_data.get("access_token")

        long_token_data = oauth.get_long_lived_token(short_token)
        long_token = long_token_data.get("access_token", short_token)

        ad_accounts = oauth.get_ad_accounts(long_token)
        if not ad_accounts:
            return RedirectResponse(f"{redirect_base}?status=error&msg=no_accounts")

        saved_count = 0
        for account in ad_accounts:
            await oauth.save_connection(
                db=db,
                workspace_id=workspace_id,
                account_id=account["account_id"],
                account_name=account["account_name"],
                access_token=long_token,
                currency=account.get("currency", "USD"),
                timezone=account.get("timezone"),
            )
            saved_count += 1

        logger.info(
            "Meta OAuth complete: workspace=%s accounts=%s",
            workspace_id,
            saved_count,
        )
        return RedirectResponse(
            f"{redirect_base}?status=success&platform=meta&accounts={saved_count}"
        )

    except Exception as e:
        logger.error("Meta OAuth callback failed: %s", e, exc_info=True)
        return RedirectResponse(f"{redirect_base}?status=error&msg={str(e)[:100]}")


@router.post("/meta/connect-token")
async def meta_connect_with_token(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect Meta with a manually-provided System User Token.

    Useful for the first onboarding flow where the company doesn't
    want to go through full OAuth app review.
    """
    access_token = data.get("access_token")
    account_id = (data.get("account_id") or "").strip()

    if not access_token:
        raise HTTPException(400, "access_token required")

    oauth = MetaOAuthService()
    if not oauth.validate_token(access_token):
        raise HTTPException(400, "Token validation failed — token may be invalid or expired")

    if not account_id:
        ad_accounts = oauth.get_ad_accounts(access_token)
        if not ad_accounts:
            raise HTTPException(400, "No ad accounts found for this token")
        saved = []
        for account in ad_accounts:
            conn_id = await oauth.save_connection(
                db=db,
                workspace_id=_wid(current_user),
                account_id=account["account_id"],
                account_name=account["account_name"],
                access_token=access_token,
                currency=account.get("currency", "USD"),
            )
            saved.append({"connection_id": conn_id, "account_id": account["account_id"]})
        return {"success": True, "connected_accounts": saved}

    account_name = data.get("account_name") or account_id
    conn_id = await oauth.save_connection(
        db=db,
        workspace_id=_wid(current_user),
        account_id=account_id,
        account_name=account_name,
        access_token=access_token,
    )
    return {"success": True, "connection_id": conn_id}


@router.get("/meta/sync/{connection_id}")
async def sync_meta_account(
    connection_id: str,
    days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync campaigns + daily performance from Meta into the
    `analytics_ad_campaigns` and `ad_performance_daily` tables.
    """
    workspace_id = _wid(current_user)
    r = await db.execute(
        text(
            """
            SELECT * FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid AND platform = 'meta'
            """
        ),
        {"id": connection_id, "wid": workspace_id},
    )
    conn_row = r.fetchone()
    if not conn_row:
        raise HTTPException(404, "Connection not found")
    conn_dict = _row_to_dict(conn_row)

    enc_token = conn_dict.get("long_lived_token_enc") or conn_dict.get("access_token_enc")
    token = decrypt(enc_token) if enc_token else None
    if not token:
        # The SELECT * above only returns columns that aren't suppressed —
        # re-pull both encrypted token columns explicitly.
        token_r = await db.execute(
            text(
                """
                SELECT long_lived_token_enc, access_token_enc
                FROM ad_account_connections WHERE id = :id
                """
            ),
            {"id": connection_id},
        )
        token_row = token_r.fetchone()
        if token_row:
            tdict = _row_to_dict(token_row)
            token = decrypt(tdict.get("long_lived_token_enc")) or decrypt(
                tdict.get("access_token_enc")
            )
    if not token:
        raise HTTPException(400, "Token decryption failed — reconnect required")

    fetcher = MetaAdsFetcher(token)
    account_id = conn_dict["account_id"]
    campaign_data = fetcher.sync_all_campaigns(account_id, days=days)
    account_summary = fetcher.get_account_summary(account_id, days=days)

    # Find or create the ad_accounts row for this Meta account.
    acc_r = await db.execute(
        text(
            """
            SELECT id FROM ad_accounts
            WHERE workspace_id = :wid AND platform = 'meta' AND account_id = :aid
            """
        ),
        {"wid": workspace_id, "aid": account_id},
    )
    acc_row = acc_r.fetchone()
    if acc_row:
        ad_account_uuid = str(acc_row[0])
    else:
        acc_ins = await db.execute(
            text(
                """
                INSERT INTO ad_accounts
                    (id, workspace_id, platform, account_id, account_name,
                     currency, is_active, last_sync_at)
                VALUES (gen_random_uuid(), :wid, 'meta', :aid, :name, :curr,
                        true, NOW())
                RETURNING id
                """
            ),
            {
                "wid": workspace_id,
                "aid": account_id,
                "name": conn_dict.get("account_name") or account_id,
                "curr": conn_dict.get("currency") or "USD",
            },
        )
        ad_account_uuid = str(acc_ins.fetchone()[0])

    synced_campaigns = 0
    today = date.today()

    for item in campaign_data:
        camp = item["campaign"]
        insights = item.get("insights", {})
        camp_ext_id = camp.get("id")
        if not camp_ext_id:
            continue

        # Upsert into analytics_ad_campaigns by (ad_account_id, platform_campaign_id).
        camp_r = await db.execute(
            text(
                """
                INSERT INTO analytics_ad_campaigns
                    (id, ad_account_id, platform_campaign_id, name, status,
                     campaign_type, daily_budget, last_synced_at)
                VALUES (gen_random_uuid(), :aid, :pcid, :name, :status,
                        :ctype, :budget, NOW())
                ON CONFLICT (ad_account_id, platform_campaign_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    last_synced_at = NOW()
                RETURNING id
                """
            ),
            {
                "aid": ad_account_uuid,
                "pcid": camp_ext_id,
                "name": camp.get("name") or "Unnamed",
                "status": (camp.get("status") or "ACTIVE")[:50],
                "ctype": (camp.get("objective") or "")[:100],
                "budget": (
                    float(camp.get("daily_budget") or 0) / 100 if camp.get("daily_budget") else None
                ),
            },
        )
        camp_uuid = str(camp_r.fetchone()[0])

        # Upsert performance for the latest sync date if insights came back.
        if insights:
            await db.execute(
                text(
                    """
                    INSERT INTO ad_performance_daily
                        (id, campaign_id, date, spend, revenue, impressions,
                         clicks, conversions, roas, cpa, ctr, frequency)
                    VALUES (gen_random_uuid(), :cid, :date, :spend, :rev, :imp,
                            :clicks, :conv, :roas, :cpa, :ctr, :freq)
                    ON CONFLICT (campaign_id, date) DO UPDATE SET
                        spend = EXCLUDED.spend,
                        revenue = EXCLUDED.revenue,
                        impressions = EXCLUDED.impressions,
                        clicks = EXCLUDED.clicks,
                        conversions = EXCLUDED.conversions,
                        roas = EXCLUDED.roas,
                        cpa = EXCLUDED.cpa,
                        ctr = EXCLUDED.ctr,
                        frequency = EXCLUDED.frequency
                    """
                ),
                {
                    "cid": camp_uuid,
                    "date": today,
                    "spend": insights.get("spend", 0),
                    "rev": insights.get("revenue", 0),
                    "imp": insights.get("impressions", 0),
                    "clicks": insights.get("clicks", 0),
                    "conv": insights.get("conversions", 0),
                    "roas": insights.get("roas", 0),
                    "cpa": insights.get("cpa", 0),
                    "ctr": insights.get("ctr", 0),
                    "freq": insights.get("frequency", 0),
                },
            )
        synced_campaigns += 1

    await db.execute(
        text(
            """
            UPDATE ad_account_connections SET
                last_synced_at = NOW(),
                last_sync_status = 'success',
                last_sync_error = NULL
            WHERE id = :id
            """
        ),
        {"id": connection_id},
    )
    await db.commit()

    return {
        "success": True,
        "synced_campaigns": synced_campaigns,
        "account_summary": account_summary,
        "period_days": days,
    }


# ─── GOOGLE ADS ───────────────────────────────────────────────────


@router.get("/google/authorize")
async def google_authorize(current_user=Depends(get_current_user)):
    """Return the Google OAuth authorization URL."""
    state = f"{_wid(current_user)}:{uuid.uuid4()}"
    try:
        oauth = GoogleAdsOAuthService()
        auth_url = oauth.get_oauth_url(state=state)
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle the Google OAuth callback and persist the refresh token."""
    workspace_id = state.split(":")[0]
    redirect_base = f"{FRONTEND_URL}/dashboard/integrations"
    try:
        oauth = GoogleAdsOAuthService()
        tokens = oauth.exchange_code_for_tokens(code)
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token") or ""

        if not refresh_token:
            return RedirectResponse(
                f"{redirect_base}?status=error&msg=no_refresh_token_hint=add_prompt_consent"
            )

        customers = oauth.get_accessible_customers(refresh_token)

        if not customers:
            await oauth.save_connection(
                db,
                workspace_id,
                "auto-detect",
                "Google Ads Account",
                access_token,
                refresh_token,
            )
            return RedirectResponse(
                f"{redirect_base}?status=partial&platform=google&msg=no_accounts_found"
            )

        for customer in customers:
            await oauth.save_connection(
                db=db,
                workspace_id=workspace_id,
                account_id=customer["customer_id"],
                account_name=customer["account_name"],
                access_token=access_token,
                refresh_token=refresh_token,
            )

        return RedirectResponse(
            f"{redirect_base}?status=success&platform=google&accounts={len(customers)}"
        )
    except Exception as e:
        logger.error("Google callback failed: %s", e, exc_info=True)
        return RedirectResponse(f"{redirect_base}?status=error&msg={str(e)[:100]}")


@router.post("/google/connect-token")
async def google_connect_with_refresh_token(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect Google Ads using a manually-provided refresh token.

    Useful for the first onboarding flow without full OAuth app
    verification.
    """
    refresh_token = data.get("refresh_token")
    customer_id = (data.get("customer_id") or "").replace("-", "")
    account_name = data.get("account_name") or f"Google Ads ({customer_id})"

    if not refresh_token:
        raise HTTPException(400, "refresh_token required")
    if not customer_id:
        raise HTTPException(400, "customer_id required (10-digit Google Ads ID, no dashes)")
    from app.services.integrations.google_ads_service import GOOGLE_DEVELOPER_TOKEN

    if not GOOGLE_DEVELOPER_TOKEN:
        raise HTTPException(400, "GOOGLE_DEVELOPER_TOKEN not configured in .env")

    oauth = GoogleAdsOAuthService()
    conn_id = await oauth.save_connection(
        db=db,
        workspace_id=_wid(current_user),
        account_id=customer_id,
        account_name=account_name,
        access_token="",  # refreshed automatically by SDK
        refresh_token=refresh_token,
    )
    return {"success": True, "connection_id": conn_id}


@router.get("/google/sync/{connection_id}")
async def sync_google_account(
    connection_id: str,
    days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync campaigns and performance from Google Ads."""
    r = await db.execute(
        text(
            """
            SELECT * FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid AND platform = 'google'
            """
        ),
        {"id": connection_id, "wid": _wid(current_user)},
    )
    conn_row = r.fetchone()
    if not conn_row:
        raise HTTPException(404, "Connection not found")
    conn_dict = _row_to_dict(conn_row)

    refresh_token = decrypt(conn_dict.get("refresh_token_enc"))
    if not refresh_token:
        raise HTTPException(400, "No refresh token — reconnect required")

    customer_id = conn_dict["account_id"]
    fetcher = GoogleAdsDataFetcher(refresh_token)
    performance = fetcher.get_campaign_performance(customer_id, days=days)

    await db.execute(
        text(
            """
            UPDATE ad_account_connections
            SET last_synced_at = NOW(), last_sync_status = 'success'
            WHERE id = :id
            """
        ),
        {"id": connection_id},
    )
    await db.commit()

    return {
        "success": True,
        "customer_id": customer_id,
        "campaigns_synced": len(performance),
        "performance": performance,
        "period_days": days,
    }


# ─── SYNC ALL ─────────────────────────────────────────────────────


@router.post("/sync-all")
async def sync_all_accounts(
    days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync every active connection for this workspace."""
    r = await db.execute(
        text(
            """
            SELECT id, platform FROM ad_account_connections
            WHERE workspace_id = :wid AND is_active = true
            """
        ),
        {"wid": _wid(current_user)},
    )
    connections = r.fetchall()
    results = []
    for conn in connections:
        try:
            if conn.platform == "meta":
                await sync_meta_account(str(conn.id), days, current_user, db)
            else:
                await sync_google_account(str(conn.id), days, current_user, db)
            results.append({"id": str(conn.id), "platform": conn.platform, "status": "ok"})
        except Exception as e:
            logger.warning("sync-all failed for %s: %s", conn.id, e)
            results.append(
                {
                    "id": str(conn.id),
                    "platform": conn.platform,
                    "status": "error",
                    "error": str(e)[:100],
                }
            )
    return {"results": results, "total": len(results)}
