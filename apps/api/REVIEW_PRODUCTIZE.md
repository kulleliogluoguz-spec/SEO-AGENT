# PRODUCTIZATION REVIEW & COMPLETION AUDIT
## AI Growth OS — Full Verification + Gap Filling
## Save as: apps/api/REVIEW_PRODUCTIZE.md

You just completed the productization implementation.
Now conduct a THOROUGH audit of everything built.
Verify correctness end-to-end.
Complete ANYTHING missing, broken, or half-implemented.
DO NOT declare done until every single check below passes.
DO NOT ask for permission between steps.
Fix everything you find before moving forward.

---

## STEP 0: FULL SYSTEM AUDIT — READ EVERYTHING FIRST

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "============================================"
echo "BACKEND SERVICE FILES"
echo "============================================"
find "$BASE/apps/api/app/services" -name "*.py" | sort
echo ""

echo "============================================"
echo "BACKEND ENDPOINT FILES"
echo "============================================"
find "$BASE/apps/api/app/api/endpoints" -name "*.py" | sort
echo ""

echo "============================================"
echo "FRONTEND PAGES"
echo "============================================"
find "$BASE/apps/web/src/app/dashboard" -name "page.tsx" | sort
echo ""

echo "============================================"
echo "MAIN.PY ROUTER REGISTRATIONS"
echo "============================================"
grep -n "include_router\|from app.api" "$BASE/apps/api/app/main.py"
echo ""

echo "============================================"
echo "MAIN.PY CORS CONFIG"
echo "============================================"
grep -n "CORS\|allow_origins\|127.0.0.1" "$BASE/apps/api/app/main.py"
echo ""

echo "============================================"
echo "CURRENT .ENV VARIABLES"
echo "============================================"
cat "$BASE/apps/api/.env" | grep -v "^#" | grep -v "^$"
echo ""

echo "============================================"
echo "DATABASE TABLES"
echo "============================================"
python3 -c "
import asyncio, asyncpg, os
async def f():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    try:
        conn = await asyncpg.connect(url)
        rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
        [print(r['tablename']) for r in rows]
        await conn.close()
    except Exception as e:
        print(f'DB ERROR: {e}')
asyncio.run(f())
" 2>/dev/null
echo ""

echo "============================================"
echo "ENCRYPTION KEY SET?"
echo "============================================"
python3 -c "
import os
key = os.getenv('ENCRYPTION_KEY','')
if key:
    print(f'✅ ENCRYPTION_KEY set ({len(key)} chars)')
else:
    print('❌ ENCRYPTION_KEY MISSING')
" 2>/dev/null
echo ""

echo "============================================"
echo "IMPORT CHECKS"
echo "============================================"
cd "$BASE/apps/api"
python3 -c "from app.services.security.encryption import encrypt, decrypt; print('✅ encryption')" 2>/dev/null || echo "❌ encryption FAILED"
python3 -c "from app.services.integrations.meta_oauth import MetaOAuthService; print('✅ meta_oauth')" 2>/dev/null || echo "❌ meta_oauth FAILED"
python3 -c "from app.services.integrations.meta_ads_fetcher import MetaAdsFetcher; print('✅ meta_fetcher')" 2>/dev/null || echo "❌ meta_fetcher FAILED"
python3 -c "from app.services.integrations.google_ads_service import GoogleAdsOAuthService; print('✅ google_ads')" 2>/dev/null || echo "❌ google_ads FAILED"
python3 -c "from app.api.endpoints.integrations import router; print('✅ integrations_router')" 2>/dev/null || echo "❌ integrations_router FAILED"
python3 -c "from app.api.endpoints.workspace import router; print('✅ workspace_router')" 2>/dev/null || echo "❌ workspace_router FAILED"
python3 -c "from app.services.ai.model_config import call_ollama, ModelSelector; print('✅ model_config')" 2>/dev/null || echo "❌ model_config FAILED"
python3 -c "from app.services.automation.event_bus import EventBus; print('✅ event_bus')" 2>/dev/null || echo "❌ event_bus FAILED"
python3 -c "from app.services.discovery.discovery_engine import DiscoveryEngine; print('✅ discovery')" 2>/dev/null || echo "❌ discovery FAILED"
echo ""

echo "============================================"
echo "OLLAMA STATUS"
echo "============================================"
curl -s http://localhost:11434/api/tags | python3 -c \
  "import sys,json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; [print(m) for m in models]" 2>/dev/null
echo ""

echo "============================================"
echo "PACKAGE CHECK"
echo "============================================"
pip list 2>/dev/null | grep -E "facebook|google-ads|cryptography|sentry|loguru|twilio|faster.whisper|whisperx"
echo ""

echo "============================================"
echo "FILE SIZE CHECK (detect empty/stub files)"
echo "============================================"
for f in \
  "apps/api/app/services/security/encryption.py" \
  "apps/api/app/services/integrations/meta_oauth.py" \
  "apps/api/app/services/integrations/meta_ads_fetcher.py" \
  "apps/api/app/services/integrations/google_ads_service.py" \
  "apps/api/app/api/endpoints/integrations.py" \
  "apps/api/app/api/endpoints/workspace.py" \
  "apps/web/src/app/dashboard/integrations/page.tsx" \
  "apps/web/src/app/dashboard/setup/page.tsx"; do
  full="$BASE/$f"
  if [ -f "$full" ]; then
    lines=$(wc -l < "$full")
    if [ "$lines" -lt 20 ]; then
      echo "⚠️  TOO SHORT ($lines lines): $f"
    else
      echo "✅ $f ($lines lines)"
    fi
  else
    echo "❌ MISSING: $f"
  fi
done
```

After reading ALL output above, build a complete picture of what exists and what is missing.

---

## STEP 1: FIX ALL MISSING TABLES

Run regardless — IF NOT EXISTS is safe:

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 -c "
import asyncio, asyncpg, os

async def ensure():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS workspace_settings (
            workspace_id UUID PRIMARY KEY,
            company_name VARCHAR(500),
            industry VARCHAR(200),
            default_currency VARCHAR(10) DEFAULT 'USD',
            monthly_ad_budget NUMERIC(14,2),
            break_even_roas NUMERIC(10,4) DEFAULT 2.5,
            avg_order_value NUMERIC(12,2),
            cogs_per_unit NUMERIC(12,4) DEFAULT 0,
            shipping_cost NUMERIC(12,4) DEFAULT 0,
            return_rate NUMERIC(5,4) DEFAULT 0.05,
            meta_app_id_enc TEXT,
            meta_app_secret_enc TEXT,
            google_developer_token_enc TEXT,
            google_client_id_enc TEXT,
            google_client_secret_enc TEXT,
            twilio_account_sid_enc TEXT,
            twilio_auth_token_enc TEXT,
            twilio_phone_number VARCHAR(50),
            setup_completed BOOLEAN DEFAULT FALSE,
            setup_step INTEGER DEFAULT 1,
            slack_webhook_url TEXT,
            notification_email VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS ad_account_connections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            platform VARCHAR(20) NOT NULL,
            account_id VARCHAR(200) NOT NULL,
            account_name VARCHAR(500),
            currency VARCHAR(10) DEFAULT 'USD',
            timezone VARCHAR(100),
            access_token_enc TEXT,
            refresh_token_enc TEXT,
            long_lived_token_enc TEXT,
            token_expires_at TIMESTAMPTZ,
            token_type VARCHAR(50) DEFAULT 'user',
            scopes TEXT[],
            is_active BOOLEAN DEFAULT TRUE,
            last_sync_status VARCHAR(50) DEFAULT 'pending',
            last_sync_error TEXT,
            connected_at TIMESTAMPTZ DEFAULT NOW(),
            last_synced_at TIMESTAMPTZ,
            UNIQUE(workspace_id, platform, account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_connections_workspace
            ON ad_account_connections(workspace_id, platform, is_active);

        CREATE TABLE IF NOT EXISTS platform_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            source_module VARCHAR(50) NOT NULL,
            workspace_id UUID,
            payload JSONB DEFAULT '{}',
            processed_by TEXT[] DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_events_workspace_type
            ON platform_events(workspace_id, event_type, created_at DESC);

        CREATE TABLE IF NOT EXISTS product_costs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            product_name VARCHAR(500),
            sku VARCHAR(255),
            cogs NUMERIC(12,4) NOT NULL DEFAULT 0,
            shipping_cost NUMERIC(12,4) DEFAULT 0,
            return_rate NUMERIC(5,4) DEFAULT 0.05,
            currency VARCHAR(10) DEFAULT 'USD',
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            full_name VARCHAR(500),
            company_name VARCHAR(500),
            email VARCHAR(255),
            phone VARCHAR(100),
            industry VARCHAR(200),
            source VARCHAR(100) DEFAULT 'manual',
            tags TEXT[],
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_contacts_workspace ON contacts(workspace_id);

        CREATE TABLE IF NOT EXISTS leads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contact_id UUID REFERENCES contacts(id),
            workspace_id UUID NOT NULL,
            status VARCHAR(50) DEFAULT 'new',
            qualification_score INTEGER DEFAULT 0,
            category VARCHAR(50),
            ai_summary TEXT,
            ai_intent VARCHAR(100),
            ai_urgency VARCHAR(50),
            ai_next_action TEXT,
            estimated_deal_value NUMERIC(14,2),
            notes TEXT,
            last_contact_date TIMESTAMPTZ,
            call_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_leads_workspace ON leads(workspace_id, status);

        CREATE TABLE IF NOT EXISTS lead_timeline (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id UUID REFERENCES leads(id),
            event_type VARCHAR(100),
            title VARCHAR(500),
            description TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS calls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            contact_id UUID REFERENCES contacts(id),
            lead_id UUID REFERENCES leads(id),
            direction VARCHAR(20) DEFAULT 'outbound',
            status VARCHAR(50) DEFAULT 'pending',
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            duration_seconds INTEGER,
            recording_path VARCHAR(1000),
            recording_size_mb NUMERIC(10,2),
            transcription_status VARCHAR(50) DEFAULT 'pending',
            analysis_status VARCHAR(50) DEFAULT 'pending',
            provider VARCHAR(50) DEFAULT 'manual_upload',
            provider_call_id VARCHAR(255),
            consent_given BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_calls_workspace ON calls(workspace_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS call_transcripts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            call_id UUID REFERENCES calls(id),
            speaker VARCHAR(50) DEFAULT 'SPEAKER_0',
            text TEXT NOT NULL,
            start_time NUMERIC(10,3) DEFAULT 0,
            end_time NUMERIC(10,3) DEFAULT 0,
            confidence NUMERIC(5,4),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS call_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            call_id UUID REFERENCES calls(id) UNIQUE,
            overall_sentiment VARCHAR(50),
            customer_sentiment VARCHAR(50),
            intent VARCHAR(100),
            urgency VARCHAR(50),
            objections TEXT[],
            buying_signals TEXT[],
            action_items TEXT[],
            qualification_score INTEGER DEFAULT 0,
            qualification_category VARCHAR(50),
            summary TEXT,
            key_points TEXT[],
            next_action TEXT,
            follow_up_days INTEGER DEFAULT 3,
            ai_model_used VARCHAR(100),
            processing_duration_ms INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            file_path VARCHAR(1000),
            file_name VARCHAR(500),
            file_type VARCHAR(50),
            invoice_number VARCHAR(255),
            invoice_date DATE,
            due_date DATE,
            vendor_name VARCHAR(500),
            vendor_tax_id VARCHAR(100),
            customer_name VARCHAR(500),
            currency VARCHAR(10) DEFAULT 'TRY',
            subtotal NUMERIC(14,2),
            tax_amount NUMERIC(14,2),
            total_amount NUMERIC(14,2),
            direction VARCHAR(20) DEFAULT 'incoming',
            category VARCHAR(100) DEFAULT 'general',
            vat_rate NUMERIC(5,2),
            vat_amount NUMERIC(14,2),
            is_deductible BOOLEAN DEFAULT FALSE,
            estimated_tax_impact TEXT,
            extraction_status VARCHAR(50) DEFAULT 'pending',
            confidence_score NUMERIC(5,4),
            needs_human_review BOOLEAN DEFAULT FALSE,
            human_reviewed BOOLEAN DEFAULT FALSE,
            ai_notes TEXT,
            line_items JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_invoices_workspace ON invoices(workspace_id, invoice_date DESC NULLS LAST);

        CREATE TABLE IF NOT EXISTS ai_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            module VARCHAR(100),
            feedback_type VARCHAR(50),
            original_recommendation JSONB,
            user_action JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS ai_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            memory_type VARCHAR(50),
            module VARCHAR(100),
            key VARCHAR(255),
            value JSONB,
            confidence NUMERIC(5,4) DEFAULT 0.5,
            observation_count INTEGER DEFAULT 1,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(workspace_id, module, key)
        );

        CREATE TABLE IF NOT EXISTS company_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL UNIQUE,
            company_name TEXT,
            industry TEXT,
            stage TEXT,
            business_model TEXT,
            primary_goal TEXT,
            biggest_challenge TEXT,
            target_customer TEXT,
            avg_order_value NUMERIC(12,2),
            monthly_ad_spend NUMERIC(12,2),
            current_roas NUMERIC(10,4),
            break_even_roas NUMERIC(10,4),
            active_channels TEXT[],
            ai_summary TEXT,
            ai_insights TEXT[],
            discovery_transcript JSONB DEFAULT '[]'::jsonb,
            discovery_completed BOOLEAN DEFAULT FALSE,
            discovery_completed_at TIMESTAMPTZ,
            question_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    ''')

    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    names = [r['tablename'] for r in rows]
    required = [
        'workspace_settings','ad_account_connections','platform_events',
        'product_costs','contacts','leads','lead_timeline',
        'calls','call_transcripts','call_analysis',
        'invoices','ai_feedback','ai_memory','company_profiles'
    ]
    print('=== TABLE STATUS ===')
    all_ok = True
    for t in required:
        ok = t in names
        print(f\"{'✅' if ok else '❌'} {t}\")
        if not ok: all_ok = False
    print(f\"{'✅ All tables OK' if all_ok else '❌ Some missing'}\")
    await conn.close()

asyncio.run(ensure())
"
```

---

## STEP 2: FIX ENCRYPTION KEY IF MISSING

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

# Check if key exists
KEY_EXISTS=$(grep "ENCRYPTION_KEY=" .env | grep -v "^#" | grep -v "=$" | wc -l)

if [ "$KEY_EXISTS" -eq 0 ]; then
  echo "ENCRYPTION_KEY missing — generating..."
  KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo "ENCRYPTION_KEY=$KEY" >> .env
  echo "✅ ENCRYPTION_KEY added to .env"
else
  echo "✅ ENCRYPTION_KEY already set"
fi

# Install cryptography if missing
pip install cryptography --quiet
pip install facebook-business --quiet
pip install google-ads --quiet
pip install sentry-sdk[fastapi] --quiet
pip install loguru --quiet

# Verify encryption works
python3 -c "
from app.services.security.encryption import encrypt, decrypt
t = 'test-secret-token-abc-123'
enc = encrypt(t)
dec = decrypt(enc)
assert dec == t, f'MISMATCH: {dec} != {t}'
print('✅ Encryption/decryption working')
"
```

---

## STEP 3: CHECK AND FIX EACH SERVICE FILE

For each file below — check if it exists AND has real content (not just a stub).
If missing or <30 lines — create the full implementation now.

### 3A: Check security directory

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

# Must exist:
ls "$BASE/app/services/security/__init__.py" 2>/dev/null || touch "$BASE/app/services/security/__init__.py"
ls "$BASE/app/services/integrations/__init__.py" 2>/dev/null || touch "$BASE/app/services/integrations/__init__.py"

# Check encryption.py
lines=$(wc -l < "$BASE/app/services/security/encryption.py" 2>/dev/null || echo "0")
echo "encryption.py: $lines lines"
```

If encryption.py is missing or <40 lines, create it:

```python
# File: apps/api/app/services/security/encryption.py
"""Token Encryption using Fernet (AES-128-CBC + HMAC-SHA256)."""
import os, logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionService:
    _fernet = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            key = os.getenv("ENCRYPTION_KEY", "")
            if not key:
                logger.warning("ENCRYPTION_KEY not set — using temp key (DO NOT USE IN PRODUCTION)")
                key = Fernet.generate_key().decode()
            cls._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> Optional[str]:
        if not plaintext:
            return None
        try:
            return cls._get_fernet().encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return None

    @classmethod
    def decrypt(cls, ciphertext: str) -> Optional[str]:
        if not ciphertext:
            return None
        try:
            return cls._get_fernet().decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token or wrong key")
            return None
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return None

    @classmethod
    def generate_key(cls) -> str:
        return Fernet.generate_key().decode()


def encrypt(plaintext: str) -> Optional[str]:
    return EncryptionService.encrypt(plaintext)

def decrypt(ciphertext: str) -> Optional[str]:
    return EncryptionService.decrypt(ciphertext)
```

### 3B: Check meta_oauth.py

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/integrations/meta_oauth.py" 2>/dev/null || echo "0")
echo "meta_oauth.py: $lines lines"
```

If <60 lines, create the full implementation:

```python
# File: apps/api/app/services/integrations/meta_oauth.py
"""Meta Ads OAuth + token management."""
import os, logging, requests
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.security.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)
META_GRAPH = "https://graph.facebook.com/v19.0"
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")


class MetaOAuthService:

    def get_oauth_url(self, redirect_uri: str, state: str) -> str:
        scopes = "ads_management,ads_read,business_management"
        return (
            f"https://www.facebook.com/v19.0/dialog/oauth"
            f"?client_id={META_APP_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        r = requests.get(f"{META_GRAPH}/oauth/access_token", params={
            "client_id": META_APP_ID, "client_secret": META_APP_SECRET,
            "redirect_uri": redirect_uri, "code": code,
        }, timeout=30)
        if not r.ok:
            raise ValueError(f"Meta token exchange failed: {r.text[:200]}")
        return r.json()

    def get_long_lived_token(self, short_token: str) -> dict:
        r = requests.get(f"{META_GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID, "client_secret": META_APP_SECRET,
            "fb_exchange_token": short_token,
        }, timeout=30)
        if not r.ok:
            raise ValueError(f"Long-lived token exchange failed: {r.text[:200]}")
        return r.json()

    def get_ad_accounts(self, access_token: str) -> list[dict]:
        r = requests.get(f"{META_GRAPH}/me/adaccounts", params={
            "access_token": access_token,
            "fields": "id,name,currency,timezone_name,account_status",
        }, timeout=30)
        if not r.ok:
            logger.error(f"Meta ad accounts failed: {r.text[:200]}")
            return []
        return [
            {
                "account_id": a.get("id"),
                "account_name": a.get("name"),
                "currency": a.get("currency", "USD"),
                "timezone": a.get("timezone_name"),
                "status": a.get("account_status"),
            }
            for a in r.json().get("data", [])
        ]

    def validate_token(self, access_token: str) -> bool:
        try:
            r = requests.get(f"{META_GRAPH}/me", params={
                "access_token": access_token, "fields": "id,name"
            }, timeout=10)
            return r.ok
        except Exception:
            return False

    async def save_connection(self, db: AsyncSession, workspace_id: str,
                               account_id: str, account_name: str,
                               access_token: str, currency: str = "USD",
                               timezone: str = None) -> str:
        enc = encrypt(access_token)
        result = await db.execute(
            text("""
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     currency, timezone, access_token_enc, long_lived_token_enc,
                     is_active, last_sync_status)
                VALUES (:wid, 'meta', :aid, :aname, :curr, :tz, :tok, :tok, true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id) DO UPDATE SET
                    account_name=:aname, access_token_enc=:tok,
                    long_lived_token_enc=:tok, is_active=true,
                    last_sync_status='pending', connected_at=NOW()
                RETURNING id
            """),
            {"wid": workspace_id, "aid": account_id, "aname": account_name,
             "curr": currency, "tz": timezone, "tok": enc}
        )
        conn_id = str(result.fetchone()[0])
        await db.commit()
        return conn_id

    def get_decrypted_token(self, connection_row: dict) -> Optional[str]:
        enc = connection_row.get("long_lived_token_enc") or connection_row.get("access_token_enc")
        return decrypt(enc) if enc else None
```

### 3C: Check meta_ads_fetcher.py

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/integrations/meta_ads_fetcher.py" 2>/dev/null || echo "0")
echo "meta_ads_fetcher.py: $lines lines"
```

If <60 lines, create full implementation:

```python
# File: apps/api/app/services/integrations/meta_ads_fetcher.py
"""Meta Ads data fetcher — real campaign + performance data."""
import logging, requests
from datetime import date, timedelta

logger = logging.getLogger(__name__)
META_GRAPH = "https://graph.facebook.com/v19.0"


class MetaAdsFetcher:

    def __init__(self, access_token: str):
        self.token = access_token
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        p = {"access_token": self.token}
        if params:
            p.update(params)
        try:
            r = self.session.get(f"{META_GRAPH}/{endpoint}", params=p, timeout=60)
            if not r.ok:
                logger.error(f"Meta API {r.status_code}: {r.text[:200]}")
                return {}
            return r.json()
        except Exception as e:
            logger.error(f"Meta API request failed: {e}")
            return {}

    def get_campaigns(self, account_id: str, limit: int = 100) -> list[dict]:
        data = self._get(f"{account_id}/campaigns", {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget,created_time",
            "limit": limit,
        })
        return data.get("data", [])

    def get_campaign_insights(self, campaign_id: str,
                               date_from: date, date_to: date) -> dict:
        data = self._get(f"{campaign_id}/insights", {
            "fields": "impressions,clicks,spend,reach,frequency,actions,action_values,ctr,purchase_roas",
            "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
            "level": "campaign",
        })
        rows = data.get("data", [])
        if not rows:
            return {}
        row = rows[0]
        spend = float(row.get("spend", 0))
        action_values = row.get("action_values", [])
        revenue = sum(
            float(a.get("value", 0)) for a in action_values
            if "purchase" in a.get("action_type", "")
        )
        actions = row.get("actions", [])
        conversions = sum(
            float(a.get("value", 0)) for a in actions
            if a.get("action_type") in ["purchase", "omni_purchase"]
        )
        roas_data = row.get("purchase_roas", [])
        roas = float(roas_data[0].get("value", 0)) if roas_data else (revenue / spend if spend > 0 else 0)
        return {
            "campaign_id": campaign_id,
            "spend": spend,
            "impressions": int(row.get("impressions", 0)),
            "clicks": int(row.get("clicks", 0)),
            "conversions": conversions,
            "revenue": revenue,
            "roas": round(roas, 4),
            "cpa": round(spend / conversions if conversions > 0 else 0, 2),
            "ctr": round(float(row.get("ctr", 0)), 4),
            "frequency": round(float(row.get("frequency", 0)), 2),
        }

    def get_account_summary(self, account_id: str, days: int = 7) -> dict:
        date_to = date.today()
        date_from = date_to - timedelta(days=days)
        data = self._get(f"{account_id}/insights", {
            "fields": "spend,impressions,clicks,actions,action_values,purchase_roas",
            "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
            "level": "account",
        })
        rows = data.get("data", [])
        if not rows:
            return {"account_id": account_id, "spend": 0, "roas": 0, "period_days": days}
        row = rows[0]
        spend = float(row.get("spend", 0))
        action_values = row.get("action_values", [])
        revenue = sum(float(a.get("value", 0)) for a in action_values if "purchase" in a.get("action_type", ""))
        roas_data = row.get("purchase_roas", [])
        roas = float(roas_data[0].get("value", 0)) if roas_data else (revenue / spend if spend > 0 else 0)
        return {"account_id": account_id, "spend": spend, "revenue": revenue,
                "roas": round(roas, 4), "period_days": days}

    def sync_all_campaigns(self, account_id: str, days: int = 7) -> list[dict]:
        campaigns = self.get_campaigns(account_id)
        date_to = date.today()
        date_from = date_to - timedelta(days=days)
        results = []
        for camp in campaigns:
            insights = self.get_campaign_insights(camp.get("id"), date_from, date_to)
            results.append({"campaign": camp, "insights": insights})
        return results
```

### 3D: Check google_ads_service.py

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/integrations/google_ads_service.py" 2>/dev/null || echo "0")
echo "google_ads_service.py: $lines lines"
```

If <60 lines, create full implementation:

```python
# File: apps/api/app/services/integrations/google_ads_service.py
"""Google Ads OAuth2 + data fetching."""
import os, logging
from typing import Optional
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.security.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_DEVELOPER_TOKEN = os.getenv("GOOGLE_DEVELOPER_TOKEN", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/google/callback")


class GoogleAdsOAuthService:

    def get_oauth_url(self, state: str) -> str:
        try:
            from google_auth_oauthlib.flow import Flow
            flow = Flow.from_client_config(
                {"web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }},
                scopes=["https://www.googleapis.com/auth/adwords"],
            )
            flow.redirect_uri = GOOGLE_REDIRECT_URI
            auth_url, _ = flow.authorization_url(
                access_type="offline", state=state, prompt="consent"
            )
            return auth_url
        except Exception as e:
            raise ValueError(f"Google OAuth URL generation failed: {e}")

    def exchange_code_for_tokens(self, code: str) -> dict:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(
            {"web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }},
            scopes=["https://www.googleapis.com/auth/adwords"],
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
        }

    def get_accessible_customers(self, refresh_token: str) -> list[dict]:
        if not GOOGLE_DEVELOPER_TOKEN:
            return []
        try:
            from google.ads.googleads.client import GoogleAdsClient
            client = GoogleAdsClient.load_from_dict({
                "developer_token": GOOGLE_DEVELOPER_TOKEN,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "use_proto_plus": True,
            })
            svc = client.get_service("CustomerService")
            response = svc.list_accessible_customers()
            return [
                {"customer_id": rn.split("/")[-1],
                 "account_name": f"Google Ads ({rn.split('/')[-1]})"}
                for rn in response.resource_names
            ]
        except Exception as e:
            logger.error(f"Google accessible customers failed: {e}")
            return []

    async def save_connection(self, db: AsyncSession, workspace_id: str,
                               account_id: str, account_name: str,
                               access_token: str, refresh_token: str) -> str:
        result = await db.execute(
            text("""
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     access_token_enc, refresh_token_enc, is_active, last_sync_status)
                VALUES (:wid, 'google', :aid, :aname, :atk, :rtk, true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id) DO UPDATE SET
                    account_name=:aname, access_token_enc=:atk,
                    refresh_token_enc=:rtk, is_active=true, connected_at=NOW()
                RETURNING id
            """),
            {"wid": workspace_id, "aid": account_id, "aname": account_name,
             "atk": encrypt(access_token) if access_token else None,
             "rtk": encrypt(refresh_token) if refresh_token else None}
        )
        conn_id = str(result.fetchone()[0])
        await db.commit()
        return conn_id


class GoogleAdsDataFetcher:

    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token

    def _get_client(self, customer_id: str = None):
        from google.ads.googleads.client import GoogleAdsClient
        config = {
            "developer_token": GOOGLE_DEVELOPER_TOKEN,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": self.refresh_token,
            "use_proto_plus": True,
        }
        if customer_id:
            config["login_customer_id"] = customer_id
        return GoogleAdsClient.load_from_dict(config)

    def get_campaign_performance(self, customer_id: str, days: int = 7) -> list[dict]:
        try:
            client = self._get_client(customer_id)
            ga_service = client.get_service("GoogleAdsService")
            date_to = date.today()
            date_from = date_to - timedelta(days=days)
            query = f"""
                SELECT campaign.id, campaign.name,
                    metrics.impressions, metrics.clicks, metrics.cost_micros,
                    metrics.conversions, metrics.conversions_value, metrics.ctr
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                  AND segments.date BETWEEN '{date_from}' AND '{date_to}'
                ORDER BY metrics.cost_micros DESC LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            results = []
            for row in response:
                spend = row.metrics.cost_micros / 1_000_000
                revenue = row.metrics.conversions_value
                conversions = row.metrics.conversions
                roas = revenue / spend if spend > 0 else 0
                results.append({
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "spend": round(spend, 2),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "conversions": conversions,
                    "revenue": round(revenue, 2),
                    "roas": round(roas, 4),
                    "cpa": round(spend / conversions if conversions > 0 else 0, 2),
                    "ctr": round(row.metrics.ctr, 4),
                    "period_days": days,
                })
            return results
        except Exception as e:
            logger.error(f"Google Ads performance failed: {e}")
            return []
```

---

## STEP 4: CHECK AND FIX ENDPOINT FILES

### 4A: Check integrations.py endpoint

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/api/endpoints/integrations.py" 2>/dev/null || echo "0")
echo "integrations.py: $lines lines"
```

If missing or <100 lines, create the complete endpoint file as specified in PRODUCTIZE.md.
The file must have these routes:
- GET /api/v1/integrations/connections
- DELETE /api/v1/integrations/connections/{id}
- GET /api/v1/integrations/meta/authorize
- GET /api/v1/integrations/meta/callback
- POST /api/v1/integrations/meta/connect-token
- GET /api/v1/integrations/meta/sync/{id}
- GET /api/v1/integrations/google/authorize
- GET /api/v1/integrations/google/callback
- POST /api/v1/integrations/google/connect-token
- GET /api/v1/integrations/google/sync/{id}
- POST /api/v1/integrations/sync-all

### 4B: Check workspace.py endpoint

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/api/endpoints/workspace.py" 2>/dev/null || echo "0")
echo "workspace.py: $lines lines"
```

If missing or <50 lines, create it with these routes:
- GET /api/v1/workspace/settings
- PUT /api/v1/workspace/settings
- GET /api/v1/workspace/setup-status

---

## STEP 5: VERIFY MAIN.PY IS COMPLETE

```bash
cat "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/main.py" | grep -n "include_router\|from app.api\|CORS\|allow_origins"
```

Required registrations — add any missing ones:

```python
# These must ALL be in main.py:
from app.api.endpoints.integrations import router as integrations_router
from app.api.endpoints.workspace import router as workspace_router
app.include_router(integrations_router)
app.include_router(workspace_router)
```

CORS must include 127.0.0.1:
```python
# CORSMiddleware allow_origins must include:
"http://localhost:3001",
"http://127.0.0.1:3001",
"http://localhost:3000",
"http://127.0.0.1:3000",
```

Also add to main.py startup:
```python
from app.core.logging_config import setup_logging
setup_logging()
```

Check and create `apps/api/app/core/logging_config.py` if missing:

```python
# File: apps/api/app/core/logging_config.py
"""Structured logging + Sentry initialization."""
import os, sys, logging
from loguru import logger

def setup_logging():
    logger.remove()
    logger.add(sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO"), colorize=True)
    logger.add("/tmp/ai-growth-os.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} — {message}",
        rotation="1 day", retention="7 days", level="DEBUG")

    sentry_dsn = os.getenv("SENTRY_DSN", "")
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            send_default_pii=False,
        )
        logger.info("Sentry initialized")
    return logger
```

---

## STEP 6: VERIFY .ENV HAS ALL REQUIRED VARIABLES

```bash
ENV_FILE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"

# Check and add missing variables
add_if_missing() {
  local key=$1
  local value=$2
  if ! grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    echo "${key}=${value}" >> "$ENV_FILE"
    echo "Added: ${key}"
  fi
}

add_if_missing "ENCRYPTION_KEY" "$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
add_if_missing "META_APP_ID" ""
add_if_missing "META_APP_SECRET" ""
add_if_missing "GOOGLE_CLIENT_ID" ""
add_if_missing "GOOGLE_CLIENT_SECRET" ""
add_if_missing "GOOGLE_DEVELOPER_TOKEN" ""
add_if_missing "GOOGLE_REDIRECT_URI" "http://localhost:8000/api/v1/integrations/google/callback"
add_if_missing "BACKEND_URL" "http://localhost:8000"
add_if_missing "FRONTEND_URL" "http://127.0.0.1:3001"
add_if_missing "SENTRY_DSN" ""
add_if_missing "ENVIRONMENT" "development"
add_if_missing "LOG_LEVEL" "INFO"

echo "✅ .env check complete"
cat "$ENV_FILE" | grep -v "^#" | grep -v "^$" | head -40
```

---

## STEP 7: CHECK AND FIX FRONTEND PAGES

### 7A: Check integrations page

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src/app/dashboard/integrations/page.tsx" 2>/dev/null || echo "0")
echo "integrations/page.tsx: $lines lines"
```

If missing or <100 lines, create the full page as specified in PRODUCTIZE.md.
The page must:
- Show list of connected accounts
- Have tabs: Connected | + Meta Ads | + Google Ads
- Support System User Token connection (Option B — no OAuth needed)
- Support refresh token connection for Google
- Show sync button + last sync time per connection
- Show disconnect button
- Handle OAuth callback params (status=success/error in URL)

### 7B: Check setup wizard page

```bash
lines=$(wc -l < "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src/app/dashboard/setup/page.tsx" 2>/dev/null || echo "0")
echo "setup/page.tsx: $lines lines"
```

If missing or <100 lines, create the 4-step setup wizard:
- Step 1: Company info (name, industry, budget)
- Step 2: Connect ad accounts (links to integrations page)
- Step 3: Product costs (COGS, shipping, return rate)
- Step 4: Done — go to dashboard

---

## STEP 8: CHECK SIDEBAR HAS NEW LINKS

```bash
grep -rn "integrations\|setup\|Integrations\|Setup" \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src" \
  --include="*.tsx" | grep -v "node_modules" | grep -v "dashboard/integrations/page" | head -10
```

Find the sidebar component:
```bash
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src" \
  -name "*.tsx" -not -path "*/node_modules/*" \
  | xargs grep -l "href.*dashboard\|Link.*dashboard" 2>/dev/null \
  | head -5
```

Open sidebar file and verify these links exist:
- `/dashboard/integrations` (labeled "Integrations" or "Ad Accounts")
- `/dashboard/setup` (labeled "Setup" or "Getting Started")

If missing, add them following the exact same pattern as existing nav items.

---

## STEP 9: LIVE BACKEND TEST

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

# Kill and restart fresh
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 4

cd "$BASE/apps/api"
uvicorn app.main:app --reload --port 8000 > /tmp/review_startup.log 2>&1 &
sleep 14

# Check startup errors
echo "=== STARTUP ERRORS ==="
grep -E "ERROR|Import|Module|Traceback|Exception" /tmp/review_startup.log | head -20

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token', d.get('detail','FAILED')))" 2>/dev/null)

echo "Token: ${TOKEN:0:40}..."

if [[ "$TOKEN" == *"FAILED"* ]] || [[ -z "$TOKEN" ]]; then
  echo "❌ Login failed. Backend startup log:"
  cat /tmp/review_startup.log | tail -30
  exit 1
fi

# Test all endpoints
echo ""
echo "=== ENDPOINT STATUS ==="
PASS=0; FAIL=0
for ep in \
  "GET /health" \
  "GET /api/v1/integrations/connections" \
  "GET /api/v1/workspace/settings" \
  "GET /api/v1/workspace/setup-status" \
  "GET /api/v1/system/health" \
  "GET /api/v1/ads/campaigns" \
  "GET /api/v1/ads/portfolio/summary" \
  "GET /api/v1/ads/profitability/settings" \
  "GET /api/v1/ads/profitability/analysis?avg_order_value=50" \
  "GET /api/v1/calls" \
  "GET /api/v1/calls/leads" \
  "GET /api/v1/finance/invoices" \
  "GET /api/v1/finance/dashboard?months=3" \
  "GET /api/v1/discovery/status" \
  "GET /api/v1/ai-learning/summary" \
  "GET /api/v1/twitter/accounts"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  status=$(curl -s -o /tmp/r.json -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)
  if [[ "$status" == "200" ]] || [[ "$status" == "201" ]]; then
    echo "✅ $status $ep"
    PASS=$((PASS+1))
  else
    echo "❌ $status $ep"
    python3 -c "import json; d=json.load(open('/tmp/r.json')); print('  →',str(d)[:100])" 2>/dev/null
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"

# Fix every failed endpoint before proceeding
```

For every ❌ endpoint:
1. Read the error JSON
2. Find the root cause in the Python file
3. Fix it (missing import, DB error, wrong table name, etc.)
4. Re-test

---

## STEP 10: ENCRYPTION END-TO-END TEST

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

python3 -c "
import asyncio, asyncpg, os
from app.services.security.encryption import encrypt, decrypt

# Test 1: Basic encrypt/decrypt
secret = 'EAAtest_meta_token_xyz123'
enc = encrypt(secret)
dec = decrypt(enc)
assert dec == secret, f'Basic test FAILED: {dec}'
print('✅ Basic encrypt/decrypt working')

# Test 2: Decrypt None gracefully
result = decrypt(None)
assert result is None
print('✅ None handling working')

# Test 3: Wrong data gracefully
result = decrypt('not-valid-ciphertext')
assert result is None
print('✅ Invalid ciphertext handled gracefully')

print('✅ All encryption tests passed')
"
```

---

## STEP 11: META CONNECTION SIMULATION TEST

Test that the System User Token flow works end-to-end (without real Meta credentials):

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Test: connect with invalid token — should return clear error, not 500
echo "=== META TOKEN VALIDATION TEST ==="
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/integrations/meta/connect-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"access_token":"INVALID_TOKEN_FOR_TESTING"}')
echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print('Response:', str(d)[:100])"
# Should return 400 with a clear error message, not 500

# Test: workspace settings save
echo "=== WORKSPACE SETTINGS TEST ==="
RESULT=$(curl -s -o /tmp/ws.json -w "%{http_code}" \
  -X PUT http://localhost:8000/api/v1/workspace/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Test Co","industry":"E-commerce","monthly_ad_budget":10000}')
echo "Status: $RESULT"
cat /tmp/ws.json

# Verify it saved
RESULT=$(curl -s http://localhost:8000/api/v1/workspace/settings \
  -H "Authorization: Bearer $TOKEN")
echo "Settings:" && echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('settings',{}).get('company_name','NOT SAVED'))"
```

---

## STEP 12: FRONTEND BUILD + TYPE CHECK

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

cd "$BASE/apps/web"

echo "=== TypeScript Check ==="
npx tsc --noEmit 2>&1 | grep "error TS" | head -20
TS_ERRORS=$(npx tsc --noEmit 2>&1 | grep "error TS" | wc -l)
echo "TypeScript errors: $TS_ERRORS"

echo ""
echo "=== Next.js Build ==="
npx next build 2>&1 | grep -E "✓ Compiled|error|Error|Route" | tail -20

echo ""
echo "=== Sentry Config Files ==="
ls sentry.client.config.ts 2>/dev/null && echo "✅ sentry.client.config.ts" || echo "❌ sentry.client.config.ts missing"
ls sentry.server.config.ts 2>/dev/null && echo "✅ sentry.server.config.ts" || echo "❌ sentry.server.config.ts missing"
```

Fix all TypeScript errors before proceeding.
Common fixes:
- Add `'use client'` directive if using hooks
- Fix `any` types with proper interfaces
- Fix missing imports

---

## STEP 13: BACKEND LINT FIX

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

# Auto-fix what can be fixed
ruff check app/ --fix 2>/dev/null

# Show remaining issues
ISSUES=$(ruff check app/ 2>&1 | grep -v "^$" | wc -l)
echo "Remaining lint issues: $ISSUES"

if [ "$ISSUES" -gt 5 ]; then
  ruff check app/ 2>&1 | head -30
fi
```

---

## STEP 14: FULL FINAL VERIFICATION

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           FINAL PRODUCTIZATION VERIFICATION               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# === DB TABLES ===
echo "--- DATABASE TABLES ---"
python3 -c "
import asyncio, asyncpg, os
async def f():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL','').replace('+asyncpg',''))
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
    names = [r['tablename'] for r in rows]
    required = [
        'workspace_settings','ad_account_connections','platform_events',
        'product_costs','contacts','leads','lead_timeline',
        'calls','call_transcripts','call_analysis',
        'invoices','ai_feedback','ai_memory','company_profiles'
    ]
    ok = 0
    for t in required:
        if t in names:
            print(f'  ✅ {t}'); ok += 1
        else:
            print(f'  ❌ {t} MISSING')
    print(f'Tables: {ok}/{len(required)}')
    await conn.close()
asyncio.run(f())
" 2>/dev/null
echo ""

# === IMPORTS ===
echo "--- PYTHON IMPORTS ---"
cd "$BASE/apps/api"
python3 -c "from app.services.security.encryption import encrypt, decrypt; enc=encrypt('test'); assert decrypt(enc)=='test'; print('  ✅ encryption')" 2>/dev/null || echo "  ❌ encryption"
python3 -c "from app.services.integrations.meta_oauth import MetaOAuthService; print('  ✅ meta_oauth')" 2>/dev/null || echo "  ❌ meta_oauth"
python3 -c "from app.services.integrations.meta_ads_fetcher import MetaAdsFetcher; print('  ✅ meta_fetcher')" 2>/dev/null || echo "  ❌ meta_fetcher"
python3 -c "from app.services.integrations.google_ads_service import GoogleAdsOAuthService; print('  ✅ google_ads')" 2>/dev/null || echo "  ❌ google_ads"
python3 -c "from app.api.endpoints.integrations import router; print(f'  ✅ integrations ({len(router.routes)} routes)')" 2>/dev/null || echo "  ❌ integrations_router"
python3 -c "from app.api.endpoints.workspace import router; print(f'  ✅ workspace ({len(router.routes)} routes)')" 2>/dev/null || echo "  ❌ workspace_router"
echo ""

# === API ENDPOINTS ===
echo "--- API ENDPOINTS ---"
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 4
cd "$BASE/apps/api"
uvicorn app.main:app --port 8000 > /tmp/final_v.log 2>&1 &
sleep 12

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

PASS=0; FAIL=0
for ep in \
  "GET /health" \
  "GET /api/v1/integrations/connections" \
  "GET /api/v1/workspace/settings" \
  "GET /api/v1/workspace/setup-status" \
  "GET /api/v1/system/health" \
  "GET /api/v1/ads/campaigns" \
  "GET /api/v1/calls" \
  "GET /api/v1/finance/dashboard?months=3" \
  "GET /api/v1/discovery/status" \
  "GET /api/v1/ai-learning/summary"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)
  if [[ "$status" == "200" ]]; then
    echo "  ✅ $status $ep"; PASS=$((PASS+1))
  else
    echo "  ❌ $status $ep"; FAIL=$((FAIL+1))
  fi
done
echo "  Endpoints: $PASS passed, $FAIL failed"
echo ""

# === FRONTEND FILES ===
echo "--- FRONTEND PAGES ---"
for page in \
  "dashboard/integrations/page.tsx" \
  "dashboard/setup/page.tsx" \
  "dashboard/system/page.tsx" \
  "dashboard/company-intelligence/page.tsx" \
  "dashboard/ads/profitability/page.tsx" \
  "dashboard/calls/page.tsx" \
  "dashboard/finance/page.tsx" \
  "dashboard/ai-learning/page.tsx"; do
  full="$BASE/apps/web/src/app/$page"
  if [ -f "$full" ]; then
    lines=$(wc -l < "$full")
    echo "  ✅ $page ($lines lines)"
  else
    echo "  ❌ MISSING: $page"
  fi
done
echo ""

# === ENCRYPTION ===
echo "--- ENCRYPTION ---"
cd "$BASE/apps/api"
python3 -c "
import os
from app.services.security.encryption import encrypt, decrypt
key = os.getenv('ENCRYPTION_KEY','')
if key:
    test = 'secret-token-xyz'
    enc = encrypt(test)
    dec = decrypt(enc)
    if dec == test:
        print(f'  ✅ Encryption working (key: {len(key)} chars)')
    else:
        print('  ❌ Encryption FAILED — decrypt mismatch')
else:
    print('  ❌ ENCRYPTION_KEY not set')
" 2>/dev/null
echo ""

# === OVERALL RESULT ===
if [ "$FAIL" -eq 0 ]; then
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║   ✅  ALL CHECKS PASSED — PLATFORM IS PRODUCT-READY       ║"
  echo "║                                                            ║"
  echo "║   WHAT YOU CAN DO NOW:                                     ║"
  echo "║   1. Go to /dashboard/setup — complete onboarding wizard  ║"
  echo "║   2. Go to /dashboard/integrations — connect Meta Ads     ║"
  echo "║      Option B: paste System User Token → auto-discovers   ║"
  echo "║   3. Click Sync → real campaign data loads in seconds     ║"
  echo "║   4. Go to Ad Analytics → real ROAS + kill/scale signals  ║"
  echo "║   5. For Google: need Developer Token + Refresh Token     ║"
  echo "╚════════════════════════════════════════════════════════════╝"
else
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║   ❌  $FAIL CHECKS FAILED — FIX BEFORE USING WITH CLIENT  ║"
  echo "╚════════════════════════════════════════════════════════════╝"
fi

# === COMMIT ===
echo ""
echo "--- GIT COMMIT ---"
cd "$BASE"

# Fix lint first
cd apps/api && ruff check app/ --fix 2>/dev/null; cd ../..

# Fix frontend types
cd apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -5; cd ../..

git add -A
git status --short | head -20
git commit -m "fix: productization review — all tables, endpoints, pages, encryption verified and fixed"
git push origin main && echo "✅ Pushed to GitHub" || echo "❌ Push failed"
```

---

## IF ANY CHECK STILL FAILS AFTER ALL STEPS:

For each remaining ❌:

**DB table missing:**
```bash
# Re-run Step 1 — it's idempotent
```

**Import failed:**
```bash
# Check the exact error:
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 -c "from app.services.integrations.meta_oauth import MetaOAuthService" 2>&1
# Fix the specific import error shown
```

**Endpoint 422/500:**
```bash
# Get the actual error:
curl -s http://localhost:8000/api/v1/integrations/connections \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Fix the specific error in the endpoint file
```

**Frontend page missing:**
```bash
# Create the directory and file
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src/app/dashboard/integrations"
# Then create page.tsx with full implementation
```

**TypeScript error:**
```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npx tsc --noEmit 2>&1
# Fix each error shown
```

DO NOT STOP until:
```
✅ ALL CHECKS PASSED — PLATFORM IS PRODUCT-READY
```
is shown.
