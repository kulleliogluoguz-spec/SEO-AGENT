# PHASE 2 REVIEW & COMPLETION AUDIT
## AI Growth OS — Full System Verification + Gap Filling
## Place at: apps/api/REVIEW_PHASE2.md

You just completed the Phase 2 implementation of AI Growth OS.
Now conduct a THOROUGH audit of everything built, verify correctness end-to-end,
and complete ANYTHING missing, broken, or half-implemented.

DO NOT declare done until every check below passes.
DO NOT ask for permission between steps.
Fix everything you find broken before moving forward.

---

## STEP 0: FULL CODEBASE AUDIT — READ BEFORE TOUCHING ANYTHING

Run every command. Read every output. Build a complete mental map.

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "=== BACKEND STRUCTURE ==="
find "$BASE/apps/api/app/services" -name "*.py" | sort
find "$BASE/apps/api/app/api/endpoints" -name "*.py" | sort

echo "=== FRONTEND PAGES ==="
find "$BASE/apps/web/src/app/dashboard" -name "page.tsx" | sort

echo "=== ROUTER REGISTRATIONS IN MAIN.PY ==="
grep -n "include_router\|import.*router" "$BASE/apps/api/app/main.py"

echo "=== .ENV NEW VARIABLES ==="
grep -E "TWILIO|HUGGINGFACE|MAUTIC|STORAGE|WEBHOOK" "$BASE/apps/api/.env"

echo "=== STORAGE DIRS ==="
ls "$BASE/storage/" 2>/dev/null || echo "storage dir missing"

echo "=== PASS STATEMENTS (incomplete code) ==="
grep -rn "^    pass$\|^        pass$" \
  "$BASE/apps/api/app/api/endpoints/calling.py" \
  "$BASE/apps/api/app/api/endpoints/finance.py" \
  "$BASE/apps/api/app/api/endpoints/email_bridge.py" \
  "$BASE/apps/api/app/api/endpoints/ai_learning.py" \
  2>/dev/null | wc -l

echo "=== INSTALLED PACKAGES ==="
pip list 2>/dev/null | grep -E "twilio|faster-whisper|whisperx|pyannote|paddleocr|pdfplumber|chromadb|sentence-transformers|reportlab|ffmpeg-python"

echo "=== DATABASE TABLES ==="
python3 -c "
import asyncio, asyncpg, os
async def main():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    try:
        conn = await asyncpg.connect(url)
        rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
        for r in rows: print(r['tablename'])
        await conn.close()
    except Exception as e:
        print(f'DB ERROR: {e}')
asyncio.run(main())
" 2>/dev/null

echo "=== OLLAMA MODELS ==="
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c \
  "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]"

echo "=== FRONTEND NPM PACKAGES ==="
cd "$BASE/apps/web" && cat package.json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); deps={**d.get('dependencies',{}),**d.get('devDependencies',{})}; [print(f'{k}: {v}') for k,v in deps.items() if any(x in k for x in ['livekit','wavesurfer','recharts'])]"

echo "=== SIDEBAR NAV (check for new sections) ==="
grep -rn "CALLING\|FINANCE\|AI SYSTEM\|Call Hub\|Lead Inbox\|P&L\|ai-learning" \
  "$BASE/apps/web/src" --include="*.tsx" | head -20
```

After reading all output, create this checklist in your mind:

```
REQUIRED FILES:
[ ] apps/api/app/services/ai/model_config.py
[ ] apps/api/app/services/ai/memory_service.py
[ ] apps/api/app/services/shared/data_bridge.py
[ ] apps/api/app/services/calling/call_engine.py
[ ] apps/api/app/services/calling/transcription_engine.py
[ ] apps/api/app/services/calling/lead_qualifier.py
[ ] apps/api/app/services/finance/invoice_intelligence.py
[ ] apps/api/app/services/email/mautic_bridge.py
[ ] apps/api/app/services/ad_analytics/report_generator.py
[ ] apps/api/app/api/endpoints/calling.py
[ ] apps/api/app/api/endpoints/finance.py
[ ] apps/api/app/api/endpoints/email_bridge.py
[ ] apps/api/app/api/endpoints/ai_learning.py

REQUIRED TABLES:
[ ] contacts
[ ] leads
[ ] lead_timeline
[ ] calls
[ ] call_transcripts
[ ] call_analysis
[ ] invoices
[ ] ai_feedback
[ ] ai_memory

REQUIRED FRONTEND PAGES:
[ ] /dashboard/calls/page.tsx
[ ] /dashboard/calls/[id]/page.tsx
[ ] /dashboard/calls/leads/[id]/page.tsx
[ ] /dashboard/finance/page.tsx
[ ] /dashboard/ai-learning/page.tsx

REQUIRED ROUTERS IN main.py:
[ ] calling_router
[ ] finance_router
[ ] email_router
[ ] ai_learning_router

REQUIRED SIDEBAR SECTIONS:
[ ] CALLING ENGINE
[ ] FINANCE
[ ] AI SYSTEM
```

---

## STEP 1: FIX DATABASE — Create any missing tables

Run this regardless — uses IF NOT EXISTS so safe to run multiple times:

```python
# Save as: apps/api/scripts/ensure_all_tables.py
import asyncio, asyncpg, os

async def ensure():
    url = os.getenv('DATABASE_URL', '').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            full_name VARCHAR(500),
            company_name VARCHAR(500),
            email VARCHAR(255),
            phone VARCHAR(100),
            website VARCHAR(500),
            linkedin_url VARCHAR(500),
            country VARCHAR(100),
            city VARCHAR(100),
            industry VARCHAR(200),
            company_size VARCHAR(50),
            source VARCHAR(100) DEFAULT 'manual',
            tags TEXT[],
            custom_fields JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS leads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contact_id UUID REFERENCES contacts(id) NOT NULL,
            workspace_id UUID NOT NULL,
            status VARCHAR(50) DEFAULT 'new',
            qualification_score INTEGER DEFAULT 0,
            category VARCHAR(50),
            last_contact_date TIMESTAMPTZ,
            next_follow_up_date DATE,
            follow_up_count INTEGER DEFAULT 0,
            call_count INTEGER DEFAULT 0,
            email_count INTEGER DEFAULT 0,
            ad_touched BOOLEAN DEFAULT FALSE,
            ai_summary TEXT,
            ai_objections TEXT[],
            ai_intent VARCHAR(100),
            ai_urgency VARCHAR(50),
            ai_next_action TEXT,
            estimated_deal_value NUMERIC(14,2),
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS lead_timeline (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id UUID REFERENCES leads(id) NOT NULL,
            event_type VARCHAR(100),
            title VARCHAR(500),
            description TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS ai_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            user_id UUID,
            module VARCHAR(100),
            feedback_type VARCHAR(50),
            original_recommendation JSONB,
            user_action JSONB,
            outcome JSONB,
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
            consent_timestamp TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS call_transcripts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            call_id UUID REFERENCES calls(id) NOT NULL,
            speaker VARCHAR(50) DEFAULT 'SPEAKER_0',
            speaker_label VARCHAR(100),
            text TEXT NOT NULL,
            start_time NUMERIC(10,3) DEFAULT 0,
            end_time NUMERIC(10,3) DEFAULT 0,
            confidence NUMERIC(5,4),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS call_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            call_id UUID REFERENCES calls(id) NOT NULL UNIQUE,
            overall_sentiment VARCHAR(50),
            customer_sentiment VARCHAR(50),
            agent_sentiment VARCHAR(50),
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
            customer_tax_id VARCHAR(100),
            currency VARCHAR(10) DEFAULT 'TRY',
            subtotal NUMERIC(14,2),
            tax_amount NUMERIC(14,2),
            total_amount NUMERIC(14,2),
            direction VARCHAR(20) DEFAULT 'incoming',
            category VARCHAR(100) DEFAULT 'general',
            tax_category VARCHAR(100),
            is_deductible BOOLEAN DEFAULT FALSE,
            vat_rate NUMERIC(5,2),
            vat_amount NUMERIC(14,2),
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

        CREATE INDEX IF NOT EXISTS idx_contacts_workspace ON contacts(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email) WHERE email IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone) WHERE phone IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_leads_contact ON leads(contact_id);
        CREATE INDEX IF NOT EXISTS idx_leads_workspace_status ON leads(workspace_id, status);
        CREATE INDEX IF NOT EXISTS idx_leads_workspace_score ON leads(workspace_id, qualification_score DESC);
        CREATE INDEX IF NOT EXISTS idx_calls_contact ON calls(contact_id);
        CREATE INDEX IF NOT EXISTS idx_calls_workspace ON calls(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_calls_lead ON calls(lead_id);
        CREATE INDEX IF NOT EXISTS idx_transcripts_call ON call_transcripts(call_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_workspace ON invoices(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date DESC NULLS LAST);
        CREATE INDEX IF NOT EXISTS idx_ai_memory_lookup ON ai_memory(workspace_id, module, key);
        CREATE INDEX IF NOT EXISTS idx_timeline_lead ON lead_timeline(lead_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_feedback_workspace ON ai_feedback(workspace_id, module);
    """)

    # Verify
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    names = [t['tablename'] for t in tables]
    required = ['contacts','leads','lead_timeline','calls','call_transcripts',
                'call_analysis','invoices','ai_feedback','ai_memory']
    print("\n=== TABLE STATUS ===")
    all_ok = True
    for t in required:
        status = '✅' if t in names else '❌ MISSING'
        print(f"{status} {t}")
        if t not in names:
            all_ok = False
    print(f"\n{'✅ All tables OK' if all_ok else '❌ Some tables missing!'}")
    await conn.close()

asyncio.run(ensure())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/ensure_all_tables.py
```

---

## STEP 2: FIX MISSING PACKAGES

Install anything missing from the audit:

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"

# Check what's actually installed
pip list 2>/dev/null | grep -E "twilio|faster.whisper|pyannote|paddleocr|pdfplumber|pdf2image|pytesseract|chromadb|sentence.transform|reportlab|ffmpeg.python|pydub|soundfile"

# Install ALL required packages (idempotent)
pip install twilio==9.3.0 --quiet
pip install faster-whisper==1.0.3 --quiet
pip install pyannote.audio==3.3.2 --quiet
pip install pdfplumber==0.11.0 --quiet
pip install pdf2image==1.17.0 --quiet
pip install pytesseract==0.3.13 --quiet
pip install pillow==10.4.0 --quiet
pip install chromadb==0.5.23 --quiet
pip install sentence-transformers==3.3.1 --quiet
pip install reportlab==4.2.0 --quiet
pip install ffmpeg-python==0.2.0 --quiet
pip install pydub==0.25.1 --quiet
pip install soundfile==0.12.1 --quiet

# Try WhisperX (may fail on some systems — that's OK, faster-whisper is fallback)
pip install whisperx==3.1.6 --quiet 2>/dev/null || echo "whisperx install failed — faster-whisper fallback will be used"

# Try PaddleOCR (large, optional — pytesseract is fallback)
pip install paddleocr==2.8.1 --quiet 2>/dev/null || echo "PaddleOCR install failed — pytesseract fallback will be used"

echo "Package installation complete"

# Frontend packages
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npm install --save \
  @livekit/components-react \
  @livekit/client \
  livekit-client \
  wavesurfer.js \
  2>/dev/null

echo "Frontend packages done"
```

---

## STEP 3: ENSURE ALL SERVICE FILES EXIST AND ARE COMPLETE

For each required service file, verify it exists and has no `pass` stubs.
If missing or incomplete, create/fix it now.

### 3A: Check and fix model_config.py

```bash
cat "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/ai/model_config.py" 2>/dev/null | wc -l
```

If output is 0 or file missing, create it:

**File: `apps/api/app/services/ai/model_config.py`**

```python
"""
AI Model Configuration — Local Model Stack.
All inference via Ollama. Zero external API calls.
"""
import logging, requests, re, json
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)
OLLAMA_BASE = "http://localhost:11434"


class TaskType(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    REASONING = "reasoning"
    MULTILINGUAL = "multilingual"
    CREATIVE = "creative"


class ModelSelector:
    TASK_MODELS = {
        TaskType.FAST:         ["qwen3:8b", "gemma4:2b", "qwen3:8b"],
        TaskType.STANDARD:     ["gemma4:27b", "qwen3:14b", "qwen3:8b"],
        TaskType.REASONING:    ["deepseek-r1:8b", "gemma4:27b", "qwen3:8b"],
        TaskType.MULTILINGUAL: ["qwen3:14b", "qwen3:8b", "gemma4:27b"],
        TaskType.CREATIVE:     ["gemma4:27b", "qwen3:14b", "qwen3:8b"],
    }
    _available: Optional[list] = None

    @classmethod
    def get_available(cls) -> list[str]:
        if cls._available is None:
            try:
                r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
                cls._available = [m["name"] for m in r.json().get("models", [])]
            except Exception:
                cls._available = ["qwen3:8b"]
        return cls._available

    @classmethod
    def select(cls, task: TaskType) -> str:
        avail = cls.get_available()
        for candidate in cls.TASK_MODELS.get(task, ["qwen3:8b"]):
            prefix = candidate.split(":")[0]
            for a in avail:
                if prefix in a:
                    return a
        return avail[0] if avail else "qwen3:8b"

    @classmethod
    def invalidate_cache(cls):
        cls._available = None


def call_ollama(prompt: str, task: TaskType = TaskType.STANDARD,
                model: Optional[str] = None, max_tokens: int = 500,
                temperature: float = 0.3, system: Optional[str] = None,
                timeout: int = 120) -> str:
    selected = model or ModelSelector.select(task)
    payload = {
        "model": selected, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temperature}
    }
    if system:
        payload["system"] = system
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        logger.error(f"Ollama timeout ({timeout}s) model={selected}")
        return "[AI timeout — model loading. Retry in 30s.]"
    except requests.exceptions.ConnectionError:
        return "[AI unavailable — run: ollama serve]"
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"[AI error: {str(e)[:100]}]"


def call_ollama_json(prompt: str, schema_example: dict,
                     task: TaskType = TaskType.STANDARD,
                     model: Optional[str] = None, timeout: int = 120) -> dict:
    json_prompt = (f"{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON. "
                   f"No explanation, no markdown, no backticks.\n"
                   f"Example format: {str(schema_example)}")
    response = call_ollama(json_prompt, task=task, model=model,
                           max_tokens=1000, temperature=0.1, timeout=timeout)
    clean = response.strip()
    for prefix in ["```json", "```"]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    clean = clean.rstrip("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        logger.error(f"JSON parse failed: {clean[:200]}")
        return {}
```

### 3B: Check and fix shared __init__ files

```bash
# Ensure __init__.py files exist in all new packages
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/ai/__init__.py"
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/calling/__init__.py"
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/finance/__init__.py"
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/email/__init__.py"
touch "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/shared/__init__.py"
```

### 3C: Verify all service files

For each file below, check it:
1. Exists
2. Has no empty `pass` stubs
3. Has proper imports
4. Functions are complete

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app"

for f in \
  "services/ai/model_config.py" \
  "services/ai/memory_service.py" \
  "services/shared/data_bridge.py" \
  "services/calling/call_engine.py" \
  "services/calling/transcription_engine.py" \
  "services/calling/lead_qualifier.py" \
  "services/finance/invoice_intelligence.py" \
  "services/email/mautic_bridge.py" \
  "api/endpoints/calling.py" \
  "api/endpoints/finance.py" \
  "api/endpoints/email_bridge.py" \
  "api/endpoints/ai_learning.py"; do
  full="$BASE/$f"
  if [ -f "$full" ]; then
    lines=$(wc -l < "$full")
    passes=$(grep -c "^    pass$\|^        pass$" "$full" 2>/dev/null || echo 0)
    echo "✅ $f ($lines lines, $passes pass stubs)"
  else
    echo "❌ MISSING: $f"
  fi
done
```

For every ❌ MISSING file, create it now using the complete implementation from MISSION_PHASE2.md.
For every file with pass stubs > 0, implement those functions now.

---

## STEP 4: VERIFY ROUTER REGISTRATIONS

```bash
grep -n "include_router\|from app.api.endpoints" \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/main.py"
```

Required registrations. If any are missing, add them to main.py:

```python
# These 4 lines must exist in main.py — add after existing router registrations:
from app.api.endpoints.calling import router as calling_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints.email_bridge import router as email_router
from app.api.endpoints.ai_learning import router as ai_learning_router

app.include_router(calling_router)
app.include_router(finance_router)
app.include_router(email_router)
app.include_router(ai_learning_router)
```

---

## STEP 5: LIVE BACKEND TEST

```bash
# Kill and restart backend fresh
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 3

cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
uvicorn app.main:app --reload --port 8000 > /tmp/backend_startup.log 2>&1 &
sleep 12

# Check for startup errors
cat /tmp/backend_startup.log | grep -E "ERROR|ImportError|ModuleNotFoundError|Exception" | head -20

# Get JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; data=json.load(sys.stdin); print(data.get('access_token', data.get('detail','FAILED')))" 2>/dev/null)

echo "Token: ${TOKEN:0:50}..."

if [[ "$TOKEN" == "FAILED"* ]] || [[ -z "$TOKEN" ]]; then
  echo "❌ Login failed — check backend logs"
  cat /tmp/backend_startup.log | tail -30
  exit 1
fi

# Test every new endpoint
echo ""
echo "=== ENDPOINT STATUS ==="
declare -a TESTS=(
  "GET /api/v1/calls"
  "GET /api/v1/calls/contacts"
  "GET /api/v1/calls/leads"
  "GET /api/v1/finance/invoices"
  "GET /api/v1/finance/dashboard?months=3"
  "GET /api/v1/ai-learning/summary"
  "GET /api/v1/ads/accounts"
  "GET /api/v1/ads/recommendations"
  "GET /api/v1/ads/portfolio/summary"
  "GET /health"
)

PASS=0; FAIL=0
for test in "${TESTS[@]}"; do
  method=$(echo $test | awk '{print $1}')
  path=$(echo $test | awk '{print $2}')
  status=$(curl -s -o /tmp/ep_response.json -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")
  if [[ "$status" == "200" ]] || [[ "$status" == "201" ]]; then
    echo "✅ $status $test"
    PASS=$((PASS+1))
  else
    echo "❌ $status $test"
    cat /tmp/ep_response.json 2>/dev/null | head -3
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"
```

For every ❌ failed endpoint:
1. Read the error response
2. Find the cause (missing import, DB error, wrong query)
3. Fix it
4. Re-test until ✅

---

## STEP 6: FIX COMMON BACKEND ISSUES

### Issue type 1: ImportError on startup

```bash
# Check imports actually work
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 -c "from app.api.endpoints.calling import router; print('calling ✅')"
python3 -c "from app.api.endpoints.finance import router; print('finance ✅')"
python3 -c "from app.api.endpoints.email_bridge import router; print('email_bridge ✅')"
python3 -c "from app.api.endpoints.ai_learning import router; print('ai_learning ✅')"
python3 -c "from app.services.ai.model_config import call_ollama; print('model_config ✅')"
python3 -c "from app.services.shared.data_bridge import DataBridge; print('data_bridge ✅')"
```

Fix any import that fails before proceeding.

### Issue type 2: DB column type mismatch

If endpoints return 500 errors about JSON or UUID:

```bash
python3 -c "
import asyncio, asyncpg, os
async def main():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    # Check column types
    for table in ['contacts','leads','calls','invoices']:
        cols = await conn.fetch('''
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = \$1 ORDER BY ordinal_position
        ''', table)
        print(f'\\n{table}:')
        for c in cols: print(f'  {c[\"column_name\"]}: {c[\"data_type\"]}')
    await conn.close()
asyncio.run(main())
"
```

### Issue type 3: Missing workspace_id on user object

```bash
# Check what fields the user object has
grep -n "workspace_id\|current_user\." \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/api/dependencies/auth.py" | head -20
grep -n "workspace_id" \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/models" --include="*.py" -r | head -10
```

If workspace_id doesn't exist on the user model, find the correct field name and update all new endpoints accordingly.

---

## STEP 7: SEED DEMO DATA FOR ALL NEW MODULES

Create realistic demo data so all dashboards show content immediately:

```python
# Save as: apps/api/scripts/seed_full_demo.py
import asyncio, asyncpg, os, uuid, json
from datetime import date, timedelta, datetime
import random

async def seed():
    url = os.getenv('DATABASE_URL', '').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)

    # Get workspace ID
    workspace = await conn.fetchrow("SELECT id FROM workspaces LIMIT 1")
    if not workspace:
        print("❌ No workspace found")
        return
    wid = workspace['id']
    print(f"Using workspace: {wid}")

    # ─── CONTACTS ────────────────────────────────────────
    contacts_data = [
        {"full_name":"Ahmet Yılmaz","company_name":"TechSoft A.Ş.","email":"ahmet@techsoft.com.tr","phone":"+90 532 111 2233","industry":"Software","city":"Istanbul","source":"call"},
        {"full_name":"Ayşe Kaya","company_name":"Marketing Pro","email":"ayse@marketingpro.com","phone":"+90 533 222 3344","industry":"Marketing","city":"Ankara","source":"email"},
        {"full_name":"Mehmet Demir","company_name":"Retail Plus","email":"mehmet@retailplus.com","phone":"+90 541 333 4455","industry":"Retail","city":"Izmir","source":"call"},
        {"full_name":"Fatma Şahin","company_name":"E-Commerce Hub","email":"fatma@ecommhub.com","phone":"+90 542 444 5566","industry":"E-Commerce","city":"Istanbul","source":"ad"},
        {"full_name":"Ali Çelik","company_name":"B2B Solutions","email":"ali@b2bsolutions.com","phone":"+90 505 555 6677","industry":"Consulting","city":"Bursa","source":"call"},
        {"full_name":"Zeynep Arslan","company_name":"Digital First","email":"zeynep@digitalfirst.com","phone":"+90 506 666 7788","industry":"Digital Agency","city":"Antalya","source":"call"},
    ]

    contact_ids = []
    for c in contacts_data:
        existing = await conn.fetchrow(
            "SELECT id FROM contacts WHERE email=$1 AND workspace_id=$2", c["email"], wid
        )
        if existing:
            contact_ids.append(existing['id'])
            continue
        cid = await conn.fetchval(
            """INSERT INTO contacts(workspace_id,full_name,company_name,email,phone,industry,city,source)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
            wid,c["full_name"],c["company_name"],c["email"],c["phone"],
            c["industry"],c["city"],c["source"]
        )
        contact_ids.append(cid)
    print(f"✅ Contacts: {len(contact_ids)}")

    # ─── LEADS ───────────────────────────────────────────
    lead_data = [
        {"score":82,"cat":"hot","status":"qualified","intent":"interested","urgency":"high",
         "summary":"Very interested in enterprise plan. Has budget approval. Wants demo next week.",
         "next_action":"Schedule product demo for next Tuesday"},
        {"score":65,"cat":"warm","status":"contacted","intent":"evaluating","urgency":"medium",
         "summary":"Currently evaluating 3 vendors. Price is main concern. Has 3-month timeline.",
         "next_action":"Send competitive pricing comparison document"},
        {"score":45,"cat":"warm","status":"contacted","intent":"evaluating","urgency":"low",
         "summary":"Interested but not urgent. Will revisit in Q2. Asked for case studies.",
         "next_action":"Send relevant case studies and follow up in 30 days"},
        {"score":78,"cat":"hot","status":"qualified","intent":"interested","urgency":"high",
         "summary":"Strong buying signals. Budget approved. Needs quick implementation.",
         "next_action":"Send proposal and schedule technical call"},
        {"score":20,"cat":"cold","status":"contacted","intent":"not_interested","urgency":"low",
         "summary":"Not the right time. Company restructuring. May revisit in 6 months.",
         "next_action":"Add to cold reactivation sequence for Q4"},
        {"score":55,"cat":"warm","status":"new","intent":"follow_up_needed","urgency":"medium",
         "summary":"Left voicemail twice. Engaged via email. Interested in growth package.",
         "next_action":"Try WhatsApp contact or connect on LinkedIn"},
    ]

    lead_ids = []
    for i, (cid, ld) in enumerate(zip(contact_ids, lead_data)):
        existing = await conn.fetchrow(
            "SELECT id FROM leads WHERE contact_id=$1 AND workspace_id=$2", cid, wid
        )
        if existing:
            lead_ids.append(existing['id'])
            continue
        lid = await conn.fetchval(
            """INSERT INTO leads(contact_id,workspace_id,status,qualification_score,category,
               ai_summary,ai_intent,ai_urgency,ai_next_action,last_contact_date)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW()-($10||' days')::interval) RETURNING id""",
            cid,wid,ld["status"],ld["score"],ld["cat"],
            ld["summary"],ld["intent"],ld["urgency"],ld["next_action"],
            str(random.randint(0,14))
        )
        lead_ids.append(lid)
    print(f"✅ Leads: {len(lead_ids)}")

    # ─── CALLS ───────────────────────────────────────────
    call_ids = []
    for i, (cid, lid) in enumerate(zip(contact_ids[:4], lead_ids[:4])):
        call_id = str(uuid.uuid4())
        days_ago = random.randint(0,21)
        duration = random.randint(240, 1800)
        await conn.execute(
            """INSERT INTO calls(id,workspace_id,contact_id,lead_id,direction,status,
               started_at,ended_at,duration_seconds,provider,consent_given,
               transcription_status,analysis_status)
               VALUES($1,$2,$3,$4,'outbound','completed',
               NOW()-($5||' days')::interval,
               NOW()-($5||' days')::interval+($6||' seconds')::interval,
               $6,'manual_upload',true,'completed','completed')
               ON CONFLICT DO NOTHING""",
            call_id,wid,cid,lid,str(days_ago),duration
        )
        call_ids.append(call_id)

        # Add transcript segments
        sample_convos = [
            ("SPEAKER_0","Merhaba, aramanızın sebebi nedir acaba?",0,4),
            ("SPEAKER_1","Evet merhaba, ürününüzle ilgili bilgi almak istiyordum.",4,9),
            ("SPEAKER_0","Tabii, hangi konuda yardımcı olabilirim?",9,13),
            ("SPEAKER_1","Fiyatlandırma konusunda daha detaylı bilgi alabilir miyim?",13,19),
            ("SPEAKER_0","Elbette, size özel bir teklif hazırlayabiliriz.",19,24),
            ("SPEAKER_1","Harika, bütçemiz var bu konuda ilerleyebiliriz.",24,30),
        ]
        for spk, txt, start, end in sample_convos:
            await conn.execute(
                """INSERT INTO call_transcripts(call_id,speaker,text,start_time,end_time,confidence)
                   VALUES($1,$2,$3,$4,$5,0.92) ON CONFLICT DO NOTHING""",
                call_id, spk, txt, start, end
            )

        # Add call analysis
        scores = [82,65,78,55]
        cats = ["hot","warm","hot","warm"]
        await conn.execute(
            """INSERT INTO call_analysis(call_id,overall_sentiment,customer_sentiment,
               intent,urgency,objections,buying_signals,action_items,
               qualification_score,qualification_category,summary,next_action,follow_up_days,
               ai_model_used,processing_duration_ms)
               VALUES($1,'mixed_positive','positive','interested','medium',
               $2,$3,$4,$5,$6,$7,$8,3,'gemma4:27b',4500)
               ON CONFLICT(call_id) DO NOTHING""",
            call_id,
            ["price","timing"],
            ["mentioned budget","asked about implementation"],
            ["send proposal","schedule follow-up"],
            scores[i],cats[i],
            f"Customer showed interest in the product. Main concern was pricing. Call lasted {duration//60} minutes.",
            "Send detailed proposal with pricing options"
        )

    # Add timeline events
    for lid in lead_ids[:4]:
        events = [
            ("call_made","Outbound call completed","12-minute discovery call completed."),
            ("email_sent","Follow-up email sent","Sent pricing document as requested."),
            ("score_updated","Lead score updated","AI qualification score updated based on call analysis."),
        ]
        for etype, title, desc in events:
            await conn.execute(
                """INSERT INTO lead_timeline(lead_id,event_type,title,description,metadata)
                   VALUES($1,$2,$3,$4,'{}') ON CONFLICT DO NOTHING""",
                lid, etype, title, desc
            )
    print(f"✅ Calls: {len(call_ids)} with transcripts and analysis")

    # ─── INVOICES ────────────────────────────────────────
    invoice_data = [
        {"vendor":"AWS Turkey","inv_num":"AWS-2024-001","direction":"incoming","cat":"software",
         "total":2400.0,"vat":432.0,"vat_rate":18,"currency":"USD","date":date.today()-timedelta(days=5)},
        {"vendor":"Acme Corp","inv_num":"ACME-2024-089","direction":"outgoing","cat":"professional_services",
         "total":15000.0,"vat":3000.0,"vat_rate":20,"currency":"TRY","date":date.today()-timedelta(days=10)},
        {"vendor":"Google Ads","inv_num":"GADS-2024-112","direction":"incoming","cat":"advertising",
         "total":5800.0,"vat":1160.0,"vat_rate":20,"currency":"TRY","date":date.today()-timedelta(days=15)},
        {"vendor":"Microsoft 365","inv_num":"MS365-2024-003","direction":"incoming","cat":"software",
         "total":890.0,"vat":178.0,"vat_rate":20,"currency":"USD","date":date.today()-timedelta(days=20)},
        {"vendor":"TechSoft A.Ş.","inv_num":"TS-2024-056","direction":"outgoing","cat":"software",
         "total":22000.0,"vat":4400.0,"vat_rate":20,"currency":"TRY","date":date.today()-timedelta(days=3)},
    ]

    for inv in invoice_data:
        inv_id = str(uuid.uuid4())
        sub = inv["total"] - inv["vat"]
        deductible = inv["direction"] == "incoming"
        tax_impact = (f"KDV mahsup: {inv['vat']:.0f} {inv['currency']}" if deductible
                      else f"KDV beyan edilmeli: {inv['vat']:.0f} {inv['currency']}")
        await conn.execute(
            """INSERT INTO invoices(id,workspace_id,file_name,file_type,invoice_number,
               invoice_date,vendor_name,currency,subtotal,tax_amount,total_amount,
               direction,category,vat_rate,vat_amount,is_deductible,
               estimated_tax_impact,ai_notes,extraction_status,confidence_score)
               VALUES($1,$2,$3,'pdf',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,'completed',0.91)
               ON CONFLICT DO NOTHING""",
            inv_id,wid,f"{inv['vendor_name'] if 'vendor_name' in inv else inv['vendor']}_invoice.pdf",
            inv["inv_num"],inv["date"],inv["vendor"],inv["currency"],
            sub,inv["vat"],inv["total"],inv["direction"],inv["cat"],
            inv["vat_rate"],inv["vat"],deductible,tax_impact,
            f"Fatura analizi tamamlandı. {tax_impact}\n\n⚠️ Bu bir tahmindir. Mali müşavirinize danışın."
        )
    print(f"✅ Invoices: {len(invoice_data)}")

    # ─── AI FEEDBACK SAMPLES ─────────────────────────────
    modules = ["ad_analytics","lead_qualification","invoice"]
    for mod in modules:
        for _ in range(random.randint(3,8)):
            action = random.choice(["accepted","rejected","accepted","accepted"])
            await conn.execute(
                """INSERT INTO ai_feedback(workspace_id,module,feedback_type,
                   original_recommendation,user_action)
                   VALUES($1,$2,$3,'{"type":"scale","priority":"high"}'::jsonb,
                   '{"action":"applied"}'::jsonb)""",
                wid, mod, action
            )
    print("✅ AI feedback samples")

    print("\n✅ Full demo data seeded successfully!")
    print(f"  {len(contact_ids)} contacts | {len(lead_ids)} leads | {len(call_ids)} calls | {len(invoice_data)} invoices")
    await conn.close()

asyncio.run(seed())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/seed_full_demo.py
```

---

## STEP 8: VERIFY ALL FRONTEND PAGES

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src/app/dashboard"

echo "=== FRONTEND PAGE STATUS ==="
for page in \
  "calls/page.tsx" \
  "calls/[id]/page.tsx" \
  "calls/leads/[id]/page.tsx" \
  "finance/page.tsx" \
  "ai-learning/page.tsx"; do
  full="$BASE/$page"
  if [ -f "$full" ]; then
    lines=$(wc -l < "$full")
    echo "✅ $page ($lines lines)"
  else
    echo "❌ MISSING: $page"
  fi
done
```

### For any MISSING page, create it now:

#### `apps/web/src/app/dashboard/calls/page.tsx` — Call Hub

```typescript
'use client'
import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { Phone, Upload, Users, TrendingUp, AlertCircle, ChevronRight } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json'
})

const CAT_STYLE: Record<string,string> = {
  hot:   'bg-red-100 text-red-700 border-red-300',
  warm:  'bg-orange-100 text-orange-700 border-orange-300',
  cold:  'bg-blue-100 text-blue-700 border-blue-300',
  nurture: 'bg-gray-100 text-gray-500 border-gray-300',
  disqualified: 'bg-gray-50 text-gray-400 border-gray-200',
}

export default function CallHub() {
  const [calls, setCalls]     = useState<any[]>([])
  const [leads, setLeads]     = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState<'leads'|'calls'>('leads')
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    const [cr, lr] = await Promise.all([
      fetch(`${API}/api/v1/calls`, { headers: hdrs() }),
      fetch(`${API}/api/v1/calls/leads`, { headers: hdrs() }),
    ])
    if (cr.ok) setCalls((await cr.json()).calls || [])
    if (lr.ok) setLeads((await lr.json()).leads || [])
    setLoading(false)
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    await fetch(`${API}/api/v1/calls/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
      body: fd
    })
    setTimeout(() => { load(); setUploading(false) }, 3000)
    if (fileRef.current) fileRef.current.value = ''
  }

  const hotCount  = leads.filter(l => l.category === 'hot').length
  const warmCount = leads.filter(l => l.category === 'warm').length
  const avgScore  = leads.length
    ? Math.round(leads.reduce((a,l) => a + (l.qualification_score||0), 0) / leads.length)
    : 0

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calling Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered call analysis and lead qualification</p>
        </div>
        <div className="flex gap-3">
          <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300
            text-sm font-medium cursor-pointer hover:bg-gray-50 transition ${uploading ? 'opacity-60 pointer-events-none' : ''}`}>
            <Upload className="w-4 h-4" />
            {uploading ? 'Processing...' : 'Upload Recording'}
            <input ref={fileRef} type="file" accept=".wav,.mp3,.m4a,.ogg,.webm"
                   onChange={handleUpload} className="hidden" />
          </label>
          <Link href="/dashboard/calls/new-contact"
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
            <Users className="w-4 h-4" /> Add Contact
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label:'Total Leads', val: leads.length, icon: Users, color:'text-indigo-600' },
          { label:'Hot Leads',   val: hotCount,     icon: AlertCircle, color:'text-red-500' },
          { label:'Warm Leads',  val: warmCount,    icon: TrendingUp, color:'text-orange-500' },
          { label:'Avg Score',   val: avgScore,     icon: Phone, color:'text-green-600' },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-xl border p-4 shadow-sm">
            <div className={`flex items-center gap-2 text-sm mb-1 ${k.color}`}>
              <k.icon className="w-4 h-4" /> {k.label}
            </div>
            <div className="text-2xl font-bold text-gray-900">{k.val}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(['leads','calls'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'leads' ? `Lead Inbox (${leads.length})` : `Call History (${calls.length})`}
          </button>
        ))}
      </div>

      {/* Lead Inbox */}
      {tab === 'leads' && (
        <div className="space-y-3">
          {loading ? (
            Array.from({length:4}).map((_,i) => (
              <div key={i} className="bg-white rounded-xl border p-4 h-20 animate-pulse bg-gray-100" />
            ))
          ) : leads.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No leads yet</p>
              <p className="text-sm mt-1">Upload a call recording to get started</p>
            </div>
          ) : leads.map((lead: any) => (
            <Link key={lead.id} href={`/dashboard/calls/leads/${lead.id}`}
              className="block bg-white rounded-xl border hover:border-indigo-300 hover:shadow-md transition-all p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center
                    text-indigo-700 font-bold text-sm flex-shrink-0">
                    {(lead.full_name || 'U').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-semibold text-gray-800">{lead.full_name || 'Unknown'}</div>
                    <div className="text-sm text-gray-500">
                      {lead.company_name}{lead.email ? ` · ${lead.email}` : ''}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {lead.category && (
                    <span className={`text-xs px-2 py-1 rounded-full border font-medium capitalize
                      ${CAT_STYLE[lead.category] || 'bg-gray-100 text-gray-500 border-gray-300'}`}>
                      {lead.category}
                    </span>
                  )}
                  <div className="text-right">
                    <div className="font-bold text-gray-800">{lead.qualification_score || 0}</div>
                    <div className="text-xs text-gray-400">score</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                </div>
              </div>
              {lead.ai_next_action && (
                <div className="mt-2 text-sm text-indigo-600 flex items-center gap-1">
                  <span>💡</span> {lead.ai_next_action}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}

      {/* Call History */}
      {tab === 'calls' && (
        <div className="space-y-2">
          {loading ? (
            Array.from({length:3}).map((_,i) => (
              <div key={i} className="bg-white rounded-xl border p-4 h-16 animate-pulse bg-gray-100" />
            ))
          ) : calls.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Phone className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No calls recorded yet</p>
            </div>
          ) : calls.map((call: any) => (
            <Link key={call.id} href={`/dashboard/calls/${call.id}`}
              className="block bg-white rounded-xl border hover:border-indigo-200 p-4 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    call.status === 'completed' ? 'bg-green-500' :
                    call.status === 'failed' ? 'bg-red-500' : 'bg-yellow-400'
                  }`} />
                  <div>
                    <div className="font-medium text-gray-800">
                      {call.full_name || call.provider_call_id || call.id.slice(0,8)}
                    </div>
                    <div className="text-sm text-gray-500">
                      {call.started_at ? new Date(call.started_at).toLocaleString('tr-TR') : 'Unknown time'}
                      {call.duration_seconds
                        ? ` · ${Math.floor(call.duration_seconds/60)}m ${call.duration_seconds%60}s`
                        : ''}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {call.qualification_score != null && (
                    <div className="text-right">
                      <div className="font-bold text-gray-800">{call.qualification_score}</div>
                      <div className="text-xs text-gray-400">score</div>
                    </div>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    call.transcription_status === 'completed' ? 'bg-green-100 text-green-700' :
                    call.transcription_status === 'processing' ? 'bg-yellow-100 text-yellow-600' :
                    'bg-gray-100 text-gray-500'
                  }`}>
                    {call.transcription_status === 'completed' ? '✓ Analyzed' :
                     call.transcription_status === 'processing' ? '⟳ Analyzing' : '○ Pending'}
                  </span>
                </div>
              </div>
              {call.summary && (
                <div className="mt-2 text-sm text-gray-600 line-clamp-1 pl-5">{call.summary}</div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
```

#### `apps/web/src/app/dashboard/calls/[id]/page.tsx` — Transcript Viewer

```typescript
'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, RefreshCw, AlertCircle, CheckCircle, Clock } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json'
})

const SPEAKER_COLORS: Record<string,string> = {
  SPEAKER_0: 'bg-blue-100 text-blue-800',
  SPEAKER_1: 'bg-green-100 text-green-800',
  SPEAKER_2: 'bg-purple-100 text-purple-800',
}

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m.toString().padStart(2,'0')}:${sec.toString().padStart(2,'0')}`
}

export default function TranscriptViewer() {
  const { id } = useParams()
  const router = useRouter()
  const [data, setData]           = useState<any>(null)
  const [loading, setLoading]     = useState(true)
  const [reanalyzing, setReanalyzing] = useState(false)

  useEffect(() => { if (id) load() }, [id])

  async function load() {
    setLoading(true)
    const r = await fetch(`${API}/api/v1/calls/${id}/transcript`, { headers: hdrs() })
    if (r.ok) setData(await r.json())
    setLoading(false)
  }

  async function reanalyze() {
    setReanalyzing(true)
    await fetch(`${API}/api/v1/calls/${id}/reanalyze`, { method: 'POST', headers: hdrs() })
    await load()
    setReanalyzing(false)
  }

  if (loading) return (
    <div className="p-6 space-y-4">
      <div className="h-8 bg-gray-200 rounded animate-pulse w-48" />
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-3">
          {Array.from({length:6}).map((_,i) => <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />)}
        </div>
        <div className="h-96 bg-gray-200 rounded animate-pulse" />
      </div>
    </div>
  )

  const an = data?.analysis || {}
  const segments = data?.segments || []

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/calls" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-bold text-gray-900">Call Transcript</h1>
          <span className="text-sm text-gray-400">{id?.toString().slice(0,8)}...</span>
        </div>
        <button onClick={reanalyze} disabled={reanalyzing}
          className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50
            disabled:opacity-50 transition">
          <RefreshCw className={`w-4 h-4 ${reanalyzing ? 'animate-spin' : ''}`} />
          {reanalyzing ? 'Re-analyzing...' : 'Re-analyze with AI'}
        </button>
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Transcript — 60% */}
        <div className="col-span-3 space-y-3">
          {segments.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border p-8 text-center text-gray-400">
              <Clock className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p>Transcript pending or processing...</p>
            </div>
          ) : segments.map((seg: any, i: number) => (
            <div key={i} className="flex gap-3">
              <div className="flex-shrink-0 pt-0.5">
                <span className={`text-xs px-1.5 py-0.5 rounded font-mono
                  ${SPEAKER_COLORS[seg.speaker] || 'bg-gray-100 text-gray-600'}`}>
                  {seg.speaker?.replace('SPEAKER_','S') || '?'}
                </span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs text-gray-400 font-mono">
                    {formatTime(seg.start_time || 0)}
                  </span>
                </div>
                <p className="text-sm text-gray-800 leading-relaxed">{seg.text}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Analysis Panel — 40% */}
        <div className="col-span-2 space-y-4">
          {/* Score */}
          {an.qualification_score != null && (
            <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
              <div className="text-4xl font-bold text-gray-900 mb-1">
                {an.qualification_score}
              </div>
              <div className="text-sm text-gray-500">Qualification Score</div>
              <div className={`mt-2 inline-block px-3 py-1 rounded-full text-sm font-medium ${
                an.qualification_category === 'hot' ? 'bg-red-100 text-red-700' :
                an.qualification_category === 'warm' ? 'bg-orange-100 text-orange-700' :
                an.qualification_category === 'cold' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {an.qualification_category || 'unknown'}
              </div>
            </div>
          )}

          {/* Signals */}
          {(an.intent || an.urgency) && (
            <div className="bg-white rounded-xl border p-4 shadow-sm space-y-2">
              {an.intent && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Intent</span>
                  <span className="text-sm font-medium text-gray-800 capitalize">
                    {an.intent.replace(/_/g,' ')}
                  </span>
                </div>
              )}
              {an.urgency && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Urgency</span>
                  <span className={`text-sm font-medium capitalize ${
                    an.urgency === 'high' ? 'text-red-600' :
                    an.urgency === 'medium' ? 'text-orange-600' : 'text-blue-600'
                  }`}>{an.urgency}</span>
                </div>
              )}
            </div>
          )}

          {/* Summary */}
          {an.summary && (
            <div className="bg-white rounded-xl border p-4 shadow-sm">
              <div className="text-xs font-medium text-gray-400 uppercase mb-2">Summary</div>
              <p className="text-sm text-gray-700 leading-relaxed">{an.summary}</p>
            </div>
          )}

          {/* Objections */}
          {an.objections?.length > 0 && (
            <div className="bg-white rounded-xl border p-4 shadow-sm">
              <div className="text-xs font-medium text-gray-400 uppercase mb-2">Objections</div>
              <div className="flex flex-wrap gap-2">
                {an.objections.map((o: string, i: number) => (
                  <span key={i} className="bg-red-50 text-red-700 text-xs px-2 py-1 rounded-full border border-red-200">
                    {o}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Buying Signals */}
          {an.buying_signals?.length > 0 && (
            <div className="bg-white rounded-xl border p-4 shadow-sm">
              <div className="text-xs font-medium text-gray-400 uppercase mb-2">Buying Signals</div>
              <div className="flex flex-wrap gap-2">
                {an.buying_signals.map((s: string, i: number) => (
                  <span key={i} className="bg-green-50 text-green-700 text-xs px-2 py-1 rounded-full border border-green-200">
                    ✓ {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Next Action */}
          {an.next_action && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
              <div className="text-xs font-medium text-indigo-400 uppercase mb-1">Recommended Next Action</div>
              <p className="text-sm text-indigo-800 font-medium">{an.next_action}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

#### `apps/web/src/app/dashboard/calls/leads/[id]/page.tsx` — Lead Profile

```typescript
'use client'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Phone, Mail, Building2, Calendar } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json'
})

const CAT_COLOR: Record<string,string> = {
  hot:   'bg-red-100 text-red-700', warm: 'bg-orange-100 text-orange-700',
  cold:  'bg-blue-100 text-blue-700', nurture: 'bg-gray-100 text-gray-600',
  disqualified: 'bg-gray-50 text-gray-400',
}
const EVENT_ICON: Record<string,string> = {
  call_made:'📞', call_received:'📞', email_sent:'📧', email_received:'📧',
  status_changed:'🔄', note_added:'📝', score_updated:'📊', manual_update:'✏️',
  email_sequence_started:'🚀'
}

export default function LeadProfile() {
  const { id } = useParams()
  const [lead, setLead]     = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [note, setNote]     = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => { if (id) load() }, [id])

  async function load() {
    setLoading(true)
    const r = await fetch(`${API}/api/v1/calls/leads/${id}`, { headers: hdrs() })
    if (r.ok) {
      const d = await r.json()
      setLead(d.lead)
      setStatus(d.lead?.status || 'new')
    }
    setLoading(false)
  }

  async function updateStatus(newStatus: string) {
    setStatus(newStatus)
    await fetch(`${API}/api/v1/calls/leads/${id}`, {
      method: 'PUT', headers: hdrs(),
      body: JSON.stringify({ status: newStatus })
    })
    load()
  }

  async function addNote() {
    if (!note.trim()) return
    setUpdating(true)
    await fetch(`${API}/api/v1/calls/leads/${id}`, {
      method: 'PUT', headers: hdrs(),
      body: JSON.stringify({ notes: note })
    })
    setNote('')
    setUpdating(false)
    load()
  }

  if (loading) return (
    <div className="p-6 space-y-4">
      <div className="h-32 bg-gray-200 rounded-xl animate-pulse" />
      <div className="grid grid-cols-2 gap-4">
        <div className="h-64 bg-gray-200 rounded-xl animate-pulse" />
        <div className="h-64 bg-gray-200 rounded-xl animate-pulse" />
      </div>
    </div>
  )

  if (!lead) return (
    <div className="p-6 text-center text-gray-500">
      <p>Lead not found.</p>
      <Link href="/dashboard/calls" className="text-indigo-600 hover:underline mt-2 block">
        Back to Call Hub
      </Link>
    </div>
  )

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back */}
      <Link href="/dashboard/calls" className="flex items-center gap-2 text-gray-400 hover:text-gray-700 text-sm">
        <ArrowLeft className="w-4 h-4" /> Back to Call Hub
      </Link>

      {/* Lead Header */}
      <div className="bg-white rounded-xl border p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center
              text-indigo-700 font-bold text-2xl">
              {(lead.full_name || 'U').charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{lead.full_name}</h1>
              <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                {lead.company_name && <span className="flex items-center gap-1"><Building2 className="w-3 h-3" />{lead.company_name}</span>}
                {lead.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{lead.email}</span>}
                {lead.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-3xl font-bold text-gray-900">{lead.qualification_score || 0}</div>
              <div className="text-xs text-gray-400">score</div>
            </div>
            {lead.category && (
              <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${CAT_COLOR[lead.category] || 'bg-gray-100 text-gray-600'}`}>
                {lead.category}
              </span>
            )}
          </div>
        </div>

        {/* Status + Update */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t">
          <label className="text-sm text-gray-500">Status:</label>
          <select value={status} onChange={e => updateStatus(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:ring-2 focus:ring-indigo-300">
            {['new','contacted','qualified','warm','hot','cold','nurture','disqualified'].map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: AI Assessment + Calls */}
        <div className="space-y-4">
          {/* AI Summary */}
          {lead.ai_summary && (
            <div className="bg-white rounded-xl border p-4 shadow-sm">
              <div className="text-xs font-medium text-gray-400 uppercase mb-2">AI Assessment</div>
              <p className="text-sm text-gray-700 leading-relaxed">{lead.ai_summary}</p>
              {lead.ai_next_action && (
                <div className="mt-3 bg-indigo-50 rounded-lg p-3">
                  <div className="text-xs text-indigo-500 mb-1">Recommended Action</div>
                  <div className="text-sm text-indigo-800 font-medium">{lead.ai_next_action}</div>
                </div>
              )}
            </div>
          )}

          {/* Call Stats */}
          {lead.call_stats && (
            <div className="bg-white rounded-xl border p-4 shadow-sm">
              <div className="text-xs font-medium text-gray-400 uppercase mb-3">Call Stats</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center bg-gray-50 rounded-lg p-3">
                  <div className="text-xl font-bold text-gray-800">{Number(lead.call_stats.cnt || 0)}</div>
                  <div className="text-xs text-gray-500">Total Calls</div>
                </div>
                <div className="text-center bg-gray-50 rounded-lg p-3">
                  <div className="text-xl font-bold text-gray-800">
                    {lead.call_stats.avg_dur ? `${Math.floor(Number(lead.call_stats.avg_dur)/60)}m` : '—'}
                  </div>
                  <div className="text-xs text-gray-500">Avg Duration</div>
                </div>
              </div>
            </div>
          )}

          {/* Add Note */}
          <div className="bg-white rounded-xl border p-4 shadow-sm">
            <div className="text-xs font-medium text-gray-400 uppercase mb-2">Add Note</div>
            <textarea value={note} onChange={e => setNote(e.target.value)}
              rows={3} placeholder="Type a note..."
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-indigo-300" />
            <button onClick={addNote} disabled={updating || !note.trim()}
              className="mt-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700
                disabled:opacity-50 transition">
              {updating ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </div>

        {/* Right: Timeline */}
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs font-medium text-gray-400 uppercase mb-3">Timeline</div>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {(lead.timeline || []).length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">No events yet</p>
            ) : (lead.timeline || []).map((ev: any, i: number) => (
              <div key={i} className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-base">
                  {EVENT_ICON[ev.event_type] || '•'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800">{ev.title}</div>
                  {ev.description && (
                    <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{ev.description}</div>
                  )}
                  <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(ev.created_at).toLocaleDateString('tr-TR', {
                      day:'numeric', month:'short', hour:'2-digit', minute:'2-digit'
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
```

#### `apps/web/src/app/dashboard/finance/page.tsx` — Finance Dashboard

```typescript
'use client'
import { useState, useEffect, useRef } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Upload, AlertCircle, CheckCircle } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json'
})

export default function FinanceDashboard() {
  const [dash, setDash]       = useState<any>(null)
  const [invoices, setInv]    = useState<any[]>([])
  const [months, setMonths]   = useState(3)
  const [uploading, setUpl]   = useState(false)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { load() }, [months])

  async function load() {
    setLoading(true)
    const [dr, ir] = await Promise.all([
      fetch(`${API}/api/v1/finance/dashboard?months=${months}`, { headers: hdrs() }),
      fetch(`${API}/api/v1/finance/invoices`, { headers: hdrs() }),
    ])
    if (dr.ok) setDash(await dr.json())
    if (ir.ok) setInv((await ir.json()).invoices || [])
    setLoading(false)
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUpl(true)
    const fd = new FormData()
    fd.append('file', file)
    await fetch(`${API}/api/v1/finance/invoices/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
      body: fd
    })
    setTimeout(() => { load(); setUpl(false) }, 4000)
    if (fileRef.current) fileRef.current.value = ''
  }

  const fmt = (n: number, curr = 'TRY') =>
    `${n.toLocaleString('tr-TR', {maximumFractionDigits:0})} ${curr}`

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Finance Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered invoice analysis and P&L overview</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={months} onChange={e => setMonths(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm text-gray-700">
            <option value={1}>Last month</option>
            <option value={3}>Last 3 months</option>
            <option value={6}>Last 6 months</option>
            <option value={12}>Last 12 months</option>
          </select>
          <label className={`flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg
            text-sm font-medium cursor-pointer hover:bg-indigo-700 transition ${uploading ? 'opacity-60 pointer-events-none' : ''}`}>
            <Upload className="w-4 h-4" />
            {uploading ? 'Processing...' : 'Upload Invoice'}
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png"
                   onChange={handleUpload} className="hidden" />
          </label>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-yellow-600 flex-shrink-0" />
        <p className="text-yellow-800 text-sm">
          Figures are AI estimates. Consult your accountant before tax filing.
        </p>
      </div>

      {/* P&L Cards */}
      {dash && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border p-5 shadow-sm">
              <div className="flex items-center gap-2 text-green-600 text-sm mb-2">
                <TrendingUp className="w-4 h-4" /> Income
              </div>
              <div className="text-2xl font-bold text-gray-900">{fmt(dash.income.total)}</div>
              <div className="text-sm text-gray-500 mt-1">
                {dash.income.invoice_count} invoices ·
                KDV collected: {fmt(dash.income.vat_collected)}
              </div>
            </div>
            <div className="bg-white rounded-xl border p-5 shadow-sm">
              <div className="flex items-center gap-2 text-red-500 text-sm mb-2">
                <TrendingDown className="w-4 h-4" /> Expenses
              </div>
              <div className="text-2xl font-bold text-gray-900">{fmt(dash.expenses.total)}</div>
              <div className="text-sm text-gray-500 mt-1">
                {dash.expenses.invoice_count} invoices ·
                KDV offset: {fmt(dash.expenses.vat_paid)}
              </div>
            </div>
            <div className={`rounded-xl border p-5 shadow-sm ${
              dash.profit_loss.gross >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-2 text-gray-600 text-sm mb-2">
                <DollarSign className="w-4 h-4" /> Net Profit/Loss
              </div>
              <div className={`text-2xl font-bold ${
                dash.profit_loss.gross >= 0 ? 'text-green-700' : 'text-red-700'
              }`}>
                {dash.profit_loss.gross >= 0 ? '+' : ''}{fmt(dash.profit_loss.gross)}
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Est. net KDV payable: {fmt(dash.profit_loss.estimated_net_vat_payable)}
              </div>
            </div>
          </div>

          {/* Category Breakdown */}
          {dash.categories?.length > 0 && (
            <div className="bg-white rounded-xl border p-5 shadow-sm">
              <h3 className="font-semibold text-gray-800 mb-4">By Category</h3>
              <div className="space-y-2">
                {dash.categories.slice(0,10).map((cat: any, i: number) => (
                  <div key={i} className="flex items-center justify-between py-1">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        cat.direction === 'outgoing' ? 'bg-green-500' : 'bg-red-400'
                      }`} />
                      <span className="text-sm text-gray-700 capitalize">{cat.category}</span>
                      <span className="text-xs text-gray-400">({cat.cnt} invoices)</span>
                    </div>
                    <span className={`text-sm font-medium ${
                      cat.direction === 'outgoing' ? 'text-green-700' : 'text-red-600'
                    }`}>
                      {cat.direction === 'outgoing' ? '+' : '−'}{fmt(Number(cat.total))}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Invoice List */}
      <div className="bg-white rounded-xl border shadow-sm">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Recent Invoices ({invoices.length})</h3>
        </div>
        <div className="divide-y max-h-96 overflow-y-auto">
          {invoices.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <Upload className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p>Upload your first invoice to get started</p>
            </div>
          ) : invoices.map((inv: any) => (
            <div key={inv.id} className="p-4 hover:bg-gray-50 cursor-pointer flex items-center justify-between"
                 onClick={() => setSelected(selected?.id === inv.id ? null : inv)}>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-800 truncate">
                  {inv.vendor_name || inv.file_name || 'Unknown vendor'}
                </div>
                <div className="text-sm text-gray-500">
                  {inv.invoice_date || '—'} ·
                  <span className="capitalize"> {inv.category}</span> ·
                  <span className={`ml-1 font-medium ${
                    inv.direction === 'outgoing' ? 'text-green-600' : 'text-red-500'
                  }`}>
                    {inv.direction === 'outgoing' ? 'income' : 'expense'}
                  </span>
                </div>
              </div>
              <div className="text-right ml-4 flex-shrink-0">
                <div className={`font-bold ${inv.direction === 'outgoing' ? 'text-green-700' : 'text-gray-800'}`}>
                  {fmt(Number(inv.total_amount || 0), inv.currency || 'TRY')}
                </div>
                <div className="flex items-center justify-end gap-1 mt-0.5">
                  {inv.extraction_status === 'completed'
                    ? <CheckCircle className="w-3 h-3 text-green-500" />
                    : <AlertCircle className="w-3 h-3 text-yellow-500" />}
                  <span className="text-xs text-gray-400">{inv.extraction_status}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Invoice Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
             onClick={e => e.target === e.currentTarget && setSelected(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">{selected.vendor_name || selected.file_name}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Invoice #', selected.invoice_number],
                ['Date', selected.invoice_date],
                ['Currency', selected.currency],
                ['Subtotal', fmt(Number(selected.subtotal||0), selected.currency)],
                ['VAT', fmt(Number(selected.vat_amount||0), selected.currency)],
                ['Total', fmt(Number(selected.total_amount||0), selected.currency)],
                ['VAT Rate', `${selected.vat_rate}%`],
                ['Deductible', selected.is_deductible ? 'Yes' : 'No'],
              ].filter(([,v]) => v).map(([k,v]) => (
                <div key={k as string} className="bg-gray-50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">{k}</div>
                  <div className="font-medium text-gray-800">{v}</div>
                </div>
              ))}
            </div>
            {selected.ai_notes && (
              <div className="bg-blue-50 rounded-xl p-4">
                <div className="text-xs font-medium text-blue-400 uppercase mb-2">AI Analysis</div>
                <p className="text-sm text-blue-900 whitespace-pre-line">{selected.ai_notes}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

#### `apps/web/src/app/dashboard/ai-learning/page.tsx` — AI Learning

```typescript
'use client'
import { useState, useEffect } from 'react'
import { Brain, CheckCircle, XCircle, TrendingUp, Database } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json'
})

export default function AILearning() {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    const r = await fetch(`${API}/api/v1/ai-learning/summary`, { headers: hdrs() })
    if (r.ok) setSummary(await r.json())
    setLoading(false)
  }

  // Group feedback by module
  const byModule: Record<string, {accepted:number,rejected:number,total:number}> = {}
  if (summary?.feedback_by_module) {
    for (const row of summary.feedback_by_module) {
      if (!byModule[row.module]) byModule[row.module] = {accepted:0,rejected:0,total:0}
      byModule[row.module].total += Number(row.cnt)
      if (row.feedback_type === 'accepted') byModule[row.module].accepted += Number(row.cnt)
      if (row.feedback_type === 'rejected') byModule[row.module].rejected += Number(row.cnt)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Learning System</h1>
          <p className="text-sm text-gray-500 mt-1">Platform learns from your feedback to improve recommendations</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          summary?.status === 'active'
            ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
        }`}>
          {summary?.status === 'active' ? '● Active Learning' : '○ Gathering Data'}
        </span>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label:'Total Feedback', val: summary?.total_feedback || 0, icon: Brain, color:'text-indigo-600' },
          { label:'Learned Preferences', val: summary?.learned_preferences || 0, icon: Database, color:'text-blue-600' },
          { label:'Modules Tracked', val: Object.keys(byModule).length, icon: TrendingUp, color:'text-green-600' },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-xl border p-4 shadow-sm">
            <div className={`flex items-center gap-2 text-sm mb-1 ${k.color}`}>
              <k.icon className="w-4 h-4" /> {k.label}
            </div>
            <div className="text-2xl font-bold text-gray-900">{k.val}</div>
          </div>
        ))}
      </div>

      {/* Module Breakdown */}
      {Object.keys(byModule).length > 0 && (
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="p-4 border-b">
            <h3 className="font-semibold text-gray-800">Learning by Module</h3>
          </div>
          <div className="divide-y">
            {Object.entries(byModule).map(([mod, stats]) => {
              const rate = stats.total > 0 ? Math.round(stats.accepted/stats.total*100) : 0
              return (
                <div key={mod} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 capitalize">
                      {mod.replace(/_/g,' ')}
                    </span>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle className="w-3.5 h-3.5" /> {stats.accepted}
                      </span>
                      <span className="flex items-center gap-1 text-red-500">
                        <XCircle className="w-3.5 h-3.5" /> {stats.rejected}
                      </span>
                      <span className="text-gray-500">{rate}% accepted</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-indigo-500 h-2 rounded-full transition-all"
                         style={{width:`${rate}%`}} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* How it works */}
      <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-5">
        <h3 className="font-semibold text-indigo-800 mb-3">How AI Learning Works</h3>
        <div className="space-y-2 text-sm text-indigo-700">
          {[
            'When you accept or reject a recommendation, the AI records your preference.',
            'Over time, the system learns your thresholds — e.g., you prefer higher-confidence recommendations.',
            'Call analysis improves as the AI learns which signals predict your best leads.',
            'All learning is local to your workspace. Nothing is shared externally.',
          ].map((line, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-indigo-400 mt-0.5">→</span>
              <span>{line}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

## STEP 9: VERIFY AND FIX SIDEBAR

```bash
grep -rn "CALLING\|FINANCE\|AI SYSTEM\|Call Hub\|Lead Inbox\|ai-learning\|/dashboard/calls\|/dashboard/finance" \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src" \
  --include="*.tsx" | grep -v "node_modules" | head -20
```

Find the main sidebar/layout component (usually `layout.tsx` or a `Sidebar.tsx` or `navigation.tsx`):

```bash
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src" \
  -name "*.tsx" -not -path "*/node_modules/*" \
  | xargs grep -l "href.*dashboard\|navigation\|sidebar" 2>/dev/null | head -5
```

Open that file and add these nav items in the appropriate section.
Follow the EXACT pattern already used for existing nav items.
If items use an array of objects, add to the array.
If they're hardcoded JSX Links, add Link elements.

```typescript
// Add to imports:
import { Phone, Users, BarChart3, Brain, Upload } from 'lucide-react'

// CALLING ENGINE section items:
{ label: 'Call Hub',    href: '/dashboard/calls',           icon: Phone  }
{ label: 'Lead Inbox',  href: '/dashboard/calls?tab=leads', icon: Users  }

// FINANCE section items:
{ label: 'P&L Dashboard', href: '/dashboard/finance', icon: BarChart3 }

// AI SYSTEM section items:
{ label: 'AI Learning', href: '/dashboard/ai-learning', icon: Brain }
```

---

## STEP 10: FINAL END-TO-END TEST

```bash
# Restart backend clean
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 3
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
uvicorn app.main:app --reload --port 8000 > /tmp/final_test.log 2>&1 &
sleep 12

# Check for import errors
echo "=== STARTUP ERRORS ==="
grep -E "ERROR|Import|ModuleNotFound" /tmp/final_test.log | head -10

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',d.get('detail','FAILED')))")
echo "Auth: ${TOKEN:0:40}..."

# All endpoints
echo ""
echo "=== FULL ENDPOINT TEST ==="
PASS=0; FAIL=0
for ep in \
  "GET /health" \
  "GET /api/v1/calls" \
  "GET /api/v1/calls/contacts" \
  "GET /api/v1/calls/leads" \
  "GET /api/v1/finance/invoices" \
  "GET /api/v1/finance/dashboard?months=3" \
  "GET /api/v1/email/sync-lead/00000000-0000-0000-0000-000000000000" \
  "GET /api/v1/ai-learning/summary" \
  "GET /api/v1/ads/accounts" \
  "GET /api/v1/ads/campaigns" \
  "GET /api/v1/ads/recommendations" \
  "GET /api/v1/ads/portfolio/summary"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  status=$(curl -s -o /tmp/r.json -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN")
  # 200, 201, 404 (not found ID) are OK. 500, 422, 000 are failures
  if [[ "$status" == "200" ]] || [[ "$status" == "201" ]] || [[ "$status" == "404" ]]; then
    echo "✅ $status  $ep"
    PASS=$((PASS+1))
  else
    echo "❌ $status  $ep"
    python3 -c "import json,sys; d=json.load(open('/tmp/r.json')); print('  →',str(d)[:120])" 2>/dev/null
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "═══════════════════════════════"
echo "Passed: $PASS | Failed: $FAIL"
echo "═══════════════════════════════"

# Frontend build
echo ""
echo "=== FRONTEND BUILD ==="
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npx next build 2>&1 | grep -E "error TS|Error:|✓ Compiled|Route|✓ Generating" | tail -20

# Final file check
echo ""
echo "=== FINAL FILE CHECK ==="
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"
MISSING=0
for f in \
  "apps/api/app/services/ai/model_config.py" \
  "apps/api/app/services/ai/memory_service.py" \
  "apps/api/app/services/shared/data_bridge.py" \
  "apps/api/app/services/calling/call_engine.py" \
  "apps/api/app/services/calling/transcription_engine.py" \
  "apps/api/app/services/calling/lead_qualifier.py" \
  "apps/api/app/services/finance/invoice_intelligence.py" \
  "apps/api/app/services/email/mautic_bridge.py" \
  "apps/api/app/api/endpoints/calling.py" \
  "apps/api/app/api/endpoints/finance.py" \
  "apps/api/app/api/endpoints/email_bridge.py" \
  "apps/api/app/api/endpoints/ai_learning.py" \
  "apps/web/src/app/dashboard/calls/page.tsx" \
  "apps/web/src/app/dashboard/calls/[id]/page.tsx" \
  "apps/web/src/app/dashboard/calls/leads/[id]/page.tsx" \
  "apps/web/src/app/dashboard/finance/page.tsx" \
  "apps/web/src/app/dashboard/ai-learning/page.tsx"; do
  if [ -f "$BASE/$f" ]; then
    echo "✅ $f"
  else
    echo "❌ MISSING: $f"
    MISSING=$((MISSING+1))
  fi
done

echo ""
if [ $MISSING -eq 0 ] && [ $FAIL -eq 0 ]; then
  echo "╔══════════════════════════════════════════╗"
  echo "║  ✅ ALL CHECKS PASSED — SYSTEM IS READY  ║"
  echo "╚══════════════════════════════════════════╝"
else
  echo "═══════════════════════════════════════════"
  echo "❌ $MISSING missing files, $FAIL failed endpoints"
  echo "Fix all issues above before declaring done."
  echo "═══════════════════════════════════════════"
fi
```

---

## DO NOT STOP UNTIL OUTPUT SHOWS:
```
✅ ALL CHECKS PASSED — SYSTEM IS READY
```

Fix every ❌ you find. Re-run verification after each fix batch.
