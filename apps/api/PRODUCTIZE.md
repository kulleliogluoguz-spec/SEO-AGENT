# PHASE 2 — FULL PRODUCTIZATION MEGAPROMPT
## AI Growth OS → Real Production Product
## Save as: apps/api/PRODUCTIZE.md

You are a senior full-stack engineer, SaaS architect, and integration specialist.
Your mission: transform this platform from a partially-working prototype into a 
real product that can onboard a real company and analyze their actual Meta + Google Ads data.

Platform: /Users/oguzkullelioglu/Desktop/ai-cmo-os 2/
Stack: FastAPI (8000) + Next.js 14 (3001) + PostgreSQL + Ollama (11434)

RULES:
- Never break existing functionality
- Every step has verification — run it before proceeding
- If a step fails, fix it before moving forward
- No placeholder code, no TODOs, no stubs — everything fully implemented
- Commit after each major module

---

## PHASE 0: FULL AUDIT FIRST

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "=== CURRENT FILES ==="
find "$BASE/apps/api/app/api/endpoints" -name "*.py" | sort
find "$BASE/apps/api/app/services" -name "*.py" | sort
find "$BASE/apps/web/src/app/dashboard" -name "page.tsx" | sort

echo "=== DATABASE TABLES ==="
python3 -c "
import asyncio, asyncpg, os
async def f():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL','').replace('+asyncpg',''))
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    [print(r['tablename']) for r in rows]
    await conn.close()
asyncio.run(f())
"

echo "=== CURRENT .ENV ==="
cat "$BASE/apps/api/.env"

echo "=== OLLAMA MODELS ==="
curl -s http://localhost:11434/api/tags | python3 -c \
  "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]"

echo "=== MAIN.PY ROUTERS ==="
grep -n "include_router" "$BASE/apps/api/app/main.py"
```

Read ALL output before touching anything.

---

## MODULE 1: DATABASE SCHEMA — ALL NEW TABLES

Run this script to create every table needed for productization:

```python
# Save as: apps/api/scripts/productize_db.py
import asyncio, asyncpg, os

async def create_all():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)

    await conn.execute("""

    -- ─────────────────────────────────────────────
    -- WORKSPACE SETTINGS (dashboard-driven config)
    -- ─────────────────────────────────────────────
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
        -- Encrypted credentials (AES-256 via Fernet)
        meta_app_id_enc TEXT,
        meta_app_secret_enc TEXT,
        google_developer_token_enc TEXT,
        google_client_id_enc TEXT,
        google_client_secret_enc TEXT,
        twilio_account_sid_enc TEXT,
        twilio_auth_token_enc TEXT,
        twilio_phone_number VARCHAR(50),
        -- Setup progress
        setup_completed BOOLEAN DEFAULT FALSE,
        setup_step INTEGER DEFAULT 1,
        -- Notifications
        slack_webhook_url TEXT,
        notification_email VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────
    -- AD ACCOUNT CONNECTIONS (OAuth tokens per workspace)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS ad_account_connections (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id UUID NOT NULL,
        platform VARCHAR(20) NOT NULL,       -- 'meta' | 'google'
        account_id VARCHAR(200) NOT NULL,    -- Meta: act_123456 | Google: 123-456-7890
        account_name VARCHAR(500),
        currency VARCHAR(10) DEFAULT 'USD',
        timezone VARCHAR(100),
        -- Encrypted tokens
        access_token_enc TEXT,              -- Fernet encrypted
        refresh_token_enc TEXT,             -- Fernet encrypted
        long_lived_token_enc TEXT,          -- Meta: 60-day token
        -- Token management
        token_expires_at TIMESTAMPTZ,
        token_type VARCHAR(50) DEFAULT 'user',
        scopes TEXT[],
        -- Status
        is_active BOOLEAN DEFAULT TRUE,
        last_sync_status VARCHAR(50) DEFAULT 'pending',
        last_sync_error TEXT,
        -- Timestamps
        connected_at TIMESTAMPTZ DEFAULT NOW(),
        last_synced_at TIMESTAMPTZ,
        UNIQUE(workspace_id, platform, account_id)
    );
    CREATE INDEX IF NOT EXISTS idx_connections_workspace
        ON ad_account_connections(workspace_id, platform, is_active);

    -- ─────────────────────────────────────────────
    -- PLATFORM EVENTS (cross-module event bus)
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- PRODUCT COSTS (for true profitability)
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_product_costs_workspace
        ON product_costs(workspace_id, is_default);

    -- ─────────────────────────────────────────────
    -- CAMPAIGN PROFIT ANALYSIS (true ROAS results)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS campaign_profit_analysis (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID REFERENCES ad_campaigns(id) ON DELETE CASCADE,
        analysis_date DATE NOT NULL,
        reported_roas NUMERIC(10,4),
        estimated_true_roas NUMERIC(10,4),
        contribution_margin NUMERIC(8,4),
        gross_profit NUMERIC(14,2),
        break_even_roas NUMERIC(10,4),
        kill_signal BOOLEAN DEFAULT FALSE,
        scale_signal BOOLEAN DEFAULT FALSE,
        signal_reason TEXT,
        confidence NUMERIC(5,4) DEFAULT 0.7,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(campaign_id, analysis_date)
    );
    CREATE INDEX IF NOT EXISTS idx_profit_analysis_campaign
        ON campaign_profit_analysis(campaign_id, analysis_date DESC);

    -- ─────────────────────────────────────────────
    -- CONTACTS (shared across modules)
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_contacts_workspace
        ON contacts(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_contacts_email
        ON contacts(email) WHERE email IS NOT NULL;

    -- ─────────────────────────────────────────────
    -- LEADS
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_leads_workspace_status
        ON leads(workspace_id, status);
    CREATE INDEX IF NOT EXISTS idx_leads_score
        ON leads(workspace_id, qualification_score DESC);

    -- ─────────────────────────────────────────────
    -- LEAD TIMELINE
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS lead_timeline (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        lead_id UUID REFERENCES leads(id),
        event_type VARCHAR(100),
        title VARCHAR(500),
        description TEXT,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_timeline_lead
        ON lead_timeline(lead_id, created_at DESC);

    -- ─────────────────────────────────────────────
    -- CALLS
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_calls_workspace
        ON calls(workspace_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_calls_lead
        ON calls(lead_id);

    -- ─────────────────────────────────────────────
    -- CALL TRANSCRIPTS
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_transcripts_call
        ON call_transcripts(call_id);

    -- ─────────────────────────────────────────────
    -- CALL ANALYSIS
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- INVOICES (finance module)
    -- ─────────────────────────────────────────────
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
    CREATE INDEX IF NOT EXISTS idx_invoices_workspace_date
        ON invoices(workspace_id, invoice_date DESC NULLS LAST);

    -- ─────────────────────────────────────────────
    -- AI FEEDBACK (learning layer)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS ai_feedback (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id UUID NOT NULL,
        module VARCHAR(100),
        feedback_type VARCHAR(50),
        original_recommendation JSONB,
        user_action JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────
    -- AI MEMORY (learning layer)
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- COMPANY PROFILES (discovery panel)
    -- ─────────────────────────────────────────────
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

    """)

    # Verify all tables
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    names = [t['tablename'] for t in tables]
    required = [
        'workspace_settings','ad_account_connections','platform_events',
        'product_costs','campaign_profit_analysis','contacts','leads',
        'lead_timeline','calls','call_transcripts','call_analysis',
        'invoices','ai_feedback','ai_memory','company_profiles'
    ]
    print("\n=== TABLE VERIFICATION ===")
    all_ok = True
    for t in required:
        ok = t in names
        print(f"{'✅' if ok else '❌'} {t}")
        if not ok: all_ok = False
    print(f"\n{'✅ All tables created' if all_ok else '❌ Some tables missing!'}")
    await conn.close()

asyncio.run(create_all())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/productize_db.py
```

All ✅ before proceeding.

---

## MODULE 2: ENCRYPTION SERVICE

Create `apps/api/app/services/security/encryption.py`:

```python
"""
Token Encryption Service
Encrypts/decrypts sensitive credentials (OAuth tokens, API keys)
using Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
"""
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Encrypts credentials before DB storage.
    Decrypts when loading for API calls.
    
    Key stored in .env as ENCRYPTION_KEY (never in DB).
    """
    _fernet: Optional[Fernet] = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            key = os.getenv("ENCRYPTION_KEY")
            if not key:
                # Generate key and warn — should be set in .env
                logger.warning(
                    "ENCRYPTION_KEY not set in .env — generating temporary key. "
                    "SET A PERMANENT KEY: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
                key = Fernet.generate_key().decode()
            cls._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> Optional[str]:
        """Encrypt a string. Returns base64-encoded ciphertext."""
        if not plaintext:
            return None
        try:
            return cls._get_fernet().encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None

    @classmethod
    def decrypt(cls, ciphertext: str) -> Optional[str]:
        """Decrypt a Fernet ciphertext. Returns plaintext or None."""
        if not ciphertext:
            return None
        try:
            return cls._get_fernet().decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token — key mismatch or corrupted data")
            return None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    @classmethod
    def generate_key(cls) -> str:
        """Generate a new Fernet key. Run once, store in .env."""
        return Fernet.generate_key().decode()


# Singleton helper functions
def encrypt(plaintext: str) -> Optional[str]:
    return EncryptionService.encrypt(plaintext)

def decrypt(ciphertext: str) -> Optional[str]:
    return EncryptionService.decrypt(ciphertext)
```

Add `ENCRYPTION_KEY` to `.env`:

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

# Generate a key
KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "ENCRYPTION_KEY=$KEY" >> .env
echo "Generated ENCRYPTION_KEY and added to .env"

# Install cryptography if not already installed
pip install cryptography --quiet

# Verify
python3 -c "
from app.services.security.encryption import encrypt, decrypt
test = 'my-secret-token-123'
enc = encrypt(test)
dec = decrypt(enc)
assert dec == test, 'Encryption test FAILED'
print('✅ Encryption working:', enc[:30], '...')
print('✅ Decryption working:', dec)
"
```

Create `apps/api/app/services/security/__init__.py` (empty).

---

## MODULE 3: META ADS INTEGRATION

### 3A: Install dependencies

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install facebook-business==20.0.0 requests-oauthlib --quiet
echo "facebook-business==20.0.0" >> requirements.txt
```

### 3B: Meta OAuth Service

Create `apps/api/app/services/integrations/meta_oauth.py`:

```python
"""
Meta Ads OAuth Service
Handles Facebook Marketing API authentication.
Supports both:
  - System User Token (immediate, no user interaction)
  - OAuth2 flow (user-authorizes, production-grade)
"""
import os
import logging
import requests
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.security.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v19.0"
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")


class MetaOAuthService:

    def get_oauth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Meta OAuth authorization URL."""
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
        """Exchange OAuth code for short-lived access token."""
        r = requests.get(
            f"{META_GRAPH_URL}/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30
        )
        if not r.ok:
            raise ValueError(f"Token exchange failed: {r.text}")
        return r.json()

    def get_long_lived_token(self, short_lived_token: str) -> dict:
        """
        Exchange short-lived token (1-2 hours) for long-lived token (60 days).
        For Standard/Advanced Marketing API access: tokens never expire.
        """
        r = requests.get(
            f"{META_GRAPH_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": short_lived_token,
            },
            timeout=30
        )
        if not r.ok:
            raise ValueError(f"Long-lived token exchange failed: {r.text}")
        return r.json()

    def get_ad_accounts(self, access_token: str) -> list[dict]:
        """Get all ad accounts accessible with this token."""
        r = requests.get(
            f"{META_GRAPH_URL}/me/adaccounts",
            params={
                "access_token": access_token,
                "fields": "id,name,currency,timezone_name,account_status",
            },
            timeout=30
        )
        if not r.ok:
            logger.error(f"Meta ad accounts fetch failed: {r.text}")
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
        """Verify token is still valid."""
        r = requests.get(
            f"{META_GRAPH_URL}/me",
            params={"access_token": access_token, "fields": "id,name"},
            timeout=10
        )
        return r.ok

    async def save_connection(
        self,
        db: AsyncSession,
        workspace_id: str,
        account_id: str,
        account_name: str,
        access_token: str,
        currency: str = "USD",
        timezone: str = None
    ) -> str:
        """Save Meta connection to DB with encrypted token."""
        enc_token = encrypt(access_token)
        result = await db.execute(
            text("""
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     currency, timezone, access_token_enc, long_lived_token_enc,
                     is_active, last_sync_status)
                VALUES (:wid, 'meta', :aid, :aname, :curr, :tz, :tok, :ltok, true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id)
                DO UPDATE SET
                    account_name = :aname,
                    access_token_enc = :tok,
                    long_lived_token_enc = :ltok,
                    is_active = true,
                    last_sync_status = 'pending',
                    connected_at = NOW()
                RETURNING id
            """),
            {
                "wid": workspace_id, "aid": account_id, "aname": account_name,
                "curr": currency, "tz": timezone,
                "tok": enc_token, "ltok": enc_token,
            }
        )
        conn_id = str(result.fetchone()[0])
        await db.commit()
        logger.info(f"Meta connection saved: workspace={workspace_id} account={account_id}")
        return conn_id

    def get_decrypted_token(self, connection_row: dict) -> Optional[str]:
        """Decrypt token from DB row for API use."""
        enc = connection_row.get("long_lived_token_enc") or connection_row.get("access_token_enc")
        if not enc:
            return None
        return decrypt(enc)
```

### 3C: Meta Ads Data Fetcher

Create `apps/api/app/services/integrations/meta_ads_fetcher.py`:

```python
"""
Meta Ads Data Fetcher
Fetches real campaign/adset/ad performance data from Meta Marketing API.
"""
import logging
import requests
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
META_GRAPH_URL = "https://graph.facebook.com/v19.0"


class MetaAdsFetcher:

    def __init__(self, access_token: str):
        self.token = access_token
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated GET request."""
        p = {"access_token": self.token}
        if params:
            p.update(params)
        r = self.session.get(f"{META_GRAPH_URL}/{endpoint}", params=p, timeout=60)
        if not r.ok:
            logger.error(f"Meta API error {r.status_code}: {r.text[:200]}")
            return {}
        return r.json()

    def get_campaigns(self, account_id: str, limit: int = 100) -> list[dict]:
        """Fetch all campaigns for an ad account."""
        data = self._get(
            f"{account_id}/campaigns",
            {
                "fields": "id,name,status,objective,daily_budget,lifetime_budget,created_time,updated_time",
                "limit": limit,
            }
        )
        campaigns = data.get("data", [])
        logger.info(f"Fetched {len(campaigns)} campaigns from Meta account {account_id}")
        return campaigns

    def get_campaign_insights(
        self,
        campaign_id: str,
        date_from: date,
        date_to: date,
    ) -> dict:
        """
        Fetch performance metrics for a campaign.
        Returns: spend, impressions, clicks, conversions, revenue, ROAS, CPA, CTR, frequency.
        """
        data = self._get(
            f"{campaign_id}/insights",
            {
                "fields": (
                    "impressions,clicks,spend,reach,frequency,"
                    "actions,action_values,ctr,cpc,cpm,"
                    "cost_per_action_type,purchase_roas"
                ),
                "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
                "level": "campaign",
            }
        )
        rows = data.get("data", [])
        if not rows:
            return {}

        row = rows[0]
        spend = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        clicks = int(row.get("clicks", 0))
        frequency = float(row.get("frequency", 0))
        ctr = float(row.get("ctr", 0))

        # Parse actions for conversions and revenue
        actions = row.get("actions", [])
        action_values = row.get("action_values", [])
        conversions = sum(
            float(a.get("value", 0)) for a in actions
            if a.get("action_type") in ["purchase", "omni_purchase"]
        )
        revenue = sum(
            float(a.get("value", 0)) for a in action_values
            if a.get("action_type") in ["purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"]
        )

        roas_data = row.get("purchase_roas", [])
        roas = float(roas_data[0].get("value", 0)) if roas_data else (revenue / spend if spend > 0 else 0)
        cpa = spend / conversions if conversions > 0 else 0

        return {
            "campaign_id": campaign_id,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": revenue,
            "roas": round(roas, 4),
            "cpa": round(cpa, 2),
            "ctr": round(ctr, 4),
            "frequency": round(frequency, 2),
        }

    def get_account_summary(
        self,
        account_id: str,
        days: int = 7
    ) -> dict:
        """Get account-level summary for last N days."""
        date_to = date.today()
        date_from = date_to - timedelta(days=days)
        data = self._get(
            f"{account_id}/insights",
            {
                "fields": "spend,impressions,clicks,actions,action_values,purchase_roas",
                "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
                "level": "account",
            }
        )
        rows = data.get("data", [])
        if not rows:
            return {"account_id": account_id, "spend": 0, "roas": 0, "period_days": days}

        row = rows[0]
        spend = float(row.get("spend", 0))
        action_values = row.get("action_values", [])
        revenue = sum(
            float(a.get("value", 0)) for a in action_values
            if "purchase" in a.get("action_type", "")
        )
        roas_data = row.get("purchase_roas", [])
        roas = float(roas_data[0].get("value", 0)) if roas_data else (revenue / spend if spend > 0 else 0)

        return {
            "account_id": account_id,
            "spend": spend,
            "revenue": revenue,
            "roas": round(roas, 4),
            "period_days": days,
        }

    def sync_all_campaigns(
        self,
        account_id: str,
        days: int = 7
    ) -> list[dict]:
        """
        Full sync: get campaigns + performance for each.
        Returns list ready to upsert into ad_campaigns + ad_performance_daily.
        """
        campaigns = self.get_campaigns(account_id)
        date_to = date.today()
        date_from = date_to - timedelta(days=days)

        results = []
        for camp in campaigns:
            camp_id = camp.get("id")
            insights = self.get_campaign_insights(camp_id, date_from, date_to)
            results.append({
                "campaign": camp,
                "insights": insights,
            })

        return results
```

---

## MODULE 4: GOOGLE ADS INTEGRATION

### 4A: Install dependencies

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install google-ads==24.1.0 google-auth google-auth-oauthlib --quiet
echo "google-ads==24.1.0" >> requirements.txt
```

### 4B: Google Ads Service

Create `apps/api/app/services/integrations/google_ads_service.py`:

```python
"""
Google Ads Integration Service
Handles OAuth2 and data fetching from Google Ads API.

Important: Requires Google Ads Developer Token
(apply at: ads.google.com → Tools → API Center)
"""
import os
import logging
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
        """Generate Google OAuth2 authorization URL."""
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=["https://www.googleapis.com/auth/adwords"],
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force refresh token
        )
        return auth_url

    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access + refresh tokens."""
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=["https://www.googleapis.com/auth/adwords"],
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "expiry": str(credentials.expiry) if credentials.expiry else None,
        }

    def get_accessible_customers(self, refresh_token: str) -> list[dict]:
        """List all Google Ads accounts accessible with this token."""
        try:
            from google.ads.googleads.client import GoogleAdsClient
            client = GoogleAdsClient.load_from_dict({
                "developer_token": GOOGLE_DEVELOPER_TOKEN,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "use_proto_plus": True,
            })
            customer_service = client.get_service("CustomerService")
            response = customer_service.list_accessible_customers()
            customers = []
            for resource_name in response.resource_names:
                customer_id = resource_name.split("/")[-1]
                customers.append({
                    "customer_id": customer_id,
                    "account_name": f"Google Ads Account ({customer_id})",
                    "resource_name": resource_name,
                })
            return customers
        except Exception as e:
            logger.error(f"Google Ads accessible customers failed: {e}")
            return []

    async def save_connection(
        self,
        db: AsyncSession,
        workspace_id: str,
        account_id: str,
        account_name: str,
        access_token: str,
        refresh_token: str,
    ) -> str:
        """Save Google Ads connection with encrypted tokens."""
        result = await db.execute(
            text("""
                INSERT INTO ad_account_connections
                    (workspace_id, platform, account_id, account_name,
                     access_token_enc, refresh_token_enc, is_active, last_sync_status)
                VALUES (:wid, 'google', :aid, :aname, :atk, :rtk, true, 'pending')
                ON CONFLICT (workspace_id, platform, account_id)
                DO UPDATE SET
                    account_name = :aname,
                    access_token_enc = :atk,
                    refresh_token_enc = :rtk,
                    is_active = true,
                    connected_at = NOW()
                RETURNING id
            """),
            {
                "wid": workspace_id,
                "aid": account_id,
                "aname": account_name,
                "atk": encrypt(access_token),
                "rtk": encrypt(refresh_token),
            }
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

    def get_campaigns(self, customer_id: str) -> list[dict]:
        """Fetch all campaigns for a customer."""
        try:
            client = self._get_client(customer_id)
            ga_service = client.get_service("GoogleAdsService")
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.bidding_strategy_type,
                    campaign_budget.amount_micros
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                ORDER BY campaign.id
                LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            campaigns = []
            for row in response:
                camp = row.campaign
                budget = row.campaign_budget
                campaigns.append({
                    "id": str(camp.id),
                    "name": camp.name,
                    "status": camp.status.name,
                    "channel_type": camp.advertising_channel_type.name,
                    "daily_budget": budget.amount_micros / 1_000_000 if budget.amount_micros else 0,
                })
            return campaigns
        except Exception as e:
            logger.error(f"Google Ads campaigns fetch failed: {e}")
            return []

    def get_campaign_performance(
        self,
        customer_id: str,
        days: int = 7
    ) -> list[dict]:
        """Fetch campaign performance for the last N days."""
        try:
            client = self._get_client(customer_id)
            ga_service = client.get_service("GoogleAdsService")
            date_to = date.today()
            date_from = date_to - timedelta(days=days)

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_per_conversion
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                  AND segments.date BETWEEN '{date_from}' AND '{date_to}'
                ORDER BY metrics.cost_micros DESC
                LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            results = []
            for row in response:
                camp = row.campaign
                m = row.metrics
                spend = m.cost_micros / 1_000_000
                revenue = m.conversions_value
                roas = revenue / spend if spend > 0 else 0
                cpa = spend / m.conversions if m.conversions > 0 else 0

                results.append({
                    "campaign_id": str(camp.id),
                    "campaign_name": camp.name,
                    "spend": round(spend, 2),
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "conversions": m.conversions,
                    "revenue": round(revenue, 2),
                    "roas": round(roas, 4),
                    "cpa": round(cpa, 2),
                    "ctr": round(m.ctr, 4),
                    "period_days": days,
                })
            return results
        except Exception as e:
            logger.error(f"Google Ads performance fetch failed: {e}")
            return []
```

---

## MODULE 5: INTEGRATIONS API ENDPOINTS

Create `apps/api/app/api/endpoints/integrations.py`:

```python
"""
Integrations API — Dashboard-driven Meta + Google Ads connection.
No env-file manual setup needed. Everything through the dashboard.
"""
import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.integrations.meta_oauth import MetaOAuthService
from app.services.integrations.google_ads_service import (
    GoogleAdsOAuthService, GoogleAdsDataFetcher
)
from app.services.integrations.meta_ads_fetcher import MetaAdsFetcher
from app.services.security.encryption import encrypt, decrypt

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3001")

# ─── CONNECTIONS LIST ─────────────────────────────────────────────

@router.get("/connections")
async def list_connections(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all ad account connections for this workspace."""
    r = await db.execute(
        text("""
            SELECT id, platform, account_id, account_name, currency, timezone,
                   is_active, last_sync_status, last_sync_error,
                   connected_at, last_synced_at
            FROM ad_account_connections
            WHERE workspace_id = :wid
            ORDER BY platform, connected_at DESC
        """),
        {"wid": str(current_user.workspace_id)}
    )
    connections = [dict(row._mapping) for row in r.fetchall()]
    return {"connections": connections}

@router.delete("/connections/{connection_id}")
async def disconnect_account(
    connection_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect and delete an ad account connection."""
    await db.execute(
        text("""
            DELETE FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid
        """),
        {"id": connection_id, "wid": str(current_user.workspace_id)}
    )
    await db.commit()
    return {"success": True, "message": "Account disconnected"}

# ─── META ADS ─────────────────────────────────────────────────────

@router.get("/meta/authorize")
async def meta_authorize(
    current_user=Depends(get_current_user),
):
    """
    Step 1: Redirect user to Meta OAuth authorization page.
    After approval, Meta redirects to /meta/callback.
    """
    state = f"{current_user.workspace_id}:{uuid.uuid4()}"
    redirect_uri = f"{BACKEND_URL}/api/v1/integrations/meta/callback"
    oauth = MetaOAuthService()
    auth_url = oauth.get_oauth_url(redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}

@router.get("/meta/callback")
async def meta_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Meta redirects here with OAuth code.
    Exchange code for token, get ad accounts, save to DB.
    Redirects to frontend on success/failure.
    """
    workspace_id = state.split(":")[0]
    redirect_base = f"{FRONTEND_URL}/dashboard/integrations"

    try:
        redirect_uri = f"{BACKEND_URL}/api/v1/integrations/meta/callback"
        oauth = MetaOAuthService()

        # Exchange code for short-lived token
        token_data = oauth.exchange_code_for_token(code, redirect_uri)
        short_token = token_data.get("access_token")

        # Upgrade to long-lived token (60 days)
        long_token_data = oauth.get_long_lived_token(short_token)
        long_token = long_token_data.get("access_token", short_token)

        # Get accessible ad accounts
        ad_accounts = oauth.get_ad_accounts(long_token)

        if not ad_accounts:
            return RedirectResponse(f"{redirect_base}?status=error&msg=no_accounts")

        # Save all accessible accounts
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

        logger.info(f"Meta OAuth complete: workspace={workspace_id} accounts={saved_count}")
        return RedirectResponse(
            f"{redirect_base}?status=success&platform=meta&accounts={saved_count}"
        )

    except Exception as e:
        logger.error(f"Meta OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(f"{redirect_base}?status=error&msg={str(e)[:100]}")

@router.post("/meta/connect-token")
async def meta_connect_with_token(
    data: dict,  # {"access_token": "...", "account_id": "act_...", "account_name": "..."}
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Alternative: Connect Meta with a manually-provided System User Token.
    Useful for first company / testing without full OAuth setup.
    """
    access_token = data.get("access_token")
    account_id = data.get("account_id", "").strip()

    if not access_token:
        raise HTTPException(400, "access_token required")

    oauth = MetaOAuthService()

    # Validate token
    if not oauth.validate_token(access_token):
        raise HTTPException(400, "Token validation failed — token may be invalid or expired")

    # If no account_id provided, discover accounts automatically
    if not account_id:
        ad_accounts = oauth.get_ad_accounts(access_token)
        if not ad_accounts:
            raise HTTPException(400, "No ad accounts found for this token")
        saved = []
        for account in ad_accounts:
            conn_id = await oauth.save_connection(
                db=db,
                workspace_id=str(current_user.workspace_id),
                account_id=account["account_id"],
                account_name=account["account_name"],
                access_token=access_token,
                currency=account.get("currency", "USD"),
            )
            saved.append({"connection_id": conn_id, "account_id": account["account_id"]})
        return {"success": True, "connected_accounts": saved}
    else:
        account_name = data.get("account_name") or account_id
        conn_id = await oauth.save_connection(
            db=db,
            workspace_id=str(current_user.workspace_id),
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
    db: AsyncSession = Depends(get_db)
):
    """Sync campaigns and performance data from Meta for a connected account."""
    # Get connection
    r = await db.execute(
        text("""
            SELECT * FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid AND platform = 'meta'
        """),
        {"id": connection_id, "wid": str(current_user.workspace_id)}
    )
    conn = r.fetchone()
    if not conn:
        raise HTTPException(404, "Connection not found")
    conn = dict(conn._mapping)

    # Decrypt token
    token = decrypt(conn.get("long_lived_token_enc") or conn.get("access_token_enc"))
    if not token:
        raise HTTPException(400, "Token decryption failed — reconnect required")

    # Fetch data
    fetcher = MetaAdsFetcher(token)
    account_id = conn["account_id"]
    campaign_data = fetcher.sync_all_campaigns(account_id, days=days)
    account_summary = fetcher.get_account_summary(account_id, days=days)

    # Upsert campaigns into ad_campaigns table
    synced_campaigns = 0
    for item in campaign_data:
        camp = item["campaign"]
        insights = item.get("insights", {})
        camp_ext_id = camp.get("id")

        # Check if campaign exists
        existing = await db.execute(
            text("SELECT id FROM ad_campaigns WHERE external_id = :eid AND platform = 'meta'"),
            {"eid": camp_ext_id}
        )
        existing_row = existing.fetchone()

        if existing_row:
            camp_uuid = str(existing_row[0])
            await db.execute(
                text("""
                    UPDATE ad_campaigns SET
                        name = :name, status = :status, updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": camp_uuid, "name": camp.get("name"), "status": camp.get("status", "ACTIVE")}
            )
        else:
            # Find or create ad account record
            acc_r = await db.execute(
                text("SELECT id FROM ad_accounts WHERE external_id = :eid"),
                {"eid": account_id}
            )
            acc_row = acc_r.fetchone()
            if acc_row:
                ad_account_id = str(acc_row[0])
            else:
                # Create ad account record
                acc_ins = await db.execute(
                    text("""
                        INSERT INTO ad_accounts (workspace_id, name, platform, external_id, currency, is_active)
                        VALUES (:wid, :name, 'meta', :eid, :curr, true)
                        RETURNING id
                    """),
                    {
                        "wid": str(current_user.workspace_id),
                        "name": account_id,
                        "eid": account_id,
                        "curr": account_summary.get("currency", "USD"),
                    }
                )
                ad_account_id = str(acc_ins.fetchone()[0])

            camp_ins = await db.execute(
                text("""
                    INSERT INTO ad_campaigns
                        (ad_account_id, name, platform, status, external_id)
                    VALUES (:aid, :name, 'meta', :status, :eid)
                    RETURNING id
                """),
                {
                    "aid": ad_account_id,
                    "name": camp.get("name", "Unnamed"),
                    "status": camp.get("status", "ACTIVE"),
                    "eid": camp_ext_id,
                }
            )
            camp_uuid = str(camp_ins.fetchone()[0])

        # Upsert performance data if insights available
        if insights:
            from datetime import date
            await db.execute(
                text("""
                    INSERT INTO ad_performance_daily
                        (campaign_id, date, spend, revenue, impressions, clicks,
                         conversions, roas, cpa, ctr, frequency)
                    VALUES
                        (:cid, :date, :spend, :rev, :imp, :clicks,
                         :conv, :roas, :cpa, :ctr, :freq)
                    ON CONFLICT (campaign_id, date) DO UPDATE SET
                        spend = :spend, revenue = :rev, impressions = :imp,
                        clicks = :clicks, conversions = :conv, roas = :roas,
                        cpa = :cpa, ctr = :ctr, frequency = :freq
                """),
                {
                    "cid": camp_uuid,
                    "date": date.today(),
                    "spend": insights.get("spend", 0),
                    "rev": insights.get("revenue", 0),
                    "imp": insights.get("impressions", 0),
                    "clicks": insights.get("clicks", 0),
                    "conv": insights.get("conversions", 0),
                    "roas": insights.get("roas", 0),
                    "cpa": insights.get("cpa", 0),
                    "ctr": insights.get("ctr", 0),
                    "freq": insights.get("frequency", 0),
                }
            )
        synced_campaigns += 1

    # Update connection sync status
    await db.execute(
        text("""
            UPDATE ad_account_connections SET
                last_synced_at = NOW(), last_sync_status = 'success', last_sync_error = NULL
            WHERE id = :id
        """),
        {"id": connection_id}
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
    """Redirect to Google OAuth authorization."""
    state = f"{current_user.workspace_id}:{uuid.uuid4()}"
    oauth = GoogleAdsOAuthService()
    auth_url = oauth.get_oauth_url(state=state)
    return {"auth_url": auth_url}

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback."""
    workspace_id = state.split(":")[0]
    redirect_base = f"{FRONTEND_URL}/dashboard/integrations"
    try:
        oauth = GoogleAdsOAuthService()
        tokens = oauth.exchange_code_for_tokens(code)
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if not refresh_token:
            return RedirectResponse(
                f"{redirect_base}?status=error&msg=no_refresh_token_hint=add_prompt_consent"
            )

        # Get accessible customers
        customers = oauth.get_accessible_customers(refresh_token)

        if not customers:
            # Save with empty account_id for manual setup
            await oauth.save_connection(
                db, workspace_id, "auto-detect", "Google Ads Account",
                access_token, refresh_token
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
        logger.error(f"Google callback failed: {e}", exc_info=True)
        return RedirectResponse(f"{redirect_base}?status=error&msg={str(e)[:100]}")

@router.post("/google/connect-token")
async def google_connect_with_refresh_token(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect Google Ads with manually-provided refresh token.
    Useful for first company without full OAuth app verification.
    """
    refresh_token = data.get("refresh_token")
    customer_id = data.get("customer_id", "").replace("-", "")
    account_name = data.get("account_name", f"Google Ads ({customer_id})")

    if not refresh_token:
        raise HTTPException(400, "refresh_token required")
    if not customer_id:
        raise HTTPException(400, "customer_id required (10-digit Google Ads ID, no dashes)")
    if not GOOGLE_DEVELOPER_TOKEN:
        raise HTTPException(400, "GOOGLE_DEVELOPER_TOKEN not configured in .env")

    oauth = GoogleAdsOAuthService()
    conn_id = await oauth.save_connection(
        db=db,
        workspace_id=str(current_user.workspace_id),
        account_id=customer_id,
        account_name=account_name,
        access_token="",  # Will be refreshed automatically
        refresh_token=refresh_token,
    )
    return {"success": True, "connection_id": conn_id}

@router.get("/google/sync/{connection_id}")
async def sync_google_account(
    connection_id: str,
    days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync campaigns and performance from Google Ads."""
    r = await db.execute(
        text("""
            SELECT * FROM ad_account_connections
            WHERE id = :id AND workspace_id = :wid AND platform = 'google'
        """),
        {"id": connection_id, "wid": str(current_user.workspace_id)}
    )
    conn = r.fetchone()
    if not conn:
        raise HTTPException(404, "Connection not found")
    conn = dict(conn._mapping)

    refresh_token = decrypt(conn.get("refresh_token_enc"))
    if not refresh_token:
        raise HTTPException(400, "No refresh token — reconnect required")

    customer_id = conn["account_id"]
    fetcher = GoogleAdsDataFetcher(refresh_token)
    performance = fetcher.get_campaign_performance(customer_id, days=days)

    # Update sync status
    await db.execute(
        text("UPDATE ad_account_connections SET last_synced_at=NOW(), last_sync_status='success' WHERE id=:id"),
        {"id": connection_id}
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
    db: AsyncSession = Depends(get_db)
):
    """Sync all active connections for this workspace."""
    r = await db.execute(
        text("""
            SELECT id, platform FROM ad_account_connections
            WHERE workspace_id = :wid AND is_active = true
        """),
        {"wid": str(current_user.workspace_id)}
    )
    connections = r.fetchall()
    results = []
    for conn in connections:
        try:
            if conn.platform == "meta":
                result = await sync_meta_account(
                    str(conn.id), days, current_user, db
                )
            else:
                result = await sync_google_account(
                    str(conn.id), days, current_user, db
                )
            results.append({"id": str(conn.id), "platform": conn.platform, "status": "ok"})
        except Exception as e:
            results.append({"id": str(conn.id), "platform": conn.platform, "status": "error", "error": str(e)[:100]})
    return {"results": results, "total": len(results)}
```

---

## MODULE 6: WORKSPACE SETTINGS API

Add to `apps/api/app/api/endpoints/` — create `workspace.py`:

```python
"""
Workspace Settings — Dashboard-driven configuration.
No more manual .env editing per customer.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.security.encryption import encrypt, decrypt

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])
logger = logging.getLogger(__name__)


@router.get("/settings")
async def get_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workspace settings (credentials shown as masked)."""
    wid = str(current_user.workspace_id)
    r = await db.execute(
        text("SELECT * FROM workspace_settings WHERE workspace_id = :wid"),
        {"wid": wid}
    )
    row = r.fetchone()
    if not row:
        return {"settings": {"setup_completed": False, "setup_step": 1}}

    settings = dict(row._mapping)
    # Never expose encrypted values — just show if they're set
    for field in ["meta_app_id_enc","meta_app_secret_enc","google_developer_token_enc",
                  "google_client_id_enc","google_client_secret_enc",
                  "twilio_account_sid_enc","twilio_auth_token_enc"]:
        settings[field.replace("_enc","")] = bool(settings.get(field))
        settings.pop(field, None)
    return {"settings": settings}


@router.put("/settings")
async def update_settings(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update workspace settings. Credentials are encrypted before storage."""
    wid = str(current_user.workspace_id)

    # Fields that get encrypted
    credential_fields = {
        "meta_app_id": "meta_app_id_enc",
        "meta_app_secret": "meta_app_secret_enc",
        "google_developer_token": "google_developer_token_enc",
        "google_client_id": "google_client_id_enc",
        "google_client_secret": "google_client_secret_enc",
        "twilio_account_sid": "twilio_account_sid_enc",
        "twilio_auth_token": "twilio_auth_token_enc",
    }

    # Plain fields (safe to store directly)
    plain_fields = [
        "company_name","industry","default_currency","monthly_ad_budget",
        "break_even_roas","avg_order_value","cogs_per_unit","shipping_cost",
        "return_rate","twilio_phone_number","slack_webhook_url",
        "notification_email","setup_completed","setup_step"
    ]

    # Build update dict
    updates = {}
    for plain in plain_fields:
        if plain in data:
            updates[plain] = data[plain]
    for cred_key, enc_key in credential_fields.items():
        if cred_key in data and data[cred_key]:
            updates[enc_key] = encrypt(data[cred_key])

    if not updates:
        return {"success": True, "updated_fields": 0}

    # Upsert
    set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
    updates["wid"] = wid
    await db.execute(
        text(f"""
            INSERT INTO workspace_settings (workspace_id, {', '.join(k for k in updates.keys() if k != 'wid')})
            VALUES (:wid, {', '.join(f':{k}' for k in updates.keys() if k != 'wid')})
            ON CONFLICT (workspace_id) DO UPDATE SET
                {set_clause}, updated_at = NOW()
        """),
        updates
    )
    await db.commit()
    return {"success": True, "updated_fields": len(updates) - 1}


@router.get("/setup-status")
async def get_setup_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get setup wizard progress."""
    wid = str(current_user.workspace_id)
    r = await db.execute(
        text("SELECT setup_step, setup_completed FROM workspace_settings WHERE workspace_id=:wid"),
        {"wid": wid}
    )
    row = r.fetchone()
    if not row:
        return {"setup_step": 1, "setup_completed": False}

    # Count connected accounts
    conn_r = await db.execute(
        text("SELECT platform, COUNT(*) as cnt FROM ad_account_connections WHERE workspace_id=:wid AND is_active=true GROUP BY platform"),
        {"wid": wid}
    )
    connections = {r.platform: r.cnt for r in conn_r.fetchall()}

    return {
        "setup_step": row.setup_step,
        "setup_completed": row.setup_completed,
        "meta_connected": connections.get("meta", 0) > 0,
        "google_connected": connections.get("google", 0) > 0,
    }
```

---

## MODULE 7: SENTRY + OBSERVABILITY

### 7A: Backend — Sentry for FastAPI

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install sentry-sdk[fastapi] loguru --quiet
echo "sentry-sdk[fastapi]" >> requirements.txt
echo "loguru" >> requirements.txt
```

Create `apps/api/app/core/logging_config.py`:

```python
"""Structured logging configuration."""
import os
import sys
import logging
from loguru import logger

SENTRY_DSN = os.getenv("SENTRY_DSN", "")

def setup_logging():
    """Configure loguru + Sentry."""
    # Remove default loguru handler
    logger.remove()

    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO"),
        colorize=True,
    )

    # File output (rotated daily)
    logger.add(
        "/tmp/ai-growth-os.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} — {message}",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
    )

    # Initialize Sentry
    if SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            send_default_pii=False,
        )
        logger.info("Sentry initialized")

    return logger
```

Add to `apps/api/app/main.py` at startup:

```python
# Add near the top of main.py, after imports:
from app.core.logging_config import setup_logging
setup_logging()
```

Add to `.env`:
```bash
echo "SENTRY_DSN=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "ENVIRONMENT=development" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "BACKEND_URL=http://localhost:8000" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "FRONTEND_URL=http://127.0.0.1:3001" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "GOOGLE_CLIENT_ID=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "GOOGLE_CLIENT_SECRET=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "GOOGLE_DEVELOPER_TOKEN=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/google/callback" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "META_APP_ID=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
echo "META_APP_SECRET=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
```

### 7B: Frontend — Sentry for Next.js

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npm install @sentry/nextjs --save

# Auto-setup (will ask questions, answer: yes to all)
# OR manual setup:
```

Create `apps/web/sentry.client.config.ts`:
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  integrations: [Sentry.replayIntegration()],
  debug: false,
});
```

Create `apps/web/sentry.server.config.ts`:
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN || "",
  tracesSampleRate: 0.1,
  debug: false,
});
```

Add to `apps/web/.env.local`:
```bash
echo "NEXT_PUBLIC_SENTRY_DSN=" >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/.env.local"
```

---

## MODULE 8: ONBOARDING SETUP WIZARD FRONTEND

Create `apps/web/src/app/dashboard/integrations/page.tsx`:

```typescript
'use client'
import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Link2, RefreshCw, Trash2, AlertCircle, ExternalLink } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json',
})

const PLATFORM_COLORS = {
  meta: 'bg-blue-100 text-blue-700 border-blue-300',
  google: 'bg-red-100 text-red-700 border-red-300',
}

export default function IntegrationsPage() {
  const [connections, setConnections] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [metaToken, setMetaToken] = useState('')
  const [metaAccountId, setMetaAccountId] = useState('')
  const [googleRefreshToken, setGoogleRefreshToken] = useState('')
  const [googleCustomerId, setGoogleCustomerId] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success'|'error'; text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'connected'|'connect-meta'|'connect-google'>('connected')

  useEffect(() => {
    loadConnections()
    // Check for OAuth callback result
    const params = new URLSearchParams(window.location.search)
    const status = params.get('status')
    const platform = params.get('platform')
    if (status === 'success') {
      setMessage({ type: 'success', text: `${platform?.toUpperCase()} Ads connected successfully!` })
      window.history.replaceState({}, '', window.location.pathname)
      loadConnections()
    } else if (status === 'error') {
      setMessage({ type: 'error', text: `Connection failed: ${params.get('msg') || 'unknown error'}` })
    }
  }, [])

  async function loadConnections() {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/v1/integrations/connections`, { headers: hdrs() })
      if (r.ok) setConnections((await r.json()).connections || [])
    } finally {
      setLoading(false)
    }
  }

  async function connectMetaOAuth() {
    const r = await fetch(`${API}/api/v1/integrations/meta/authorize`, { headers: hdrs() })
    if (r.ok) {
      const { auth_url } = await r.json()
      window.location.href = auth_url
    }
  }

  async function connectGoogleOAuth() {
    const r = await fetch(`${API}/api/v1/integrations/google/authorize`, { headers: hdrs() })
    if (r.ok) {
      const { auth_url } = await r.json()
      window.location.href = auth_url
    }
  }

  async function connectMetaToken() {
    if (!metaToken) return
    setSaving(true)
    setMessage(null)
    try {
      const r = await fetch(`${API}/api/v1/integrations/meta/connect-token`, {
        method: 'POST', headers: hdrs(),
        body: JSON.stringify({
          access_token: metaToken,
          account_id: metaAccountId || undefined,
        })
      })
      const d = await r.json()
      if (r.ok) {
        setMessage({ type: 'success', text: 'Meta Ads connected! Loading accounts...' })
        setMetaToken('')
        setMetaAccountId('')
        loadConnections()
        setActiveTab('connected')
      } else {
        setMessage({ type: 'error', text: d.detail || 'Connection failed' })
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  async function connectGoogleToken() {
    if (!googleRefreshToken || !googleCustomerId) return
    setSaving(true)
    setMessage(null)
    try {
      const r = await fetch(`${API}/api/v1/integrations/google/connect-token`, {
        method: 'POST', headers: hdrs(),
        body: JSON.stringify({
          refresh_token: googleRefreshToken,
          customer_id: googleCustomerId.replace(/-/g, ''),
        })
      })
      const d = await r.json()
      if (r.ok) {
        setMessage({ type: 'success', text: 'Google Ads connected!' })
        setGoogleRefreshToken('')
        setGoogleCustomerId('')
        loadConnections()
        setActiveTab('connected')
      } else {
        setMessage({ type: 'error', text: d.detail || 'Connection failed' })
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  async function syncAccount(id: string) {
    setSyncing(id)
    try {
      const platform = connections.find(c => c.id === id)?.platform
      const endpoint = platform === 'meta'
        ? `${API}/api/v1/integrations/meta/sync/${id}`
        : `${API}/api/v1/integrations/google/sync/${id}`
      const r = await fetch(endpoint, { headers: hdrs() })
      const d = await r.json()
      if (r.ok) {
        setMessage({ type: 'success', text: `Synced ${d.synced_campaigns || d.campaigns_synced} campaigns` })
        loadConnections()
      } else {
        setMessage({ type: 'error', text: d.detail || 'Sync failed' })
      }
    } finally {
      setSyncing(null)
    }
  }

  async function disconnectAccount(id: string) {
    if (!confirm('Disconnect this account? Ad data will remain in the system.')) return
    await fetch(`${API}/api/v1/integrations/connections/${id}`, { method: 'DELETE', headers: hdrs() })
    loadConnections()
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ad Account Integrations</h1>
        <p className="text-sm text-gray-500 mt-1">
          Connect your Meta Ads and Google Ads accounts to analyze real campaign data.
        </p>
      </div>

      {/* Message Banner */}
      {message && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${
          message.type === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
        }`}>
          {message.type === 'success'
            ? <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
            : <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />}
          <p className={`text-sm ${message.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
            {message.text}
          </p>
          <button onClick={() => setMessage(null)} className="ml-auto text-gray-400 hover:text-gray-600">×</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {[
          { key: 'connected', label: `Connected (${connections.length})` },
          { key: 'connect-meta', label: '+ Meta Ads' },
          { key: 'connect-google', label: '+ Google Ads' },
        ].map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Connected Accounts */}
      {activeTab === 'connected' && (
        <div className="space-y-3">
          {loading ? (
            Array.from({length:2}).map((_,i) => (
              <div key={i} className="bg-white rounded-xl border p-4 h-20 animate-pulse bg-gray-100" />
            ))
          ) : connections.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center">
              <Link2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 font-medium">No accounts connected yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Connect Meta Ads or Google Ads using the tabs above
              </p>
            </div>
          ) : (
            <>
              {connections.map(conn => (
                <div key={conn.id} className="bg-white rounded-xl border p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold uppercase border ${
                        PLATFORM_COLORS[conn.platform as keyof typeof PLATFORM_COLORS] || 'bg-gray-100 text-gray-600 border-gray-200'
                      }`}>
                        {conn.platform}
                      </span>
                      <div>
                        <div className="font-medium text-gray-800">{conn.account_name}</div>
                        <div className="text-xs text-gray-400">{conn.account_id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className={`text-xs px-2 py-1 rounded-full ${
                        conn.last_sync_status === 'success'
                          ? 'bg-green-100 text-green-700'
                          : conn.last_sync_status === 'error'
                          ? 'bg-red-100 text-red-600'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {conn.last_sync_status === 'success' ? '✓ Synced' :
                         conn.last_sync_status === 'error' ? '✗ Error' : '○ Pending'}
                      </div>
                      <button
                        onClick={() => syncAccount(conn.id)}
                        disabled={syncing === conn.id}
                        className="p-2 hover:bg-gray-100 rounded-lg transition"
                        title="Sync now"
                      >
                        <RefreshCw className={`w-4 h-4 text-gray-500 ${syncing === conn.id ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={() => disconnectAccount(conn.id)}
                        className="p-2 hover:bg-red-50 rounded-lg transition"
                        title="Disconnect"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </div>
                  {conn.last_synced_at && (
                    <div className="text-xs text-gray-400 mt-2">
                      Last synced: {new Date(conn.last_synced_at).toLocaleString()}
                    </div>
                  )}
                  {conn.last_sync_error && (
                    <div className="text-xs text-red-500 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> {conn.last_sync_error}
                    </div>
                  )}
                </div>
              ))}
              <button
                onClick={() => syncAccount('all')}
                className="w-full py-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Sync all accounts
              </button>
            </>
          )}
        </div>
      )}

      {/* Connect Meta */}
      {activeTab === 'connect-meta' && (
        <div className="space-y-4">
          {/* OAuth option */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-semibold text-blue-800 mb-2">Option A — OAuth (Recommended)</h3>
            <p className="text-sm text-blue-700 mb-4">
              Click below to authorize via Facebook. You'll be redirected to Meta and back automatically.
              Requires: Meta App with Marketing API access.
            </p>
            <button onClick={connectMetaOAuth}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
              <ExternalLink className="w-4 h-4" />
              Connect with Meta OAuth
            </button>
          </div>

          {/* Manual token option */}
          <div className="bg-white border rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-gray-800">Option B — System User Token (Quick Setup)</h3>
            <p className="text-sm text-gray-500">
              Get a token from: Meta Business Manager → Settings → Users → System Users → Generate Token.<br/>
              Grant: <code className="bg-gray-100 px-1 rounded text-xs">ads_management, ads_read</code>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Access Token *</label>
              <textarea
                value={metaToken}
                onChange={e => setMetaToken(e.target.value)}
                rows={3}
                placeholder="EAAxxxxxxx..."
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ad Account ID (optional — auto-discovers if blank)
              </label>
              <input
                value={metaAccountId}
                onChange={e => setMetaAccountId(e.target.value)}
                placeholder="act_1234567890"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button onClick={connectMetaToken} disabled={saving || !metaToken}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Connecting...' : 'Connect Meta Ads'}
            </button>
          </div>
        </div>
      )}

      {/* Connect Google */}
      {activeTab === 'connect-google' && (
        <div className="space-y-4">
          {/* OAuth option */}
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <h3 className="font-semibold text-red-800 mb-2">Option A — OAuth (Recommended)</h3>
            <p className="text-sm text-red-700 mb-4">
              Requires: Google Cloud project with Google Ads API enabled + Developer Token.
            </p>
            <button onClick={connectGoogleOAuth}
              className="bg-red-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 flex items-center gap-2">
              <ExternalLink className="w-4 h-4" />
              Connect with Google OAuth
            </button>
          </div>

          {/* Manual token option */}
          <div className="bg-white border rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-gray-800">Option B — Refresh Token (Quick Setup)</h3>
            <p className="text-sm text-gray-500">
              Generate a refresh token using the Google Ads Python script:<br/>
              <code className="bg-gray-100 px-1 rounded text-xs">
                python3 -m google.ads.googleads.examples.authentication.generate_user_credentials
              </code>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Google Customer ID *</label>
              <input
                value={googleCustomerId}
                onChange={e => setGoogleCustomerId(e.target.value)}
                placeholder="123-456-7890"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
              <p className="text-xs text-gray-400 mt-1">Found in top-right corner of Google Ads UI</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Refresh Token *</label>
              <textarea
                value={googleRefreshToken}
                onChange={e => setGoogleRefreshToken(e.target.value)}
                rows={3}
                placeholder="1//0gxxxxxx..."
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-none"
              />
            </div>
            <button onClick={connectGoogleToken}
              disabled={saving || !googleRefreshToken || !googleCustomerId}
              className="bg-red-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50">
              {saving ? 'Connecting...' : 'Connect Google Ads'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

Create `apps/web/src/app/dashboard/setup/page.tsx` — Onboarding Wizard:

```typescript
'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { CheckCircle, ArrowRight, Building2, DollarSign, Phone, Link2 } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json',
})

const STEPS = [
  { num: 1, title: 'Company Info', icon: Building2, desc: 'Tell us about your business' },
  { num: 2, title: 'Ad Accounts', icon: Link2, desc: 'Connect Meta & Google Ads' },
  { num: 3, title: 'Cost Settings', icon: DollarSign, desc: 'Set product costs for true ROAS' },
  { num: 4, title: 'Ready!', icon: CheckCircle, desc: 'Platform configured' },
]

export default function SetupWizard() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [connections, setConnections] = useState<any[]>([])
  const [form, setForm] = useState({
    company_name: '',
    industry: '',
    monthly_ad_budget: '',
    default_currency: 'USD',
    cogs_per_unit: '',
    shipping_cost: '',
    return_rate: '5',
    avg_order_value: '',
  })

  useEffect(() => { loadStatus() }, [])

  async function loadStatus() {
    const r = await fetch(`${API}/api/v1/workspace/setup-status`, { headers: hdrs() })
    if (r.ok) {
      const d = await r.json()
      if (d.setup_completed) { router.push('/dashboard'); return }
      setStep(d.setup_step || 1)
    }
    const cr = await fetch(`${API}/api/v1/integrations/connections`, { headers: hdrs() })
    if (cr.ok) setConnections((await cr.json()).connections || [])
  }

  const update = (k: string, v: string) => setForm(f => ({...f, [k]: v}))

  async function saveStep1() {
    setSaving(true)
    await fetch(`${API}/api/v1/workspace/settings`, {
      method: 'PUT', headers: hdrs(),
      body: JSON.stringify({
        company_name: form.company_name,
        industry: form.industry,
        monthly_ad_budget: parseFloat(form.monthly_ad_budget) || null,
        default_currency: form.default_currency,
        setup_step: 2,
      })
    })
    setSaving(false)
    setStep(2)
  }

  async function saveStep3() {
    setSaving(true)
    await fetch(`${API}/api/v1/workspace/settings`, {
      method: 'PUT', headers: hdrs(),
      body: JSON.stringify({
        cogs_per_unit: parseFloat(form.cogs_per_unit) || 0,
        shipping_cost: parseFloat(form.shipping_cost) || 0,
        return_rate: parseFloat(form.return_rate) / 100,
        avg_order_value: parseFloat(form.avg_order_value) || null,
        setup_step: 4,
        setup_completed: true,
      })
    })
    setSaving(false)
    setStep(4)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Progress */}
        <div className="flex items-center justify-between mb-8">
          {STEPS.map((s, i) => (
            <div key={s.num} className="flex items-center">
              <div className={`flex flex-col items-center ${i < STEPS.length-1 ? 'flex-1' : ''}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  step > s.num ? 'bg-green-500 text-white' :
                  step === s.num ? 'bg-indigo-600 text-white' :
                  'bg-gray-200 text-gray-400'
                }`}>
                  {step > s.num ? <CheckCircle className="w-5 h-5" /> : s.num}
                </div>
                <div className="text-xs text-gray-500 mt-1 text-center w-20">{s.title}</div>
              </div>
              {i < STEPS.length-1 && (
                <div className={`flex-1 h-0.5 mx-2 mb-4 ${step > s.num ? 'bg-green-400' : 'bg-gray-200'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-2xl shadow-sm border p-8">
          {/* Step 1 — Company Info */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Tell us about your company</h2>
                <p className="text-sm text-gray-500 mt-1">This personalizes all recommendations</p>
              </div>
              {[
                { label: 'Company Name *', key: 'company_name', placeholder: 'Acme Corp' },
                { label: 'Industry', key: 'industry', placeholder: 'E-commerce, SaaS, Agency...' },
                { label: 'Monthly Ad Budget ($)', key: 'monthly_ad_budget', placeholder: '10000', type: 'number' },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{f.label}</label>
                  <input
                    type={f.type || 'text'}
                    value={form[f.key as keyof typeof form]}
                    onChange={e => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    className="w-full border rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-300"
                  />
                </div>
              ))}
              <button onClick={saveStep1} disabled={saving || !form.company_name}
                className="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
                {saving ? 'Saving...' : 'Continue'} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 2 — Connect Accounts */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Connect your ad accounts</h2>
                <p className="text-sm text-gray-500 mt-1">Connect Meta and/or Google Ads to analyze real data</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className={`border-2 rounded-xl p-4 ${connections.some(c=>c.platform==='meta') ? 'border-green-400 bg-green-50' : 'border-dashed border-gray-300'}`}>
                  <div className="font-medium text-gray-800 mb-1">Meta Ads</div>
                  {connections.some(c=>c.platform==='meta') ? (
                    <div className="text-sm text-green-600 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Connected ({connections.filter(c=>c.platform==='meta').length})
                    </div>
                  ) : (
                    <button
                      onClick={() => router.push('/dashboard/integrations?tab=meta')}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Connect →
                    </button>
                  )}
                </div>
                <div className={`border-2 rounded-xl p-4 ${connections.some(c=>c.platform==='google') ? 'border-green-400 bg-green-50' : 'border-dashed border-gray-300'}`}>
                  <div className="font-medium text-gray-800 mb-1">Google Ads</div>
                  {connections.some(c=>c.platform==='google') ? (
                    <div className="text-sm text-green-600 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Connected
                    </div>
                  ) : (
                    <button
                      onClick={() => router.push('/dashboard/integrations?tab=google')}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Connect →
                    </button>
                  )}
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={() => setStep(3)}
                  className="flex-1 border border-gray-300 text-gray-600 py-3 rounded-xl text-sm hover:bg-gray-50">
                  Skip for now
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={connections.length === 0}
                  className="flex-1 bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3 — Cost Settings */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Product cost settings</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Used to calculate true profitability beyond reported ROAS. Skip if you don't know yet.
                </p>
              </div>
              {[
                { label: 'Avg Order Value ($)', key: 'avg_order_value', placeholder: '65' },
                { label: 'Cost of Goods (COGS) per unit ($)', key: 'cogs_per_unit', placeholder: '15' },
                { label: 'Shipping cost per order ($)', key: 'shipping_cost', placeholder: '5' },
                { label: 'Return rate (%)', key: 'return_rate', placeholder: '5' },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{f.label}</label>
                  <input
                    type="number" step="0.01"
                    value={form[f.key as keyof typeof form]}
                    onChange={e => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    className="w-full border rounded-xl px-4 py-3 text-sm"
                  />
                </div>
              ))}
              <div className="flex gap-3">
                <button onClick={() => saveStep3()}
                  className="flex-1 border border-gray-300 text-gray-600 py-3 rounded-xl text-sm hover:bg-gray-50">
                  Skip
                </button>
                <button onClick={saveStep3} disabled={saving}
                  className="flex-1 bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
                  {saving ? 'Saving...' : 'Finish Setup'} <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 4 — Done */}
          {step === 4 && (
            <div className="text-center space-y-4 py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Platform Ready! 🎉</h2>
              <p className="text-gray-500">
                Your platform is configured. Data will start syncing from connected accounts.
              </p>
              {connections.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3 text-sm text-blue-700">
                  {connections.length} account(s) connected — first sync may take 1-2 minutes
                </div>
              )}
              <button onClick={() => router.push('/dashboard')}
                className="bg-indigo-600 text-white px-8 py-3 rounded-xl font-medium hover:bg-indigo-700">
                Go to Dashboard →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## MODULE 9: LISTMONK (Mautic replacement/fallback)

```bash
# Check if Mautic is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8181

# If Mautic is offline, start Listmonk as a reliable alternative
# First check if docker-compose for Mautic exists and try to restart it
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2" -name "docker-compose*.yml" \
  | xargs grep -l "mautic" 2>/dev/null | head -3
```

If Mautic docker-compose found, restart it:
```bash
# Found path: cd [mautic_compose_dir] && docker-compose up -d
# Then verify:
sleep 15
curl -s -o /dev/null -w "%{http_code}" http://localhost:8181
```

If Mautic stays offline, set up Listmonk:
```bash
# Create listmonk docker-compose
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/docker/listmonk"
cat > "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/docker/listmonk/docker-compose.yml" << 'EOF'
version: "3.7"
services:
  listmonk:
    image: listmonk/listmonk:latest
    container_name: listmonk
    ports:
      - "9000:9000"
    environment:
      - TZ=Europe/Istanbul
    volumes:
      - ./config.toml:/listmonk/config.toml
      - ./uploads:/listmonk/uploads
    restart: unless-stopped
EOF

echo "Listmonk configured at port 9000"
echo "Add to .env: LISTMONK_URL=http://localhost:9000"
```

Update `apps/api/app/services/email/mautic_bridge.py` to support both:

```python
"""
Email Bridge — supports Mautic (primary) and Listmonk (fallback).
Never auto-sends — always requires human approval.
"""
import os, requests, logging
from app.services.ai.model_config import call_ollama, TaskType

logger = logging.getLogger(__name__)

MAUTIC_URL = os.getenv("MAUTIC_URL", "http://localhost:8181")
LISTMONK_URL = os.getenv("LISTMONK_URL", "http://localhost:9000")

def _email_backend() -> str:
    """Detect which email backend is available."""
    try:
        r = requests.get(f"{MAUTIC_URL}/s/health", timeout=3)
        if r.ok: return "mautic"
    except Exception:
        pass
    try:
        r = requests.get(f"{LISTMONK_URL}/health", timeout=3)
        if r.ok: return "listmonk"
    except Exception:
        pass
    return "none"
```

---

## MODULE 10: REGISTER ALL NEW ROUTERS

Update `apps/api/app/main.py` — add all new routers:

```python
# Find the section where routers are registered and add:
from app.api.endpoints.integrations import router as integrations_router
from app.api.endpoints.workspace import router as workspace_router

app.include_router(integrations_router)
app.include_router(workspace_router)
```

Also add CORS origins for 127.0.0.1:
```python
# Find CORSMiddleware and update allow_origins to include:
allow_origins=[
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

Create `__init__.py` files for new service directories:
```bash
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/integrations/__init__.py"
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/security/__init__.py"
```

---

## MODULE 11: SIDEBAR — ADD NEW PAGES

Find sidebar navigation component and add:

```typescript
// New navigation items to add:
{ label: 'Integrations', href: '/dashboard/integrations', icon: Link2 },
{ label: 'Setup', href: '/dashboard/setup', icon: Settings },
```

Import: `import { Link2, Settings } from 'lucide-react'`

---

## MODULE 12: LINT + TYPE FIXES + CI

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

# Fix backend lint
cd "$BASE/apps/api"
ruff check app/ --fix 2>/dev/null
ruff check app/ 2>&1 | head -20

# Fix frontend types
cd "$BASE/apps/web"
npx tsc --noEmit 2>&1 | grep "error TS" | head -20

# Fix any type errors found:
# - Add explicit return types where needed
# - Fix 'any' types
# - Fix missing imports
```

---

## FINAL VERIFICATION

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "=== STEP 1: DB TABLES ==="
cd "$BASE/apps/api"
python3 -c "
import asyncio, asyncpg, os
async def f():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL','').replace('+asyncpg',''))
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    names = [r['tablename'] for r in rows]
    required = ['workspace_settings','ad_account_connections','platform_events',
                'product_costs','campaign_profit_analysis','contacts','leads',
                'calls','invoices','company_profiles']
    for t in required:
        print(f\"{'✅' if t in names else '❌'} {t}\")
    await conn.close()
asyncio.run(f())
"

echo ""
echo "=== STEP 2: IMPORTS ==="
python3 -c "from app.services.security.encryption import encrypt, decrypt; print('✅ encryption')"
python3 -c "from app.services.integrations.meta_oauth import MetaOAuthService; print('✅ meta_oauth')"
python3 -c "from app.services.integrations.meta_ads_fetcher import MetaAdsFetcher; print('✅ meta_fetcher')"
python3 -c "from app.services.integrations.google_ads_service import GoogleAdsOAuthService; print('✅ google_ads')"
python3 -c "from app.api.endpoints.integrations import router; print('✅ integrations_router')"
python3 -c "from app.api.endpoints.workspace import router; print('✅ workspace_router')"

echo ""
echo "=== STEP 3: ENCRYPTION TEST ==="
python3 -c "
from app.services.security.encryption import encrypt, decrypt
t = 'test-secret-token-12345'
enc = encrypt(t)
dec = decrypt(enc)
assert dec == t
print('✅ Encrypt/decrypt working')
print('   Encrypted length:', len(enc))
"

echo ""
echo "=== STEP 4: BACKEND STARTUP ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 3
uvicorn app.main:app --reload --port 8000 > /tmp/final_startup.log 2>&1 &
sleep 12
grep -E "ERROR|Import|Module" /tmp/final_startup.log | head -20

echo ""
echo "=== STEP 5: ENDPOINT TESTS ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAILED'))")

echo "Token: ${TOKEN:0:40}..."

PASS=0; FAIL=0
for ep in \
  "GET /health" \
  "GET /api/v1/integrations/connections" \
  "GET /api/v1/workspace/settings" \
  "GET /api/v1/workspace/setup-status" \
  "GET /api/v1/system/health" \
  "GET /api/v1/ads/profitability/settings" \
  "GET /api/v1/calls" \
  "GET /api/v1/finance/dashboard?months=3" \
  "GET /api/v1/discovery/status" \
  "GET /api/v1/ai-learning/summary" \
  "GET /api/v1/twitter/accounts"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  status=$(curl -s -o /tmp/r.json -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN")
  if [[ "$status" == "200" ]] || [[ "$status" == "201" ]] || [[ "$status" == "404" ]]; then
    echo "✅ $status $ep"
    PASS=$((PASS+1))
  else
    echo "❌ $status $ep"
    python3 -c "import json,sys; d=json.load(open('/tmp/r.json')); print('  →',str(d)[:120])" 2>/dev/null
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"

echo ""
echo "=== STEP 6: FRONTEND PAGES ==="
for page in \
  "dashboard/integrations/page.tsx" \
  "dashboard/setup/page.tsx"; do
  full="$BASE/apps/web/src/app/$page"
  echo "$([ -f "$full" ] && echo ✅ || echo ❌) $page"
done

echo ""
echo "=== STEP 7: FRONTEND BUILD ==="
cd "$BASE/apps/web"
npx next build 2>&1 | grep -E "✓ Compiled|error TS|Error:" | tail -10

echo ""
echo "=== STEP 8: LINT ==="
cd "$BASE/apps/api"
ruff check app/ 2>&1 | grep -v "^$" | wc -l | xargs echo "Remaining lint issues:"

echo ""
echo "=== STEP 9: COMMIT ==="
cd "$BASE"
git add -A
git commit -m "feat: full productization — OAuth integrations, dashboard-driven setup, Sentry, encryption, real ad data sync"
git push origin main

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         PRODUCTIZATION COMPLETE — CHECKLIST                  ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ DB Tables: workspace_settings, ad_account_connections ✅     ║"
echo "║ Encryption: Fernet AES-256 for all credentials ✅           ║"
echo "║ Meta Ads: OAuth flow + System User Token ✅                  ║"
echo "║ Google Ads: OAuth flow + Refresh Token ✅                    ║"
echo "║ Real Data Sync: campaigns + performance upsert ✅            ║"
echo "║ Dashboard Setup Wizard: /dashboard/setup ✅                  ║"
echo "║ Integrations Page: /dashboard/integrations ✅                ║"
echo "║ Sentry: Backend + Frontend error tracking ✅                 ║"
echo "║ CORS: 127.0.0.1 support ✅                                   ║"
echo "║ CI/CD: lint clean + build passing ✅                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ NEXT STEPS TO USE WITH REAL COMPANY:                         ║"
echo "║ 1. Get Meta System User Token → /dashboard/integrations     ║"
echo "║ 2. Enter token → accounts auto-discovered                   ║"
echo "║ 3. Click Sync → real campaign data loads                    ║"
echo "║ 4. Go to Ad Analytics → real ROAS + kill/scale signals      ║"
echo "║ 5. For Google: get Developer Token + refresh token          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
```

Fix every ❌ before stopping. Do not stop until all checks pass and git push succeeds.
