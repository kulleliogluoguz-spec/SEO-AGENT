# MISSION PHASE 2 — AI Growth OS Full Transformation
## Complete Implementation Spec — All 7 Modules
**Place this file at:** `apps/api/MISSION_PHASE2.md`
**Platform:** `/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/`
**Stack:** FastAPI (8000) + Next.js 14 (3001) + PostgreSQL + Ollama (11434)

---

## CRITICAL RULES
- Never break existing functionality
- All AI = local Ollama only. Zero external AI API calls.
- Every action that modifies live data needs human approval
- Call recording requires consent notice (KVKK compliance)
- Tax/invoice outputs must carry "consult your accountant" disclaimer
- Follow existing code patterns: AsyncSession, JWT auth, Tailwind

---

## PHASE 0: AUDIT FIRST

```bash
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app" -name "*.py" | head -80
cat "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/main.py"
cat "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/core/config/settings.py"
cat "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env"
ls "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/api/endpoints/"
ls "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services/"
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web/src" -name "layout.tsx" | head -5
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]"
python3 -c "
import asyncio, asyncpg, os
async def main():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    [print(r['tablename']) for r in rows]
    await conn.close()
asyncio.run(main())
"
```

---

## MODULE B: LOCAL AI UPGRADE (DO FIRST)

### B1: Pull new models

```bash
python3 -c "import psutil; print(f'RAM: {psutil.virtual_memory().total/1e9:.1f}GB available: {psutil.virtual_memory().available/1e9:.1f}GB')"

# Primary: Gemma 4 27B (Google, Apache 2.0, April 2026, 85 tok/s consumer hw)
ollama pull gemma4:27b

# Reasoning tasks
ollama pull deepseek-r1:8b

# Multilingual (Turkish calls, emails)
ollama pull qwen3:14b

# Verify
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma4:27b","prompt":"ROAS 3.2x declining trend. One sentence insight.","stream":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

### B2: Create model config service

**File:** `apps/api/app/services/ai/model_config.py`

```python
"""
AI Model Configuration — Local Model Stack
All inference local via Ollama. Zero external API calls.
"""
import logging
import requests
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
        TaskType.FAST:         ["qwen3:8b", "gemma4:2b"],
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
            for a in avail:
                if candidate.split(":")[0] in a:
                    return a
        return "qwen3:8b"


def call_ollama(
    prompt: str,
    task: TaskType = TaskType.STANDARD,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
    system: Optional[str] = None,
    timeout: int = 120
) -> str:
    """Universal Ollama call with model selection and error handling."""
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
        return f"[AI timeout — model loading. Retry in 30s.]"
    except requests.exceptions.ConnectionError:
        return "[AI unavailable — run: ollama serve]"
    except Exception as e:
        return f"[AI error: {str(e)[:100]}]"


def call_ollama_json(
    prompt: str,
    schema_example: dict,
    task: TaskType = TaskType.STANDARD,
    model: Optional[str] = None,
    timeout: int = 120
) -> dict:
    """Call Ollama expecting JSON output."""
    import json, re
    json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No explanation, no markdown, no backticks.
Example format: {str(schema_example)}"""
    response = call_ollama(json_prompt, task=task, model=model, max_tokens=1000,
                           temperature=0.1, timeout=timeout)
    response = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        logger.error(f"JSON parse failed: {response[:200]}")
        return {}
```

### B3: Update existing Ollama calls

```bash
grep -rn "localhost:11434\|qwen3:8b" \
  "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/app/services" \
  --include="*.py" -l
```

For each file found, replace direct `requests.post(...)` calls with:
```python
from app.services.ai.model_config import call_ollama, call_ollama_json, TaskType
result = call_ollama(prompt, task=TaskType.STANDARD)
```

---

## MODULE G: CROSS-MODULE DATA BRIDGE (DO SECOND)

### G1: Create shared database tables

**File:** `apps/api/scripts/create_shared_tables.py`

```python
import asyncio, asyncpg, os

async def create_tables():
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
            source VARCHAR(100),
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
            confidence NUMERIC(5,4),
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
            direction VARCHAR(20),
            status VARCHAR(50) DEFAULT 'pending',
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            duration_seconds INTEGER,
            recording_path VARCHAR(1000),
            recording_size_mb NUMERIC(10,2),
            transcription_status VARCHAR(50) DEFAULT 'pending',
            analysis_status VARCHAR(50) DEFAULT 'pending',
            provider VARCHAR(50),
            provider_call_id VARCHAR(255),
            consent_given BOOLEAN DEFAULT FALSE,
            consent_timestamp TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS call_transcripts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            call_id UUID REFERENCES calls(id) NOT NULL,
            speaker VARCHAR(50),
            speaker_label VARCHAR(100),
            text TEXT NOT NULL,
            start_time NUMERIC(10,3),
            end_time NUMERIC(10,3),
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
            qualification_score INTEGER,
            qualification_category VARCHAR(50),
            summary TEXT,
            key_points TEXT[],
            next_action TEXT,
            follow_up_days INTEGER,
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
            direction VARCHAR(20),
            category VARCHAR(100),
            tax_category VARCHAR(100),
            is_deductible BOOLEAN,
            vat_rate NUMERIC(5,2),
            vat_amount NUMERIC(14,2),
            estimated_tax_impact TEXT,
            extraction_status VARCHAR(50) DEFAULT 'pending',
            confidence_score NUMERIC(5,4),
            needs_human_review BOOLEAN DEFAULT FALSE,
            human_reviewed BOOLEAN DEFAULT FALSE,
            ai_notes TEXT,
            line_items JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_contacts_workspace ON contacts(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_leads_contact ON leads(contact_id);
        CREATE INDEX IF NOT EXISTS idx_leads_workspace_status ON leads(workspace_id, status);
        CREATE INDEX IF NOT EXISTS idx_calls_contact ON calls(contact_id);
        CREATE INDEX IF NOT EXISTS idx_calls_workspace ON calls(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_transcripts_call ON call_transcripts(call_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_workspace ON invoices(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
        CREATE INDEX IF NOT EXISTS idx_ai_memory_workspace ON ai_memory(workspace_id, module);
        CREATE INDEX IF NOT EXISTS idx_timeline_lead ON lead_timeline(lead_id);
    """)
    print("✅ All shared tables created")
    await conn.close()

asyncio.run(create_tables())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/create_shared_tables.py
```

### G2: Data bridge service

**File:** `apps/api/app/services/shared/data_bridge.py`

```python
"""
Cross-Module Data Bridge — shared contact/lead data across all modules.
"""
import logging, json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataBridge:
    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    async def get_or_create_contact(self, email=None, phone=None,
                                     full_name=None, company_name=None,
                                     source="manual") -> dict:
        for field, val in [("email", email), ("phone", phone)]:
            if val:
                r = await self.db.execute(
                    text(f"SELECT * FROM contacts WHERE workspace_id=:wid AND {field}=:val LIMIT 1"),
                    {"wid": self.workspace_id, "val": val}
                )
                row = r.fetchone()
                if row:
                    return dict(row._mapping)
        r = await self.db.execute(
            text("""INSERT INTO contacts(workspace_id,full_name,company_name,email,phone,source)
                    VALUES(:wid,:name,:co,:email,:phone,:src) RETURNING *"""),
            {"wid": self.workspace_id, "name": full_name, "co": company_name,
             "email": email, "phone": phone, "src": source}
        )
        await self.db.commit()
        return dict(r.fetchone()._mapping)

    async def get_or_create_lead(self, contact_id: str) -> dict:
        r = await self.db.execute(
            text("SELECT * FROM leads WHERE contact_id=:cid AND workspace_id=:wid LIMIT 1"),
            {"cid": contact_id, "wid": self.workspace_id}
        )
        row = r.fetchone()
        if row:
            return dict(row._mapping)
        r = await self.db.execute(
            text("""INSERT INTO leads(contact_id,workspace_id,status,qualification_score)
                    VALUES(:cid,:wid,'new',0) RETURNING *"""),
            {"cid": contact_id, "wid": self.workspace_id}
        )
        await self.db.commit()
        return dict(r.fetchone()._mapping)

    async def add_timeline_event(self, lead_id: str, event_type: str,
                                  title: str, description=None, metadata=None):
        await self.db.execute(
            text("""INSERT INTO lead_timeline(lead_id,event_type,title,description,metadata)
                    VALUES(:lid,:et,:title,:desc,:meta::jsonb)"""),
            {"lid": lead_id, "et": event_type, "title": title,
             "desc": description, "meta": json.dumps(metadata or {})}
        )
        await self.db.commit()

    async def update_lead_from_call(self, lead_id: str, analysis: dict):
        await self.db.execute(
            text("""UPDATE leads SET
                    qualification_score=GREATEST(qualification_score,COALESCE(:score,qualification_score)),
                    category=COALESCE(:cat,category), ai_summary=:summary,
                    ai_intent=:intent, ai_urgency=:urgency, ai_next_action=:next,
                    last_contact_date=NOW(), call_count=call_count+1, updated_at=NOW()
                    WHERE id=:lid"""),
            {"lid": lead_id, "score": analysis.get("qualification_score"),
             "cat": analysis.get("qualification_category"),
             "summary": analysis.get("summary"), "intent": analysis.get("intent"),
             "urgency": analysis.get("urgency"), "next": analysis.get("next_action")}
        )
        await self.db.commit()

    async def get_lead_full_profile(self, lead_id: str) -> dict:
        r = await self.db.execute(
            text("""SELECT l.*,c.full_name,c.company_name,c.email,c.phone,c.industry
                    FROM leads l JOIN contacts c ON c.id=l.contact_id WHERE l.id=:lid"""),
            {"lid": lead_id}
        )
        row = r.fetchone()
        if not row:
            return {}
        lead = dict(row._mapping)
        tl = await self.db.execute(
            text("SELECT * FROM lead_timeline WHERE lead_id=:lid ORDER BY created_at DESC LIMIT 20"),
            {"lid": lead_id}
        )
        lead["timeline"] = [dict(r._mapping) for r in tl.fetchall()]
        calls = await self.db.execute(
            text("""SELECT COUNT(*) as cnt,AVG(duration_seconds) as avg_dur,MAX(started_at) as last
                    FROM calls WHERE lead_id=:lid"""),
            {"lid": lead_id}
        )
        lead["call_stats"] = dict(calls.fetchone()._mapping)
        return lead
```

---

## MODULE A: CALLING ENGINE

### A1: Install dependencies

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install twilio==9.3.0 livekit-api==0.7.0
pip install faster-whisper==1.0.3 whisperx==3.1.6
pip install pyannote.audio==3.3.2
pip install ffmpeg-python==0.2.0 pydub==0.25.1 soundfile==0.12.1
pip install chromadb==0.5.23 sentence-transformers==3.3.1
pip freeze | grep -E "twilio|livekit|faster|whisperx|pyannote|ffmpeg|pydub|chromadb|sentence" >> requirements.txt

cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npm install @livekit/components-react @livekit/client livekit-client wavesurfer.js
```

Create storage dirs:
```bash
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/recordings"
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/invoices"
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/reports"
mkdir -p "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/chroma"
```

### A2: Call Engine Service

**File:** `apps/api/app/services/calling/call_engine.py`

```python
"""
Call Engine — manages call lifecycle across Twilio/LiveKit/Manual Upload.
"""
import logging, os, uuid, shutil, tempfile
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)
RECORDINGS_DIR = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class CallEngine:
    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    async def initiate_twilio_call(self, to_phone: str, from_phone: str,
                                    contact_id=None, lead_id=None, record=True) -> dict:
        from twilio.rest import Client as TwilioClient
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        webhook = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        if not sid or not token:
            return {"error": "Twilio credentials missing. Set TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN in .env"}
        client = TwilioClient(sid, token)
        call_id = str(uuid.uuid4())
        await self.db.execute(
            text("""INSERT INTO calls(id,workspace_id,contact_id,lead_id,direction,
                    status,provider,consent_given,consent_timestamp)
                    VALUES(:id,:wid,:cid,:lid,'outbound','active','twilio',true,NOW())"""),
            {"id": call_id, "wid": self.workspace_id, "cid": contact_id, "lid": lead_id}
        )
        await self.db.commit()
        try:
            call = client.calls.create(
                to=to_phone, from_=from_phone,
                url=f"{webhook}/api/v1/calls/twiml/{call_id}",
                record=record,
                recording_status_callback=f"{webhook}/api/v1/calls/recording-webhook/{call_id}",
                recording_status_callback_event=["completed"],
                status_callback=f"{webhook}/api/v1/calls/status-webhook/{call_id}",
            )
            await self.db.execute(
                text("UPDATE calls SET provider_call_id=:sid, started_at=NOW() WHERE id=:id"),
                {"sid": call.sid, "id": call_id}
            )
            await self.db.commit()
            return {"call_id": call_id, "provider_call_id": call.sid, "status": "initiated"}
        except Exception as e:
            await self.db.execute(
                text("UPDATE calls SET status='failed' WHERE id=:id"), {"id": call_id}
            )
            await self.db.commit()
            return {"error": str(e), "call_id": call_id}

    def get_twiml_response(self, call_id: str) -> str:
        # KVKK compliance: must announce recording
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Zeynep" language="tr-TR">
        Merhaba. Bu görüşme kayıt altına alınmaktadır.
    </Say>
    <Pause length="1"/>
    <Say voice="Polly.Zeynep" language="tr-TR">
        Sizi bağlıyorum, lütfen bekleyiniz.
    </Say>
    <Dial><Conference>{call_id}</Conference></Dial>
</Response>"""

    async def handle_recording_webhook(self, call_id: str,
                                        recording_url: str, duration: int):
        import requests as req_lib
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        dest = RECORDINGS_DIR / f"{call_id}.wav"
        try:
            r = req_lib.get(f"{recording_url}.wav", auth=(sid, token), stream=True)
            with open(dest, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            size_mb = dest.stat().st_size / 1e6
            await self.db.execute(
                text("""UPDATE calls SET recording_path=:path, recording_size_mb=:size,
                        duration_seconds=:dur, status='completed', ended_at=NOW() WHERE id=:id"""),
                {"path": str(dest), "size": size_mb, "dur": duration, "id": call_id}
            )
            await self.db.commit()
            import asyncio
            asyncio.create_task(self._process_async(call_id, str(dest)))
        except Exception as e:
            logger.error(f"Recording download failed for {call_id}: {e}")

    async def _process_async(self, call_id: str, recording_path: str):
        from app.services.calling.transcription_engine import TranscriptionEngine
        from app.services.calling.lead_qualifier import LeadQualifier
        segments = await TranscriptionEngine().transcribe_call(call_id, recording_path, self.db)
        if segments:
            await LeadQualifier().analyze_call(call_id, segments, self.db)

    async def upload_recording(self, call_id: str, file_path: str,
                                contact_id=None, lead_id=None) -> dict:
        dest = RECORDINGS_DIR / f"{call_id}.wav"
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", str(dest), "-y"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"error": f"Audio conversion failed: {result.stderr[:200]}"}
        size_mb = dest.stat().st_size / 1e6
        await self.db.execute(
            text("""INSERT INTO calls(id,workspace_id,contact_id,lead_id,direction,
                    status,recording_path,recording_size_mb,provider,consent_given)
                    VALUES(:id,:wid,:cid,:lid,'inbound','completed',:path,:size,'manual_upload',true)
                    ON CONFLICT(id) DO UPDATE SET recording_path=:path,recording_size_mb=:size"""),
            {"id": call_id, "wid": self.workspace_id, "cid": contact_id, "lid": lead_id,
             "path": str(dest), "size": size_mb}
        )
        await self.db.commit()
        return {"call_id": call_id, "recording_path": str(dest),
                "size_mb": size_mb, "status": "uploaded"}
```

### A3: Transcription Engine

**File:** `apps/api/app/services/calling/transcription_engine.py`

```python
"""
Transcription Engine — WhisperX + Pyannote speaker diarization.
"""
import logging, os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    def __init__(self, model_size="large-v3", device="auto", language=None):
        self.model_size = model_size
        self.language = language
        self.device = self._detect_device() if device == "auto" else device
        self._model = None
        self._diarizer = None

    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _load_model(self):
        if self._model is not None:
            return
        try:
            import whisperx
            ct = "float16" if self.device == "cuda" else "int8"
            self._model = whisperx.load_model(self.model_size, self.device,
                                               compute_type=ct, language=self.language)
            logger.info(f"WhisperX loaded: {self.model_size} on {self.device}")
        except ImportError:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
            self._model._is_fw = True

    def _load_diarizer(self):
        if self._diarizer is not None:
            return self._diarizer
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            logger.warning("HUGGINGFACE_TOKEN not set — speaker diarization disabled")
            return None
        try:
            from pyannote.audio import Pipeline
            import torch
            self._diarizer = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1", use_auth_token=hf_token
            )
            dev = torch.device("cpu" if self.device == "mps" else self.device)
            self._diarizer.to(dev)
        except Exception as e:
            logger.error(f"Diarization load failed: {e}")
        return self._diarizer

    async def transcribe_call(self, call_id: str, audio_path: str,
                               db: AsyncSession) -> list[dict]:
        await db.execute(
            text("UPDATE calls SET transcription_status='processing' WHERE id=:id"),
            {"id": call_id}
        )
        await db.commit()
        try:
            self._load_model()
            if hasattr(self._model, "_is_fw"):
                segments = self._fw_transcribe(audio_path)
            else:
                segments = self._wx_transcribe(audio_path)

            for seg in segments:
                await db.execute(
                    text("""INSERT INTO call_transcripts
                            (call_id,speaker,text,start_time,end_time,confidence)
                            VALUES(:cid,:spk,:txt,:start,:end,:conf)"""),
                    {"cid": call_id, "spk": seg.get("speaker","UNKNOWN"),
                     "txt": seg["text"].strip(), "start": seg["start"],
                     "end": seg["end"], "conf": seg.get("confidence")}
                )
            await db.commit()
            await db.execute(
                text("UPDATE calls SET transcription_status='completed' WHERE id=:id"),
                {"id": call_id}
            )
            await db.commit()
            logger.info(f"Transcribed {call_id}: {len(segments)} segments")
            return segments
        except Exception as e:
            logger.error(f"Transcription failed {call_id}: {e}")
            await db.execute(
                text("UPDATE calls SET transcription_status='failed' WHERE id=:id"),
                {"id": call_id}
            )
            await db.commit()
            return []

    def _wx_transcribe(self, audio_path: str) -> list[dict]:
        import whisperx
        audio = whisperx.load_audio(audio_path)
        result = self._model.transcribe(audio, batch_size=16)
        lang = result.get("language", self.language or "tr")
        try:
            model_a, meta = whisperx.load_align_model(language_code=lang, device=self.device)
            result = whisperx.align(result["segments"], model_a, meta, audio, self.device,
                                    return_char_alignments=False)
        except Exception as e:
            logger.warning(f"Alignment failed: {e}")
        diarizer = self._load_diarizer()
        if diarizer:
            try:
                dr = diarizer({"waveform": None, "sample_rate": 16000},
                               min_speakers=2, max_speakers=4)
                result = whisperx.assign_word_speakers(dr, result)
            except Exception as e:
                logger.warning(f"Diarization failed: {e}")
        return [{"speaker": s.get("speaker","SPEAKER_0"), "text": s["text"],
                 "start": s["start"], "end": s["end"]} for s in result.get("segments",[])]

    def _fw_transcribe(self, audio_path: str) -> list[dict]:
        segs, _ = self._model.transcribe(audio_path, language=self.language,
                                          beam_size=5, word_timestamps=True)
        return [{"speaker":"SPEAKER_0","text":s.text,"start":s.start,"end":s.end} for s in segs]
```

### A4: Lead Qualifier

**File:** `apps/api/app/services/calling/lead_qualifier.py`

```python
"""
Lead Qualification Engine — BANT scoring + AI analysis via local Ollama.
"""
import logging, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.ai.model_config import call_ollama_json, call_ollama, TaskType

logger = logging.getLogger(__name__)


class LeadQualifier:
    SYSTEM = """You are an expert B2B sales analyst.
Analyze call transcripts objectively. Only report what is present in the transcript.
Never fabricate information."""

    async def analyze_call(self, call_id: str, segments: list[dict],
                            db: AsyncSession) -> dict:
        t0 = time.time()
        transcript = "\n".join(
            f"{s.get('speaker','?')}: {s.get('text','').strip()}"
            for s in segments if s.get('text','').strip()
        )
        if len(transcript) < 50:
            return {}

        qual = self._extract_qualification(transcript)
        sent = self._extract_sentiment(transcript)
        summ = self._extract_summary(transcript)

        score = self._compute_score(qual, sent)
        ms = int((time.time() - t0) * 1000)

        analysis = {
            **qual, **sent, **summ,
            "qualification_score": score,
            "qualification_category": self._category(score),
            "processing_duration_ms": ms
        }

        await db.execute(
            text("""INSERT INTO call_analysis
                    (call_id,overall_sentiment,customer_sentiment,agent_sentiment,
                     intent,urgency,objections,buying_signals,action_items,
                     qualification_score,qualification_category,summary,key_points,
                     next_action,follow_up_days,ai_model_used,processing_duration_ms)
                    VALUES(:cid,:os,:cs,:as2,:intent,:urgency,:obj,:buy,:act,
                           :score,:cat,:summary,:kp,:next,:days,:model,:ms)
                    ON CONFLICT(call_id) DO UPDATE SET
                     qualification_score=:score,qualification_category=:cat,
                     summary=:summary,intent=:intent,urgency=:urgency,next_action=:next"""),
            {"cid": call_id,
             "os": analysis.get("overall_sentiment"),
             "cs": analysis.get("customer_sentiment"),
             "as2": analysis.get("agent_sentiment"),
             "intent": analysis.get("intent"),
             "urgency": analysis.get("urgency"),
             "obj": analysis.get("objections",[]),
             "buy": analysis.get("buying_signals",[]),
             "act": analysis.get("action_items",[]),
             "score": score,
             "cat": analysis.get("qualification_category"),
             "summary": analysis.get("summary"),
             "kp": analysis.get("key_points",[]),
             "next": analysis.get("next_action"),
             "days": analysis.get("follow_up_days",3),
             "model": "gemma4/qwen3",
             "ms": ms}
        )
        await db.execute(
            text("UPDATE calls SET analysis_status='completed' WHERE id=:id"),
            {"id": call_id}
        )
        await db.commit()
        return analysis

    def _extract_qualification(self, transcript: str) -> dict:
        schema = {
            "intent":"interested","urgency":"medium",
            "buying_signals":["asked about pricing"],
            "objections":["price concern"],
            "has_budget":True,"has_authority":False,
            "has_need":True,"has_timeline":False,
            "follow_up_days":3,
            "action_items":["send proposal"]
        }
        prompt = f"""Analyze this sales call and extract qualification signals.

TRANSCRIPT:
{transcript[:3000]}

intent: 'interested'|'not_interested'|'evaluating'|'follow_up_needed'
urgency: 'high'|'medium'|'low'
buying_signals: positive signals (max 5)
objections: concerns raised (max 5)
has_budget/has_authority/has_need/has_timeline: true/false
follow_up_days: 1-30
action_items: next steps (max 5)"""
        return call_ollama_json(prompt, schema, task=TaskType.MULTILINGUAL, timeout=90)

    def _extract_sentiment(self, transcript: str) -> dict:
        schema = {"overall_sentiment":"mixed_positive",
                  "customer_sentiment":"positive","agent_sentiment":"professional"}
        prompt = f"""Sentiment analysis for this call transcript.
TRANSCRIPT:
{transcript[:2000]}
overall_sentiment: 'positive'|'negative'|'neutral'|'mixed_positive'|'mixed_negative'
customer_sentiment: how the customer felt
agent_sentiment: how professional the agent was"""
        return call_ollama_json(prompt, schema, task=TaskType.FAST, timeout=60)

    def _extract_summary(self, transcript: str) -> dict:
        schema = {"summary":"Call summary","key_points":["point 1"],
                  "next_action":"Send proposal"}
        prompt = f"""Summarize this sales call.
TRANSCRIPT:
{transcript[:4000]}
summary: 2-3 sentence overview
key_points: 3-5 most important things discussed
next_action: single most important next step
Be concise. End with: factual, no fabrication."""
        return call_ollama_json(prompt, schema, task=TaskType.MULTILINGUAL, timeout=90)

    def _compute_score(self, qual: dict, sent: dict) -> int:
        score = 20
        if qual.get("has_budget"):    score += 20
        if qual.get("has_authority"): score += 20
        if qual.get("has_need"):      score += 20
        if qual.get("has_timeline"):  score += 10
        score += {"interested":10,"evaluating":5,"follow_up_needed":3,
                  "not_interested":-30}.get(qual.get("intent",""),0)
        if "positive" in (sent.get("customer_sentiment") or ""): score += 5
        elif "negative" in (sent.get("customer_sentiment") or ""): score -= 10
        score += min(len(qual.get("buying_signals",[])) * 3, 10)
        score -= min(len(qual.get("objections",[])) * 2, 10)
        return max(0, min(100, score))

    def _category(self, score: int) -> str:
        if score >= 75: return "hot"
        if score >= 55: return "warm"
        if score >= 35: return "cold"
        if score >= 15: return "nurture"
        return "disqualified"
```

### A5: Calling API Endpoints

**File:** `apps/api/app/api/endpoints/calling.py`

```python
"""Calling Module — FastAPI endpoints."""
import os, uuid, shutil, tempfile
from pathlib import Path
from typing import Optional
from fastapi import (APIRouter, Depends, HTTPException, BackgroundTasks,
                     UploadFile, File, Response)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.calling.call_engine import CallEngine
from app.services.calling.transcription_engine import TranscriptionEngine
from app.services.calling.lead_qualifier import LeadQualifier
from app.services.shared.data_bridge import DataBridge

router = APIRouter(prefix="/api/v1/calls", tags=["Calling"])
logger = logging.getLogger(__name__)

# ─── CONTACTS ─────────────────────────────────────────────────────

@router.get("/contacts")
async def list_contacts(search: Optional[str] = None,
                        current_user=Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    where = "WHERE c.workspace_id=:wid"
    params = {"wid": str(current_user.workspace_id)}
    if search:
        where += " AND (c.full_name ILIKE :s OR c.company_name ILIKE :s OR c.email ILIKE :s)"
        params["s"] = f"%{search}%"
    r = await db.execute(text(f"""
        SELECT c.*, l.status as lead_status, l.qualification_score,
               l.category, l.last_contact_date, l.ai_next_action, l.id as lead_id
        FROM contacts c
        LEFT JOIN leads l ON l.contact_id=c.id AND l.workspace_id=c.workspace_id
        {where} ORDER BY l.qualification_score DESC NULLS LAST, c.created_at DESC LIMIT 100
    """), params)
    contacts = [dict(r._mapping) for r in r.fetchall()]
    return {"contacts": contacts, "total": len(contacts)}

@router.post("/contacts")
async def create_contact(data: dict, current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    bridge = DataBridge(db, str(current_user.workspace_id))
    contact = await bridge.get_or_create_contact(
        email=data.get("email"), phone=data.get("phone"),
        full_name=data.get("full_name"), company_name=data.get("company_name"),
        source="manual"
    )
    return {"contact": contact}

# ─── LEADS ────────────────────────────────────────────────────────

@router.get("/leads")
async def list_leads(status: Optional[str] = None, category: Optional[str] = None,
                     current_user=Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    where = "WHERE l.workspace_id=:wid"
    params = {"wid": str(current_user.workspace_id)}
    if status:
        where += " AND l.status=:status"; params["status"] = status
    if category:
        where += " AND l.category=:category"; params["category"] = category
    r = await db.execute(text(f"""
        SELECT l.*,c.full_name,c.company_name,c.email,c.phone,c.industry,
               (SELECT COUNT(*) FROM calls ca WHERE ca.lead_id=l.id) as total_calls,
               (SELECT MAX(started_at) FROM calls ca WHERE ca.lead_id=l.id) as last_call
        FROM leads l JOIN contacts c ON c.id=l.contact_id
        {where} ORDER BY l.qualification_score DESC, l.updated_at DESC
    """), params)
    leads = [dict(r._mapping) for r in r.fetchall()]
    return {"leads": leads, "total": len(leads)}

@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, current_user=Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    bridge = DataBridge(db, str(current_user.workspace_id))
    profile = await bridge.get_lead_full_profile(lead_id)
    if not profile:
        raise HTTPException(404, "Lead not found")
    return {"lead": profile}

@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, data: dict,
                      current_user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    allowed = ["status","category","notes","next_follow_up_date",
               "estimated_deal_value","qualification_score"]
    parts, params = [], {"id": lead_id}
    for f in allowed:
        if f in data:
            parts.append(f"{f}=:{f}"); params[f] = data[f]
    if not parts:
        raise HTTPException(400, "No valid fields")
    await db.execute(
        text(f"UPDATE leads SET {', '.join(parts)}, updated_at=NOW() WHERE id=:id"), params
    )
    await db.commit()
    bridge = DataBridge(db, str(current_user.workspace_id))
    await bridge.add_timeline_event(lead_id, "manual_update", "Lead manually updated",
                                    metadata=data)
    return {"success": True}

# ─── CALLS ────────────────────────────────────────────────────────

@router.post("/initiate")
async def initiate_call(data: dict, current_user=Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    engine = CallEngine(db, str(current_user.workspace_id))
    return await engine.initiate_twilio_call(
        to_phone=data["to_phone"],
        from_phone=os.getenv("TWILIO_PHONE_NUMBER",""),
        contact_id=data.get("contact_id"), lead_id=data.get("lead_id")
    )

@router.post("/upload")
async def upload_call(file: UploadFile = File(...),
                      contact_id: Optional[str] = None,
                      background_tasks: BackgroundTasks = BackgroundTasks(),
                      current_user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    call_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp); tmp_path = tmp.name
    engine = CallEngine(db, str(current_user.workspace_id))
    result = await engine.upload_recording(call_id, tmp_path, contact_id=contact_id)
    if "error" not in result:
        background_tasks.add_task(_bg_process, call_id, result["recording_path"])
    return result

async def _bg_process(call_id: str, path: str):
    # Note: needs its own db session in production
    pass  # Called via task queue

@router.get("")
async def list_calls(contact_id: Optional[str] = None, lead_id: Optional[str] = None,
                     current_user=Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    where = "WHERE ca.workspace_id=:wid"
    params = {"wid": str(current_user.workspace_id)}
    if contact_id: where += " AND ca.contact_id=:cid"; params["cid"] = contact_id
    if lead_id: where += " AND ca.lead_id=:lid"; params["lid"] = lead_id
    r = await db.execute(text(f"""
        SELECT ca.*,c.full_name,c.company_name,
               an.qualification_score,an.qualification_category,an.summary,an.intent
        FROM calls ca
        LEFT JOIN contacts c ON c.id=ca.contact_id
        LEFT JOIN call_analysis an ON an.call_id=ca.id
        {where} ORDER BY ca.started_at DESC NULLS LAST, ca.created_at DESC LIMIT 50
    """), params)
    calls = [dict(r._mapping) for r in r.fetchall()]
    return {"calls": calls, "total": len(calls)}

@router.get("/{call_id}/transcript")
async def get_transcript(call_id: str, current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM call_transcripts WHERE call_id=:cid ORDER BY start_time"),
        {"cid": call_id}
    )
    segs = [dict(row._mapping) for row in r.fetchall()]
    ar = await db.execute(text("SELECT * FROM call_analysis WHERE call_id=:cid"), {"cid": call_id})
    row = ar.fetchone()
    return {"call_id": call_id, "segments": segs, "analysis": dict(row._mapping) if row else {}}

@router.post("/{call_id}/reanalyze")
async def reanalyze(call_id: str, current_user=Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM call_transcripts WHERE call_id=:cid ORDER BY start_time"),
        {"cid": call_id}
    )
    segs = [dict(row._mapping) for row in r.fetchall()]
    if not segs:
        raise HTTPException(404, "No transcript found")
    analysis = await LeadQualifier().analyze_call(call_id, segs, db)
    return {"analysis": analysis}

# ─── WEBHOOKS ──────────────────────────────────────────────────────

@router.get("/twiml/{call_id}")
async def get_twiml(call_id: str):
    engine = CallEngine(None, "")
    return Response(content=engine.get_twiml_response(call_id),
                    media_type="application/xml")

@router.post("/recording-webhook/{call_id}")
async def recording_webhook(call_id: str, background_tasks: BackgroundTasks,
                             recording_url: str = "", recording_duration: int = 0,
                             db: AsyncSession = Depends(get_db)):
    engine = CallEngine(db, "")
    background_tasks.add_task(engine.handle_recording_webhook,
                              call_id, recording_url, recording_duration)
    return {"status": "processing"}

@router.post("/status-webhook/{call_id}")
async def status_webhook(call_id: str, call_status: str = "",
                         db: AsyncSession = Depends(get_db)):
    status_map = {"completed":"completed","no-answer":"missed","busy":"missed",
                  "failed":"failed","canceled":"missed"}
    s = status_map.get(call_status, call_status)
    await db.execute(text("UPDATE calls SET status=:s WHERE id=:id"), {"s": s, "id": call_id})
    await db.commit()
    return {"status": "updated"}
```

### A6: Frontend — Call Hub

**File:** `apps/web/src/app/dashboard/calls/page.tsx`

Build a full page with:
1. **Header** — title, "Upload Recording" file input (accepts .wav/.mp3/.m4a), "Add Contact" link
2. **Stats row** — Total Leads, Hot Leads, Total Calls, Avg Score (4 KPI cards)
3. **Tab switcher** — "Lead Inbox" | "Call History"
4. **Lead Inbox tab** — list of leads sorted by score. Each card: avatar initial, name, company, email, category badge (hot=red, warm=orange, cold=blue, nurture=gray), score number, ai_next_action hint. Click → `/dashboard/calls/leads/[id]`
5. **Call History tab** — list of calls: status dot (green=completed, red=failed), name/company, timestamp, duration, qualification score, transcription status chip. Click → `/dashboard/calls/[id]`
6. Upload handler: POST to `/api/v1/calls/upload` with FormData, show "AI analyzing..." for 3s then refetch
7. Fetch both `/api/v1/calls` and `/api/v1/calls/leads` on mount

**File:** `apps/web/src/app/dashboard/calls/[id]/page.tsx` — Transcript Viewer:

Build page that:
1. Fetches `GET /api/v1/calls/{id}/transcript`
2. Shows two-column layout:
   - Left (60%): transcript segments, each with timestamp badge [MM:SS], speaker label (color-coded: SPEAKER_0=blue, SPEAKER_1=green), text. Highlight segments with high confidence differently.
   - Right (40%): AI Analysis panel — score gauge (0-100 circular), category badge, intent chip, urgency chip, objections list, buying signals list, key_points list, summary text, next_action highlighted box
3. "Re-analyze" button → `POST /api/v1/calls/{id}/reanalyze`
4. If transcript empty and transcription_status='pending': show "Transcript pending..." spinner
5. Back link to `/dashboard/calls`

**File:** `apps/web/src/app/dashboard/calls/leads/[id]/page.tsx` — Lead Profile:

Build page that:
1. Fetches `GET /api/v1/calls/leads/{id}`
2. Header: large avatar with initial, name, company, email/phone, score gauge, category badge
3. Three sections:
   - **Qualification**: intent, urgency, objections, buying signals in chips
   - **AI Assessment**: ai_summary paragraph, ai_next_action highlighted
   - **Timeline**: chronological event list with icons per event_type
4. Call history: list of calls with scores and analysis summaries, each linking to transcript viewer
5. "Update Status" select dropdown (new/contacted/qualified/warm/hot/cold/disqualified) → `PUT /api/v1/calls/leads/{id}`
6. "Add Note" textarea + submit → POST note to timeline
7. "Generate Email Draft" button → `POST /api/v1/email/draft/{lead_id}` → show draft in modal for review

---

## MODULE D: E-INVOICE INTELLIGENCE

### D1: Install dependencies

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install pdfplumber==0.11.0 pdf2image==1.17.0 pytesseract==0.3.13
pip install paddleocr==2.8.1 pillow==10.4.0
pip install reportlab==4.2.0
pip freeze | grep -E "pdfplumber|pdf2image|pytesseract|paddleocr|pillow|reportlab" >> requirements.txt
```

### D2: Invoice Intelligence Service

**File:** `apps/api/app/services/finance/invoice_intelligence.py`

```python
"""
Invoice Intelligence — OCR + LLM field extraction + Turkish tax classification.
"""
import logging, json, uuid
from pathlib import Path
from typing import Optional
from app.services.ai.model_config import call_ollama_json, call_ollama, TaskType

logger = logging.getLogger(__name__)
STORAGE = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/invoices")
STORAGE.mkdir(parents=True, exist_ok=True)

DISCLAIMER = "⚠️ Bu analiz yapay zeka tarafından oluşturulmuş bir TAHMİNDİR. Vergi yükümlülükleriniz için mali müşavirinize danışın."

TR_KDV = {"food_basic":1,"food_processed":10,"medicine":10,
           "software":20,"marketing":20,"professional_services":20,
           "advertising":20,"office":20,"general":20,"exempt":0}


class InvoiceIntelligence:

    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        if path.suffix.lower() == ".pdf":
            text = self._pdf_text(file_path)
            if len(text.strip()) > 50:
                return text
            return self._ocr_pdf(file_path)
        return self._ocr_image(file_path)

    def _pdf_text(self, fp: str) -> str:
        try:
            import pdfplumber
            parts = []
            with pdfplumber.open(fp) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t: parts.append(t)
            return "\n".join(parts)
        except Exception as e:
            logger.error(f"PDF text fail: {e}"); return ""

    def _ocr_pdf(self, fp: str) -> str:
        try:
            from pdf2image import convert_from_path
            import tempfile, os
            pages = convert_from_path(fp, dpi=200)
            texts = []
            for page in pages:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    page.save(tmp.name, "JPEG")
                    texts.append(self._ocr_image(tmp.name))
                    os.unlink(tmp.name)
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"PDF OCR fail: {e}"); return ""

    def _ocr_image(self, fp: str) -> str:
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='tr', show_log=False)
            result = ocr.ocr(fp)
            if not result or not result[0]: return ""
            return "\n".join(line[1][0] for line in result[0] if line[1][0].strip())
        except Exception:
            try:
                import pytesseract
                from PIL import Image
                return pytesseract.image_to_string(Image.open(fp), lang='tur+eng')
            except Exception as e:
                logger.error(f"OCR fail: {e}"); return ""

    def extract_fields(self, raw_text: str, file_name: str = "") -> dict:
        if not raw_text or len(raw_text.strip()) < 20:
            return {"error": "Insufficient text extracted"}
        schema = {
            "invoice_number":"INV-001","invoice_date":"2024-01-15",
            "due_date":"2024-02-15","vendor_name":"Example Co",
            "vendor_tax_id":"1234567890","customer_name":"My Co",
            "customer_tax_id":"0987654321","currency":"TRY",
            "subtotal":1000.0,"tax_amount":200.0,"total_amount":1200.0,
            "vat_rate":20,"direction":"incoming","category":"software",
            "description":"Software license","line_items":[],
            "confidence":0.85
        }
        prompt = f"""Extract structured data from this invoice/receipt.

DOCUMENT:
{raw_text[:4000]}

FILE: {file_name}

direction: 'incoming'=expense we received, 'outgoing'=income we issued
category: software|marketing|office|travel|professional_services|hardware|utilities|rent|food|advertising|general
If field not found use null. Estimate confidence 0-1."""
        return call_ollama_json(prompt, schema, task=TaskType.REASONING, timeout=120)

    def classify_tax(self, data: dict) -> dict:
        category = data.get("category","general")
        direction = data.get("direction","incoming")
        total = float(data.get("total_amount") or 0)
        vat_rate = float(data.get("vat_rate") or TR_KDV.get(category,20))
        vat_amount = float(data.get("tax_amount") or total * vat_rate / (100 + vat_rate))
        result = {
            "vat_rate": vat_rate, "vat_amount": round(vat_amount,2),
            "is_deductible": direction == "incoming",
            "tax_category": category, "disclaimer": DISCLAIMER
        }
        net = total - vat_amount
        if direction == "incoming":
            result["estimated_tax_impact"] = (
                f"Gider faturası: {vat_rate}% KDV ({vat_amount:.2f} {data.get('currency','TRY')}) "
                f"mahsup edilebilir. Net gider: {net:.2f}"
            )
            result["bookkeeping_account"] = "770 - Genel Yönetim Giderleri"
        else:
            result["estimated_tax_impact"] = (
                f"Satış faturası: {vat_rate}% KDV ({vat_amount:.2f} {data.get('currency','TRY')}) "
                f"beyan edilmeli. Net gelir: {net:.2f}"
            )
            result["bookkeeping_account"] = "600 - Yurt İçi Satışlar"
        return result

    def generate_insight(self, invoice: dict, tax: dict) -> str:
        prompt = f"""You are an accounting assistant. Brief practical insight for this invoice.
Vendor: {invoice.get('vendor_name')} | Date: {invoice.get('invoice_date')}
Amount: {invoice.get('total_amount')} {invoice.get('currency','TRY')} | VAT: {tax.get('vat_amount')} ({tax.get('vat_rate')}%)
Type: {invoice.get('direction','incoming')} | Category: {invoice.get('category')}
Write 2-3 sentences: what this is, VAT impact, one accounting note.
End with: "Please verify with your accountant before filing." """
        return call_ollama(prompt, task=TaskType.STANDARD, max_tokens=200, timeout=60)

    async def process_file(self, file_path: str, file_name: str,
                            db, workspace_id: str) -> dict:
        from sqlalchemy import text as sqla_text
        raw = self.extract_text(file_path)
        data = self.extract_fields(raw, file_name)
        if "error" in data:
            return {"error": data["error"]}
        tax = self.classify_tax(data)
        insight = self.generate_insight(data, tax)
        inv_id = str(uuid.uuid4())
        await db.execute(sqla_text("""
            INSERT INTO invoices(id,workspace_id,file_path,file_name,file_type,
            invoice_number,invoice_date,due_date,vendor_name,vendor_tax_id,
            customer_name,customer_tax_id,currency,subtotal,tax_amount,total_amount,
            direction,category,vat_rate,vat_amount,is_deductible,
            estimated_tax_impact,ai_notes,line_items,confidence_score,extraction_status)
            VALUES(:id,:wid,:fp,:fn,:ft,:inum,:idate,:ddate,:vendor,:vtax,
            :cust,:ctax,:curr,:sub,:tax,:total,:dir,:cat,:vrate,:vamt,:deduct,
            :taximp,:notes,:items::jsonb,:conf,'completed')
        """), {
            "id":inv_id,"wid":workspace_id,"fp":file_path,"fn":file_name,
            "ft":Path(file_name).suffix.lower().lstrip('.'),
            "inum":data.get("invoice_number"),"idate":data.get("invoice_date"),
            "ddate":data.get("due_date"),"vendor":data.get("vendor_name"),
            "vtax":data.get("vendor_tax_id"),"cust":data.get("customer_name"),
            "ctax":data.get("customer_tax_id"),"curr":data.get("currency","TRY"),
            "sub":data.get("subtotal"),"tax":data.get("tax_amount"),
            "total":data.get("total_amount"),"dir":data.get("direction","incoming"),
            "cat":data.get("category"),"vrate":tax.get("vat_rate"),
            "vamt":tax.get("vat_amount"),"deduct":tax.get("is_deductible",False),
            "taximp":tax.get("estimated_tax_impact"),
            "notes":f"{insight}\n\n{DISCLAIMER}",
            "items":json.dumps(data.get("line_items",[])),
            "conf":data.get("confidence",0.5)
        })
        await db.commit()
        return {"invoice_id":inv_id,"invoice_data":data,"tax_analysis":tax,
                "ai_insight":insight,"disclaimer":DISCLAIMER}
```

### D3: Finance API Endpoints

**File:** `apps/api/app/api/endpoints/finance.py`

```python
"""Finance Module — Invoice Intelligence API."""
import os, shutil, uuid
from pathlib import Path
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.finance.invoice_intelligence import InvoiceIntelligence

router = APIRouter(prefix="/api/v1/finance", tags=["Finance"])
logger = logging.getLogger(__name__)
STORE = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/invoices")
STORE.mkdir(parents=True, exist_ok=True)

@router.post("/invoices/upload")
async def upload_invoice(file: UploadFile = File(...),
                         background_tasks: BackgroundTasks = BackgroundTasks(),
                         current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    fid = str(uuid.uuid4())
    dest = STORE / f"{fid}{Path(file.filename).suffix}"
    with open(dest,"wb") as f: shutil.copyfileobj(file.file, f)
    background_tasks.add_task(_process_bg, str(dest), file.filename, db,
                              str(current_user.workspace_id))
    return {"invoice_id":fid,"status":"processing",
            "message":"AI analysis will complete in 30-60 seconds."}

async def _process_bg(fp, fn, db, wid):
    await InvoiceIntelligence().process_file(fp, fn, db, wid)

@router.get("/invoices")
async def list_invoices(direction: Optional[str] = None,
                        category: Optional[str] = None,
                        date_from: Optional[date] = None,
                        date_to: Optional[date] = None,
                        current_user=Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    where = "WHERE workspace_id=:wid"
    params = {"wid": str(current_user.workspace_id)}
    if direction: where += " AND direction=:dir"; params["dir"] = direction
    if category:  where += " AND category=:cat"; params["cat"] = category
    if date_from: where += " AND invoice_date>=:df"; params["df"] = date_from
    if date_to:   where += " AND invoice_date<=:dt"; params["dt"] = date_to
    r = await db.execute(
        text(f"SELECT * FROM invoices {where} ORDER BY invoice_date DESC NULLS LAST LIMIT 100"),
        params
    )
    invoices = [dict(row._mapping) for row in r.fetchall()]
    return {"invoices": invoices, "total": len(invoices)}

@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM invoices WHERE id=:id AND workspace_id=:wid"),
        {"id":invoice_id,"wid":str(current_user.workspace_id)}
    )
    row = r.fetchone()
    if not row: raise HTTPException(404,"Invoice not found")
    return {"invoice": dict(row._mapping)}

@router.put("/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, data: dict,
                         current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    allowed = ["vendor_name","invoice_date","total_amount","tax_amount",
               "direction","category","vat_rate","is_deductible"]
    parts, params = [], {"id": invoice_id}
    for f in allowed:
        if f in data: parts.append(f"{f}=:{f}"); params[f] = data[f]
    if parts:
        await db.execute(
            text(f"UPDATE invoices SET {', '.join(parts)},human_reviewed=true WHERE id=:id"),
            params
        )
        await db.commit()
    return {"success": True}

@router.get("/dashboard")
async def finance_dashboard(months: int = 3,
                             current_user=Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    wid = str(current_user.workspace_id)
    since = date.today() - timedelta(days=months*30)

    inc = await db.execute(text("""
        SELECT SUM(total_amount) as total, SUM(vat_amount) as vat, COUNT(*) as cnt
        FROM invoices WHERE workspace_id=:wid AND direction='outgoing'
        AND invoice_date>=:since AND extraction_status='completed'
    """), {"wid":wid,"since":since})
    income = dict(inc.fetchone()._mapping)

    exp = await db.execute(text("""
        SELECT SUM(total_amount) as total, SUM(vat_amount) as vat, COUNT(*) as cnt
        FROM invoices WHERE workspace_id=:wid AND direction='incoming'
        AND invoice_date>=:since AND extraction_status='completed'
    """), {"wid":wid,"since":since})
    expenses = dict(exp.fetchone()._mapping)

    cats = await db.execute(text("""
        SELECT category, direction, SUM(total_amount) as total, COUNT(*) as cnt
        FROM invoices WHERE workspace_id=:wid AND invoice_date>=:since
        AND extraction_status='completed'
        GROUP BY category, direction ORDER BY total DESC
    """), {"wid":wid,"since":since})
    categories = [dict(r._mapping) for r in cats.fetchall()]

    ti = float(income.get("total") or 0)
    te = float(expenses.get("total") or 0)
    vi = float(income.get("vat") or 0)
    ve = float(expenses.get("vat") or 0)

    return {
        "period_months": months,
        "income": {"total":ti,"vat_collected":vi,"net":ti-vi,"invoice_count":int(income.get("cnt") or 0)},
        "expenses": {"total":te,"vat_paid":ve,"net":te-ve,"invoice_count":int(expenses.get("cnt") or 0)},
        "profit_loss": {
            "gross": ti-te,
            "net_of_vat": (ti-vi)-(te-ve),
            "estimated_net_vat_payable": max(vi-ve,0),
            "estimated_vat_refundable": max(ve-vi,0)
        },
        "categories": categories,
        "disclaimer": "⚠️ Estimates only. Consult your accountant for official tax filing."
    }
```

### D4: Finance Frontend

**File:** `apps/web/src/app/dashboard/finance/page.tsx`

Build with:
1. **Header** — "Finance Intelligence" title, period selector (1/3/6/12 months), "Upload Invoice" file input
2. **KVKK/disclaimer banner** — yellow warning box
3. **P&L cards** — Income (green), Expenses (red), Net Profit (green/red conditional). Each shows total, VAT, invoice count
4. **Category breakdown table** — category, direction, total amount, invoice count
5. **Invoice list** — vendor name or filename, date, category, direction chip, total amount, VAT amount, extraction_status
6. Upload: POST to `/api/v1/finance/invoices/upload`, show "Processing..." then refetch after 5s
7. Click invoice → show modal with full ai_notes and tax_impact details

---

## MODULE E: MAUTIC BRIDGE

### E1: Mautic Bridge Service

**File:** `apps/api/app/services/email/mautic_bridge.py`

```python
"""
Mautic Integration Bridge — lead sync and AI-assisted outreach.
All email sends require human approval. Never auto-send.
"""
import logging, os, requests
from typing import Optional
from app.services.ai.model_config import call_ollama, TaskType

logger = logging.getLogger(__name__)
MAUTIC_URL = os.getenv("MAUTIC_URL","http://localhost:8181")
MAUTIC_USER = os.getenv("MAUTIC_USER","admin")
MAUTIC_PASS = os.getenv("MAUTIC_PASS","")


class MauticBridge:
    def __init__(self):
        self.base = f"{MAUTIC_URL}/api"
        self.auth = (MAUTIC_USER, MAUTIC_PASS)

    def _get(self, ep: str) -> dict:
        try:
            r = requests.get(f"{self.base}/{ep}", auth=self.auth, timeout=10)
            r.raise_for_status(); return r.json()
        except Exception as e:
            logger.error(f"Mautic GET {ep}: {e}"); return {}

    def _post(self, ep: str, data: dict) -> dict:
        try:
            r = requests.post(f"{self.base}/{ep}", json=data, auth=self.auth, timeout=10)
            r.raise_for_status(); return r.json()
        except Exception as e:
            logger.error(f"Mautic POST {ep}: {e}"); return {}

    def sync_contact(self, contact: dict, score: int = 0) -> Optional[str]:
        name_parts = (contact.get("full_name") or "").split()
        payload = {
            "email": contact.get("email"),
            "firstname": name_parts[0] if name_parts else "",
            "lastname": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            "company": contact.get("company_name"),
            "phone": contact.get("phone"),
            "points": score,
        }
        result = self._post("contacts/new", {k:v for k,v in payload.items() if v})
        return result.get("contact", {}).get("id")

    def trigger_sequence(self, mautic_id: str, sequence: str) -> bool:
        campaign_map = {
            "hot_lead_followup":     os.getenv("MAUTIC_CAMPAIGN_HOT","2"),
            "warm_lead_nurture":     os.getenv("MAUTIC_CAMPAIGN_WARM","1"),
            "cold_lead_reactivation":os.getenv("MAUTIC_CAMPAIGN_COLD","3"),
        }
        cid = campaign_map.get(sequence)
        if not cid: return False
        result = self._post(f"campaigns/{cid}/contact/{mautic_id}/add", {})
        return bool(result)

    def generate_email_draft(self, contact: dict, analysis: dict, purpose: str = "follow_up") -> dict:
        """Generate AI draft. Human MUST approve before sending."""
        prompt = f"""Generate a professional, personalized B2B email.

Contact: {contact.get('full_name')} at {contact.get('company_name')}
Lead Status: {analysis.get('qualification_category','warm')}
Intent: {analysis.get('intent','evaluating')}
Objections: {', '.join(analysis.get('objections',[]) or []) or 'none'}
Previous summary: {analysis.get('summary','Initial contact')}
Purpose: {purpose}

Write concise email (max 150 words):
1. Reference previous conversation naturally
2. Address main concern if any
3. Propose clear next step
4. Simple call to action

Format: Subject line first, blank line, then body.
Do NOT use "I hope this email finds you well"."""

        draft = call_ollama(prompt, task=TaskType.CREATIVE, max_tokens=300,
                            temperature=0.6, timeout=90)
        lines = draft.strip().split("\n")
        subject = lines[0].replace("Subject:","").strip() if lines else f"Following up"
        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else draft

        return {
            "subject": subject, "body": body,
            "requires_human_approval": True,
            "note": "AI draft — review and edit before sending."
        }
```

### E2: Email Bridge Endpoints

**File:** `apps/api/app/api/endpoints/email_bridge.py`

```python
"""Email Bridge — Mautic integration endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.email.mautic_bridge import MauticBridge
from app.services.shared.data_bridge import DataBridge

router = APIRouter(prefix="/api/v1/email", tags=["Email"])
logger = logging.getLogger(__name__)

@router.post("/sync-lead/{lead_id}")
async def sync_lead_to_mautic(lead_id: str, current_user=Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("""SELECT l.*,c.full_name,c.email,c.phone,c.company_name
                FROM leads l JOIN contacts c ON c.id=l.contact_id WHERE l.id=:lid"""),
        {"lid": lead_id}
    )
    row = r.fetchone()
    if not row: raise HTTPException(404, "Lead not found")
    lead = dict(row._mapping)
    if not lead.get("email"):
        raise HTTPException(400, "Lead has no email address")
    bridge = MauticBridge()
    mautic_id = bridge.sync_contact(lead, lead.get("qualification_score",0))
    sequence_map = {"hot":"hot_lead_followup","warm":"warm_lead_nurture","cold":"cold_lead_reactivation"}
    seq = sequence_map.get(lead.get("category","cold"),"warm_lead_nurture")
    return {"mautic_contact_id":mautic_id,"suggested_sequence":seq,
            "requires_approval":True,"message":"Confirm to trigger email sequence."}

@router.post("/trigger-sequence/{lead_id}")
async def trigger_sequence(lead_id: str, data: dict,
                            current_user=Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    bridge = MauticBridge()
    success = bridge.trigger_sequence(data["mautic_contact_id"], data["sequence"])
    if success:
        db_bridge = DataBridge(db, str(current_user.workspace_id))
        await db_bridge.add_timeline_event(lead_id, "email_sequence_started",
                                            f"Email sequence: {data['sequence']}",
                                            metadata=data)
    return {"success": success}

@router.post("/draft/{lead_id}")
async def generate_draft(lead_id: str, data: dict,
                         current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("""SELECT l.*,c.full_name,c.email,c.company_name,
                ca.intent,ca.qualification_category,ca.summary,ca.objections
                FROM leads l JOIN contacts c ON c.id=l.contact_id
                LEFT JOIN call_analysis ca ON ca.call_id=(
                    SELECT id FROM calls WHERE lead_id=l.id ORDER BY created_at DESC LIMIT 1
                )
                WHERE l.id=:lid"""),
        {"lid": lead_id}
    )
    row = r.fetchone()
    if not row: raise HTTPException(404, "Lead not found")
    lead = dict(row._mapping)
    bridge = MauticBridge()
    draft = bridge.generate_email_draft(
        contact=lead,
        analysis={"qualification_category":lead.get("qualification_category"),
                  "intent":lead.get("intent"),
                  "objections":lead.get("objections") or [],
                  "summary":lead.get("summary")},
        purpose=data.get("purpose","follow_up")
    )
    return draft
```

---

## MODULE C: AD ANALYTICS IMPROVEMENTS

### C1: Anomaly Detection Enhancement

Add to `apps/api/app/services/ad_analytics/forecasting_engine.py`:

```python
def detect_anomalies_enhanced(self, time_series: list[dict], metric: str = 'roas',
                               sensitivity: float = 1.5) -> dict:
    import numpy as np, pandas as pd
    if len(time_series) < 7:
        return {"anomalies":[],"status":"insufficient_data"}
    df = pd.DataFrame(time_series)
    if metric not in df.columns:
        return {"anomalies":[],"status":f"metric {metric} not found"}
    values = df[metric].fillna(0).values
    mean, std = np.mean(values), np.std(values)
    z_scores = np.abs((values - mean) / std) if std > 0 else np.zeros(len(values))
    try:
        from sklearn.ensemble import IsolationForest
        labels = IsolationForest(contamination=0.1, random_state=42).fit_predict(
            values.reshape(-1,1)
        )
    except Exception:
        labels = np.where(z_scores > sensitivity*2, -1, 1)
    anomalies = []
    for i,(z,label) in enumerate(zip(z_scores, labels)):
        if label == -1 or z > sensitivity*2:
            row = df.iloc[i]
            v = float(row[metric])
            direction = "spike" if v > mean else "drop"
            severity = "critical" if z > sensitivity*3 else "high" if z > sensitivity*2 else "medium"
            anomalies.append({
                "date": str(row.get("date",i)), "metric": metric,
                "value": v, "expected": round(mean,3),
                "deviation_pct": round((v-mean)/mean*100,1) if mean != 0 else 0,
                "direction": direction, "severity": severity,
                "description": f"{metric.upper()} {direction}: {v:.2f} vs expected {mean:.2f}"
            })
    return {"anomalies":anomalies,"metric":metric,"mean":round(mean,3),"total":len(anomalies)}
```

### C2: PDF Report Generator

**File:** `apps/api/app/services/ad_analytics/report_generator.py`

```python
"""PDF Report Generator — weekly ad performance reports."""
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)
REPORTS_DIR = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportGenerator:
    def generate_weekly_pdf(self, report_data: dict, workspace_name: str = "Growth") -> str:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.units import inch
        except ImportError:
            logger.warning("Install reportlab: pip install reportlab")
            return ""

        fname = REPORTS_DIR / f"weekly_{date.today().strftime('%Y%m%d')}.pdf"
        doc = SimpleDocTemplate(str(fname), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=22,
                                     textColor=colors.HexColor('#4F46E5'))
        story.append(Paragraph("Weekly Ad Performance Report", title_style))
        story.append(Paragraph(f"{workspace_name} — {date.today()}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        kpis = report_data.get("data", {})
        table_data = [
            ["Metric","This Week",""],
            ["Total Spend", f"${float(kpis.get('total_spend_7d',0)):,.0f}",""],
            ["Total Revenue",f"${float(kpis.get('total_revenue_7d',0)):,.0f}",""],
            ["Overall ROAS",f"{float(kpis.get('overall_roas_7d',0)):.2f}x",""],
            ["Conversions",f"{float(kpis.get('total_conversions_7d',0)):,.0f}",""],
        ]
        t = Table(table_data, colWidths=[2.5*inch,2*inch,2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#4F46E5')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F9FAFB')]),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*inch))

        if report_data.get("report"):
            story.append(Paragraph("AI Performance Analysis", styles['Heading2']))
            for para in report_data["report"].split("\n\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

        story.append(Spacer(1, 0.5*inch))
        footer = ParagraphStyle('F', parent=styles['Normal'], fontSize=8,
                                textColor=colors.grey)
        story.append(Paragraph("Generated by AI Growth OS. AI estimates only.", footer))

        doc.build(story)
        return str(fname)
```

Add to `apps/api/app/api/endpoints/ad_analytics.py`:
```python
@router.get("/reports/weekly-pdf")
async def download_weekly_pdf(account_id: str,
                               current_user=Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    from fastapi.responses import FileResponse
    from app.services.ad_analytics.report_generator import ReportGenerator
    from datetime import date
    report_data = await weekly_report(account_id=account_id, current_user=current_user, db=db)
    pdf_path = ReportGenerator().generate_weekly_pdf(report_data, "Acme Growth")
    if not pdf_path:
        raise HTTPException(500, "PDF generation failed — pip install reportlab")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"weekly_report_{date.today()}.pdf")
```

---

## MODULE F: AI LEARNING LAYER

### F1: AI Memory Service

**File:** `apps/api/app/services/ai/memory_service.py`

```python
"""
AI Learning & Memory — learns from user feedback to improve recommendations.
PostgreSQL for structured preferences + Chroma for semantic search.
"""
import logging, json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)
CHROMA_DIR = "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/chroma"


class AIMemoryService:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self._chroma = None
        self._embedder = None

    def _get_chroma(self):
        if not self._chroma:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=CHROMA_DIR)
        return self._chroma

    def _get_embedder(self):
        if not self._embedder:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    async def record_feedback(self, db: AsyncSession, module: str,
                               recommendation: dict, action: str,
                               modification: Optional[dict] = None):
        await db.execute(
            text("""INSERT INTO ai_feedback(workspace_id,module,feedback_type,
                    original_recommendation,user_action)
                    VALUES(:wid,:mod,:ft,:orig::jsonb,:act::jsonb)"""),
            {"wid":self.workspace_id,"mod":module,"ft":action,
             "orig":json.dumps(recommendation),"act":json.dumps(modification or {"action":action})}
        )
        await self._update_preference(db, module, recommendation, action)
        await db.commit()

    async def _update_preference(self, db, module, recommendation, action):
        key = f"pref_{recommendation.get('type','unknown')}"
        r = await db.execute(
            text("SELECT value,observation_count FROM ai_memory WHERE workspace_id=:wid AND module=:mod AND key=:key"),
            {"wid":self.workspace_id,"mod":module,"key":key}
        )
        row = r.fetchone()
        if row:
            row = dict(row._mapping)
            pref = row["value"] if isinstance(row["value"],dict) else {}
            cnt = row["observation_count"] + 1
            accepts = pref.get("accepts",0) + (1 if action=="accepted" else 0)
            rejects = pref.get("rejects",0) + (1 if action=="rejected" else 0)
            rate = accepts/(accepts+rejects) if (accepts+rejects) > 0 else 0.5
            await db.execute(
                text("""UPDATE ai_memory SET value=:v::jsonb,observation_count=:cnt,
                        confidence=:conf,last_updated=NOW()
                        WHERE workspace_id=:wid AND module=:mod AND key=:key"""),
                {"v":json.dumps({"accepts":accepts,"rejects":rejects,"accept_rate":rate}),
                 "cnt":cnt,"conf":min(0.95,0.5+rate*0.5),
                 "wid":self.workspace_id,"mod":module,"key":key}
            )
        else:
            await db.execute(
                text("""INSERT INTO ai_memory(workspace_id,module,memory_type,key,value,confidence)
                        VALUES(:wid,:mod,'preference',:key,:v::jsonb,0.5)
                        ON CONFLICT(workspace_id,module,key) DO NOTHING"""),
                {"wid":self.workspace_id,"mod":module,"key":key,
                 "v":json.dumps({"accepts":1 if action=="accepted" else 0,
                                 "rejects":1 if action=="rejected" else 0})}
            )

    async def get_preferences(self, db: AsyncSession, module: str) -> dict:
        r = await db.execute(
            text("SELECT key,value,confidence,observation_count FROM ai_memory WHERE workspace_id=:wid AND module=:mod"),
            {"wid":self.workspace_id,"mod":module}
        )
        return {row["key"]:{"value":row["value"],"confidence":float(row["confidence"] or 0),
                             "observations":row["observation_count"]}
                for row in [dict(r._mapping) for r in r.fetchall()]}

    async def store_call_embedding(self, call_id: str, transcript: str, analysis: dict):
        try:
            emb = self._get_embedder().encode([transcript[:2000]])[0].tolist()
            col = self._get_chroma().get_or_create_collection(
                f"calls_{self.workspace_id[:20]}", metadata={"hnsw:space":"cosine"}
            )
            col.add(ids=[call_id], embeddings=[emb],
                    metadatas=[{"call_id":call_id,
                                "score":analysis.get("qualification_score",0),
                                "category":analysis.get("qualification_category","?")}],
                    documents=[transcript[:2000]])
        except Exception as e:
            logger.error(f"Embedding store failed: {e}")

    async def find_similar_calls(self, query: str, n=5) -> list:
        try:
            emb = self._get_embedder().encode([query])[0].tolist()
            col = self._get_chroma().get_collection(f"calls_{self.workspace_id[:20]}")
            results = col.query(query_embeddings=[emb], n_results=n)
            return results.get("metadatas",[[]])[0]
        except Exception:
            return []

    async def get_summary(self, db: AsyncSession) -> dict:
        r = await db.execute(
            text("SELECT module,feedback_type,COUNT(*) as cnt FROM ai_feedback WHERE workspace_id=:wid GROUP BY module,feedback_type"),
            {"wid":self.workspace_id}
        )
        feedback = [dict(row._mapping) for row in r.fetchall()]
        mc = await db.execute(
            text("SELECT COUNT(*) as cnt FROM ai_memory WHERE workspace_id=:wid"),
            {"wid":self.workspace_id}
        )
        mem_count = dict(mc.fetchone()._mapping).get("cnt",0)
        return {
            "total_feedback": sum(r["cnt"] for r in feedback),
            "feedback_by_module": feedback,
            "learned_preferences": mem_count,
            "status": "active" if mem_count > 0 else "gathering_data"
        }
```

### F2: AI Learning Endpoints

**File:** `apps/api/app/api/endpoints/ai_learning.py`

```python
"""AI Learning endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.ai.memory_service import AIMemoryService

router = APIRouter(prefix="/api/v1/ai-learning", tags=["AI Learning"])
logger = logging.getLogger(__name__)

@router.get("/summary")
async def get_summary(current_user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    svc = AIMemoryService(str(current_user.workspace_id))
    return await svc.get_summary(db)

@router.post("/feedback")
async def record_feedback(data: dict, current_user=Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    svc = AIMemoryService(str(current_user.workspace_id))
    await svc.record_feedback(
        db, module=data["module"],
        recommendation=data["recommendation"],
        action=data["action"],  # accepted/rejected/modified
        modification=data.get("modification")
    )
    return {"success": True}

@router.get("/preferences/{module}")
async def get_preferences(module: str, current_user=Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    svc = AIMemoryService(str(current_user.workspace_id))
    return {"preferences": await svc.get_preferences(db, module)}
```

### F3: AI Learning Frontend

**File:** `apps/web/src/app/dashboard/ai-learning/page.tsx`

Build with:
1. **Header** — "AI Learning System" title, status badge (Active/Gathering Data)
2. **Summary cards** — Total Feedback Events, Learned Preferences, Learning Status
3. **Module breakdown table** — module name, accepted count, rejected count, accept rate as progress bar
4. **What AI learned** — list of preferences from each module (formatted from key/value pairs)
5. Fetch from `GET /api/v1/ai-learning/summary` on mount

---

## FINAL INTEGRATION

### Register all new routers in `apps/api/app/main.py`:

```python
from app.api.endpoints.calling import router as calling_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints.email_bridge import router as email_router
from app.api.endpoints.ai_learning import router as ai_learning_router

app.include_router(calling_router)
app.include_router(finance_router)
app.include_router(email_router)
app.include_router(ai_learning_router)
```

### Update `.env` — append without overwriting:

```bash
cat >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env" << 'ENVEOF'

# CALLING
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
WEBHOOK_BASE_URL=http://localhost:8000
HUGGINGFACE_TOKEN=

# MAUTIC CAMPAIGNS
MAUTIC_URL=http://localhost:8181
MAUTIC_USER=admin
MAUTIC_PASS=
MAUTIC_CAMPAIGN_WARM=1
MAUTIC_CAMPAIGN_HOT=2
MAUTIC_CAMPAIGN_COLD=3

# STORAGE
STORAGE_BASE=/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage
ENVEOF
```

### Update Sidebar — find main nav component and add:

```typescript
// Import icons at top:
import { Phone, Users, UserPlus, BarChart3, Upload, Brain, Target, DollarSign } from 'lucide-react'

// Add these nav sections:
{
  section: "CALLING ENGINE",
  items: [
    { label: "Call Hub", href: "/dashboard/calls", icon: Phone },
    { label: "Lead Inbox", href: "/dashboard/calls", icon: Users },
    { label: "Add Contact", href: "/dashboard/calls/new-contact", icon: UserPlus },
  ]
},
{
  section: "FINANCE",
  items: [
    { label: "P&L Dashboard", href: "/dashboard/finance", icon: BarChart3 },
    { label: "Upload Invoice", href: "/dashboard/finance", icon: Upload },
  ]
},
{
  section: "AI SYSTEM",
  items: [
    { label: "AI Learning", href: "/dashboard/ai-learning", icon: Brain },
  ]
},
```

---

## VERIFICATION

```bash
# 1. Table check
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 -c "
import asyncio, asyncpg, os
async def main():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
    names = [r['tablename'] for r in rows]
    for t in ['contacts','leads','lead_timeline','calls','call_transcripts',
              'call_analysis','invoices','ai_feedback','ai_memory']:
        print(f\"{'✅' if t in names else '❌'} {t}\")
    await conn.close()
asyncio.run(main())
"

# 2. Model check
curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
models = [m['name'] for m in json.load(sys.stdin).get('models',[])]
for p in ['gemma4','deepseek-r1','qwen3:14b','qwen3:8b']:
    found = any(p.split(':')[0] in m for m in models)
    print(f\"{'✅' if found else '❌'} {p}\")
"

# 3. Start backend
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 2
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
uvicorn app.main:app --reload --port 8000 &
sleep 10

# 4. JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAILED'))")
echo "Token: ${TOKEN:0:40}..."

# 5. Endpoint tests
for ep in \
  "GET /api/v1/calls" \
  "GET /api/v1/calls/contacts" \
  "GET /api/v1/calls/leads" \
  "GET /api/v1/finance/invoices" \
  "GET /api/v1/finance/dashboard" \
  "GET /api/v1/ai-learning/summary"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X $method \
    "http://localhost:8000${path}" -H "Authorization: Bearer $TOKEN")
  echo "$STATUS  $ep"
done

# 6. File check
for f in \
  "apps/api/app/services/ai/model_config.py" \
  "apps/api/app/services/calling/call_engine.py" \
  "apps/api/app/services/calling/transcription_engine.py" \
  "apps/api/app/services/calling/lead_qualifier.py" \
  "apps/api/app/services/finance/invoice_intelligence.py" \
  "apps/api/app/services/email/mautic_bridge.py" \
  "apps/api/app/services/ai/memory_service.py" \
  "apps/api/app/services/shared/data_bridge.py" \
  "apps/api/app/api/endpoints/calling.py" \
  "apps/api/app/api/endpoints/finance.py" \
  "apps/api/app/api/endpoints/email_bridge.py" \
  "apps/api/app/api/endpoints/ai_learning.py" \
  "apps/web/src/app/dashboard/calls/page.tsx" \
  "apps/web/src/app/dashboard/calls/[id]/page.tsx" \
  "apps/web/src/app/dashboard/calls/leads/[id]/page.tsx" \
  "apps/web/src/app/dashboard/finance/page.tsx" \
  "apps/web/src/app/dashboard/ai-learning/page.tsx"; do
  full="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/$f"
  echo "$([ -f \"$full\" ] && echo ✅ || echo ❌) $f"
done

# 7. Frontend build
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npx next build 2>&1 | grep -E "error|Error|✓ Compiled|Route" | tail -20
```

Fix every ❌ before declaring done.

---

## SUCCESS CRITERIA

```
╔═══════════════════════════════════════════════════════════╗
║        AI GROWTH OS — FULL TRANSFORMATION DONE           ║
╠═══════════════════════════════════════════════════════════╣
║ B: LOCAL AI UPGRADE        ✅ Gemma4/Qwen3/DeepSeek      ║
║ G: CROSS-MODULE BRIDGE     ✅ Contacts/Leads/Timeline     ║
║ A: CALLING ENGINE          ✅ Call/Transcribe/Qualify      ║
║ C: AD ANALYTICS+           ✅ Anomaly/PDF Report           ║
║ D: INVOICE INTELLIGENCE    ✅ OCR/Extract/Tax Analysis     ║
║ E: MAUTIC BRIDGE           ✅ Lead Sync/Sequences/Drafts   ║
║ F: AI LEARNING             ✅ Memory/Feedback/Embeddings   ║
╠═══════════════════════════════════════════════════════════╣
║ DB TABLES       ✅ 9 new tables                           ║
║ API ENDPOINTS   ✅ 25+ new endpoints                      ║
║ FRONTEND PAGES  ✅ 5 new pages                            ║
║ SIDEBAR         ✅ 3 new sections                         ║
╠═══════════════════════════════════════════════════════════╣
║ NEXT STEPS AFTER BUILD:                                   ║
║ 1. Add TWILIO credentials to .env                        ║
║ 2. Add HUGGINGFACE_TOKEN for diarization                 ║
║ 3. Upload test call → /dashboard/calls                   ║
║ 4. Upload test invoice → /dashboard/finance              ║
║ 5. Check AI Learning → /dashboard/ai-learning            ║
╚═══════════════════════════════════════════════════════════╝
```
