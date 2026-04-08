"""
Meta Ads OAuth Service

Handles Facebook Marketing API authentication. Supports both:
  - System User Token (immediate, no user interaction needed)
  - OAuth2 flow (user-authorizes via Facebook, production-grade)
"""

from __future__ import annotations

import logging
import os

import requests
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.encryption import decrypt, encrypt

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v19.0"
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")


class MetaOAuthService:
    def get_oauth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Meta OAuth authorization URL."""
        scopes = "ads_management,ads_read,business_management"
        return (
            "https://www.facebook.com/v19.0/dialog/oauth"
            f"?client_id={META_APP_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            "&response_type=code"
        )

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Exchange OAuth code for short-lived access token."""
        r = requests.get(
            f"{META_GRAPH_URL}/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30,
        )
        if not r.ok:
            raise ValueError(f"Token exchange failed: {r.text}")
        return r.json()

    def get_long_lived_token(self, short_lived_token: str) -> dict:
        """
        Exchange a short-lived (1-2h) token for a long-lived (60-day) token.
        Apps with Standard/Advanced Marketing API access get tokens that
        never expire on the first exchange.
        """
        r = requests.get(
            f"{META_GRAPH_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": short_lived_token,
            },
            timeout=30,
        )
        if not r.ok:
            raise ValueError(f"Long-lived token exchange failed: {r.text}")
        return r.json()

    def get_ad_accounts(self, access_token: str) -> list[dict]:
        """Return all ad accounts accessible with this token."""
        r = requests.get(
            f"{META_GRAPH_URL}/me/adaccounts",
            params={
                "access_token": access_token,
                "fields": "id,name,currency,timezone_name,account_status",
            },
            timeout=30,
        )
        if not r.ok:
            logger.error("Meta ad accounts fetch failed: %s", r.text)
            return []
        data = r.json().get("data", [])
        return [
            {
                "account_id": acc.get("id"),
                "account_name": acc.get("name"),
                "currency": acc.get("currency", "USD"),
                "timezone": acc.get("timezone_name"),
                "status": acc.get("account_status"),
            }
            for acc in data
        ]

    def validate_token(self, access_token: str) -> bool:
        """Verify the token is still valid."""
        try:
            r = requests.get(
                f"{META_GRAPH_URL}/me",
                params={"access_token": access_token, "fields": "id,name"},
                timeout=10,
            )
            return r.ok
        except Exception as e:
            logger.warning("Meta token validation failed: %s", e)
            return False

    async def save_connection(
        self,
        db: AsyncSession,
        workspace_id: str,
        account_id: str,
        account_name: str,
        access_token: str,
        currency: str = "USD",
        timezone: str | None = None,
    ) -> str:
        """Save the Meta connection to the DB with encrypted tokens."""
        enc_token = encrypt(access_token)
        result = await db.execute(
            text(
                """
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     currency, timezone, access_token_enc, long_lived_token_enc,
                     is_active, last_sync_status)
                VALUES (:wid, 'meta', :aid, :aname, :curr, :tz, :tok, :ltok,
                        true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    access_token_enc = EXCLUDED.access_token_enc,
                    long_lived_token_enc = EXCLUDED.long_lived_token_enc,
                    is_active = true,
                    last_sync_status = 'pending',
                    connected_at = NOW()
                RETURNING id
                """
            ),
            {
                "wid": workspace_id,
                "aid": account_id,
                "aname": account_name,
                "curr": currency,
                "tz": timezone,
                "tok": enc_token,
                "ltok": enc_token,
            },
        )
        conn_id = str(result.fetchone()[0])
        await db.commit()
        logger.info("Meta connection saved: workspace=%s account=%s", workspace_id, account_id)
        return conn_id

    def get_decrypted_token(self, connection_row: dict) -> str | None:
        """Decrypt the token from a DB row for outbound API use."""
        enc = connection_row.get("long_lived_token_enc") or connection_row.get("access_token_enc")
        if not enc:
            return None
        return decrypt(enc)
