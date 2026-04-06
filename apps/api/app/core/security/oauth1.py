"""OAuth 1.0a HMAC-SHA1 signing helper."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import urllib.parse


def build_auth_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str = "",
    token_secret: str = "",
    additional_oauth_params: dict | None = None,
    query_params: dict | None = None,
) -> str:
    """Build OAuth 1.0a Authorization header with HMAC-SHA1 signature.

    Args:
        query_params: GET query parameters to include in the signature base
                      string. OAuth 1.0a requires ALL request params (OAuth
                      params + query params) to be signed together. Pass the
                      same dict you give to httpx ``params=``.
    """

    def pct(s: str) -> str:
        return urllib.parse.quote(str(s), safe="")

    oauth_params: dict[str, str] = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    if token:
        oauth_params["oauth_token"] = token
    if additional_oauth_params:
        oauth_params.update(additional_oauth_params)

    # Merge query params into the signing base (OAuth 1.0a spec requirement)
    all_params = dict(oauth_params)
    if query_params:
        all_params.update({str(k): str(v) for k, v in query_params.items()})

    param_string = "&".join(f"{pct(k)}={pct(v)}" for k, v in sorted(all_params.items()))
    base_string = f"{method.upper()}&{pct(url)}&{pct(param_string)}"
    signing_key = f"{pct(consumer_secret)}&{pct(token_secret)}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = signature
    return "OAuth " + ", ".join(f'{pct(k)}="{pct(v)}"' for k, v in sorted(oauth_params.items()))
