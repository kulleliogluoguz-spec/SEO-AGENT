# PHASE 2 — FULL PLATFORM TRANSFORMATION MEGAPROMPT
## AI Growth OS — All 7 Approved Improvements
## File: apps/api/PHASE2_FULL.md

You are a senior full-stack engineer, ML architect, and systems integration specialist.
Execute ALL 7 modules below completely. No skipping. No stubs. No asking permission between steps.

Platform: /Users/oguzkullelioglu/Desktop/ai-cmo-os 2/
Stack: FastAPI (8000) + Next.js 14 (3001) + PostgreSQL + n8n (5678) + Mautic (8181) + Ollama (11434)

CRITICAL RULES:
- Never break existing functionality
- All AI = local Ollama only
- Human approval required before executing live actions (budget changes, email sends)
- Tax/financial outputs: always include "consult your accountant" disclaimer
- Call recording: always announce recording to caller (KVKK compliance)
- Fix CI errors after each module (ruff + tsc --noEmit)

---

## PHASE 0: FULL AUDIT

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"
cat "$BASE/apps/api/app/main.py"
cat "$BASE/apps/api/.env"
ls "$BASE/apps/api/app/api/endpoints/"
ls "$BASE/apps/api/app/services/"
find "$BASE/apps/web/src/app/dashboard" -name "page.tsx" | sort
docker ps
curl -s http://localhost:5678/healthz 2>/dev/null && echo "n8n OK" || echo "n8n DOWN"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8181 && echo " Mautic" || echo "Mautic DOWN"
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]"
python3 -c "
import asyncio, asyncpg, os
async def main():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
    [print(r['tablename']) for r in rows]
    await conn.close()
asyncio.run(main())
"
```

---

## MODULE A: MAUTIC FIX + N8N CONNECTION

### A1: Diagnose and fix Mautic

```bash
# Check Mautic container
docker ps -a | grep -i mautic
docker logs $(docker ps -a | grep -i mautic | awk '{print $1}') --tail 100 2>/dev/null

# If container exists but stopped, restart it
docker start $(docker ps -a | grep -i mautic | awk '{print $1}') 2>/dev/null

# Check if port 8181 responds
curl -s -o /dev/null -w "%{http_code}" http://localhost:8181

# Check Mautic cron status inside container
docker exec $(docker ps | grep mautic | awk '{print $1}') \
  php /var/www/html/bin/console mautic:segments:update --no-interaction 2>/dev/null \
  || echo "Mautic cron failed or container not running"

# Check disk space
df -h | head -5
```

If Mautic is down, find its docker-compose file and restart it:
```bash
find "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2" -name "docker-compose*.yml" | \
  xargs grep -l "mautic" 2>/dev/null
# Then:
cd [directory_with_mautic_compose]
docker-compose up -d mautic
```

Add health check to Mautic compose service (find and update the file):
```yaml
# Add to mautic service in docker-compose:
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/s/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### A2: Create n8n monitoring workflows via API

First check if n8n is running and get its URL:
```bash
curl -s http://localhost:5678/healthz
# n8n API credentials from .env or default admin
N8N_URL="http://localhost:5678"
```

Create `apps/api/app/services/automation/n8n_client.py`:

```python
"""
n8n Integration Client
Triggers workflows and monitors platform health via n8n.
"""
import logging
import os
import httpx
from typing import Optional

logger = logging.getLogger(__name__)
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


class N8NClient:
    """
    Sends events to n8n webhooks for workflow automation.
    Non-blocking — platform continues if n8n is down.
    """

    async def trigger_webhook(self, webhook_path: str, payload: dict) -> bool:
        """Fire-and-forget webhook trigger."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{N8N_URL}/webhook/{webhook_path}",
                    json=payload
                )
                return r.status_code < 300
        except Exception as e:
            logger.warning(f"n8n webhook {webhook_path} failed (non-critical): {e}")
            return False

    async def notify_lead_hot(self, lead_id: str, contact_name: str,
                               score: int, workspace_id: str) -> bool:
        return await self.trigger_webhook("lead-hot", {
            "lead_id": lead_id,
            "contact_name": contact_name,
            "score": score,
            "workspace_id": workspace_id,
            "action": "lead_became_hot"
        })

    async def notify_call_completed(self, call_id: str, lead_id: Optional[str],
                                     duration: int, workspace_id: str) -> bool:
        return await self.trigger_webhook("call-completed", {
            "call_id": call_id,
            "lead_id": lead_id,
            "duration_seconds": duration,
            "workspace_id": workspace_id
        })

    async def notify_roas_critical(self, campaign_id: str, campaign_name: str,
                                    roas: float, workspace_id: str) -> bool:
        return await self.trigger_webhook("roas-alert", {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "roas": roas,
            "workspace_id": workspace_id,
            "severity": "critical"
        })

    async def notify_invoice_processed(self, invoice_id: str,
                                        vendor: str, total: float,
                                        workspace_id: str) -> bool:
        return await self.trigger_webhook("invoice-processed", {
            "invoice_id": invoice_id,
            "vendor": vendor,
            "total": total,
            "workspace_id": workspace_id
        })

    async def notify_weekly_report_ready(self, workspace_id: str,
                                          report_url: str) -> bool:
        return await self.trigger_webhook("weekly-report", {
            "workspace_id": workspace_id,
            "report_url": report_url
        })


# Singleton
n8n = N8NClient()
```

### A3: Platform Events Bus

Create `apps/api/scripts/create_events_table.py`:

```python
import asyncio, asyncpg, os

async def create():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            source_module VARCHAR(50) NOT NULL,
            workspace_id UUID,
            payload JSONB DEFAULT '{}',
            processed_by TEXT[] DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_events_type_workspace
            ON platform_events(event_type, workspace_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_created
            ON platform_events(created_at DESC);
    """)
    print("✅ platform_events table created")
    await conn.close()

asyncio.run(create())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/create_events_table.py
```

Create `apps/api/app/services/automation/event_bus.py`:

```python
"""
Platform Event Bus
All modules publish events here. n8n and other modules subscribe.
"""
import logging
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.automation.n8n_client import n8n

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event publisher for cross-module communication.
    Persists events to DB and fires n8n webhooks.
    """

    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    async def publish(self, event_type: str, source_module: str,
                       payload: dict) -> str:
        """Publish an event. Returns event ID."""
        result = await self.db.execute(
            text("""
                INSERT INTO platform_events
                    (event_type, source_module, workspace_id, payload)
                VALUES (:et, :src, :wid, :payload::jsonb)
                RETURNING id
            """),
            {
                "et": event_type,
                "src": source_module,
                "wid": self.workspace_id,
                "payload": json.dumps(payload)
            }
        )
        event_id = str(result.fetchone()[0])
        await self.db.commit()

        # Fire n8n webhook (non-blocking)
        await self._dispatch_to_n8n(event_type, payload)

        logger.info(f"Event published: {event_type} from {source_module}")
        return event_id

    async def _dispatch_to_n8n(self, event_type: str, payload: dict):
        """Route events to appropriate n8n webhooks."""
        if event_type == "lead_became_hot":
            await n8n.notify_lead_hot(
                lead_id=payload.get("lead_id",""),
                contact_name=payload.get("contact_name",""),
                score=payload.get("score",0),
                workspace_id=self.workspace_id
            )
        elif event_type == "call_completed":
            await n8n.notify_call_completed(
                call_id=payload.get("call_id",""),
                lead_id=payload.get("lead_id"),
                duration=payload.get("duration_seconds",0),
                workspace_id=self.workspace_id
            )
        elif event_type == "roas_critical":
            await n8n.notify_roas_critical(
                campaign_id=payload.get("campaign_id",""),
                campaign_name=payload.get("campaign_name",""),
                roas=payload.get("roas",0),
                workspace_id=self.workspace_id
            )
        elif event_type == "invoice_processed":
            await n8n.notify_invoice_processed(
                invoice_id=payload.get("invoice_id",""),
                vendor=payload.get("vendor_name",""),
                total=payload.get("total_amount",0),
                workspace_id=self.workspace_id
            )

    async def get_recent_events(self, limit: int = 50,
                                 event_type: Optional[str] = None) -> list:
        where = "WHERE workspace_id = :wid"
        params = {"wid": self.workspace_id}
        if event_type:
            where += " AND event_type = :et"
            params["et"] = event_type
        r = await self.db.execute(
            text(f"""
                SELECT id, event_type, source_module, payload, created_at
                FROM platform_events {where}
                ORDER BY created_at DESC LIMIT :lim
            """),
            {**params, "lim": limit}
        )
        return [dict(row._mapping) for row in r.fetchall()]
```

### A4: Add .env variables for n8n

```bash
# Append to apps/api/.env
cat >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env" << 'EOF'

# N8N
N8N_URL=http://localhost:5678
N8N_API_KEY=

# MAUTIC
MAUTIC_URL=http://localhost:8181
MAUTIC_USER=admin
MAUTIC_PASS=
MAUTIC_CAMPAIGN_HOT=2
MAUTIC_CAMPAIGN_WARM=1
MAUTIC_CAMPAIGN_COLD=3
EOF
```

### A5: Add System Health API endpoint

Add to `apps/api/app/api/endpoints/system.py` (create if not exists):

```python
"""System health monitoring endpoint."""
import os, httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.dependencies.auth import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/system", tags=["System"])


@router.get("/health")
async def system_health(current_user=Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """Check health of all platform components."""
    status = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        status["database"] = {"status": "ok"}
    except Exception as e:
        status["database"] = {"status": "error", "detail": str(e)[:100]}

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = {"status": "ok", "models": models}
    except Exception:
        status["ollama"] = {"status": "offline"}

    # n8n
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{os.getenv('N8N_URL','http://localhost:5678')}/healthz")
            status["n8n"] = {"status": "ok" if r.status_code == 200 else "degraded"}
    except Exception:
        status["n8n"] = {"status": "offline"}

    # Mautic
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{os.getenv('MAUTIC_URL','http://localhost:8181')}/s/health")
            status["mautic"] = {"status": "ok" if r.status_code < 400 else "degraded"}
    except Exception:
        status["mautic"] = {"status": "offline"}

    # Recent events
    try:
        r = await db.execute(
            text("SELECT COUNT(*) as cnt FROM platform_events WHERE created_at > NOW() - INTERVAL '1 hour'")
        )
        status["events_last_hour"] = int(r.fetchone()[0])
    except Exception:
        status["events_last_hour"] = 0

    overall = "ok" if all(
        v.get("status") == "ok" for v in status.values() if isinstance(v, dict)
    ) else "degraded"

    return {"overall": overall, "components": status}
```

Register in main.py:
```python
from app.api.endpoints.system import router as system_router
app.include_router(system_router)
```

### A6: Platform Health Frontend Page

Create `apps/web/src/app/dashboard/system/page.tsx`:

```typescript
'use client'
import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
})

const STATUS_ICON = {
  ok: <CheckCircle className="w-5 h-5 text-green-500" />,
  offline: <XCircle className="w-5 h-5 text-red-500" />,
  degraded: <AlertCircle className="w-5 h-5 text-yellow-500" />,
  error: <XCircle className="w-5 h-5 text-red-500" />,
}

export default function SystemHealth() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    setRefreshing(true)
    try {
      const r = await fetch(`${API}/api/v1/system/health`, { headers: hdrs() })
      if (r.ok) setHealth(await r.json())
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const components = health?.components || {}
  const overall = health?.overall || 'unknown'

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
          <p className="text-sm text-gray-500 mt-1">Platform component status</p>
        </div>
        <button onClick={load} disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Overall Status */}
      <div className={`rounded-xl p-4 border-2 ${
        overall === 'ok' ? 'bg-green-50 border-green-200' :
        overall === 'degraded' ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'
      }`}>
        <div className="flex items-center gap-3">
          {STATUS_ICON[overall as keyof typeof STATUS_ICON] || <AlertCircle className="w-5 h-5 text-gray-400" />}
          <div>
            <div className="font-semibold capitalize">System {overall}</div>
            <div className="text-sm text-gray-600">
              {health?.events_last_hour || 0} events in the last hour
            </div>
          </div>
        </div>
      </div>

      {/* Component Cards */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(components).map(([name, info]: [string, any]) => (
          <div key={name} className="bg-white rounded-xl border p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-800 capitalize">{name}</span>
              {STATUS_ICON[info?.status as keyof typeof STATUS_ICON] ||
               <AlertCircle className="w-4 h-4 text-gray-400" />}
            </div>
            <div className={`text-sm font-medium ${
              info?.status === 'ok' ? 'text-green-600' :
              info?.status === 'offline' ? 'text-red-600' : 'text-yellow-600'
            }`}>
              {info?.status?.toUpperCase()}
            </div>
            {info?.models && (
              <div className="text-xs text-gray-400 mt-1">
                {info.models.slice(0, 3).join(', ')}
              </div>
            )}
            {info?.detail && (
              <div className="text-xs text-red-500 mt-1 truncate">{info.detail}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

Add to sidebar: `{ label: 'System Health', href: '/dashboard/system', icon: Activity }`

---

## MODULE B: TWILIO AUTOMATIC CALL RECORDING PIPELINE

### B1: Fix the complete call pipeline (no more manual upload)

The current system has manual upload. Replace with fully automatic pipeline:

Update `apps/api/app/services/calling/call_engine.py` — fix `_process_async`:

```python
async def _process_async(self, call_id: str, recording_path: str) -> None:
    """
    Full automatic pipeline after call recording received:
    1. Transcribe with WhisperX
    2. Analyze with local AI (Ollama)
    3. Update lead score
    4. Publish event to bus
    5. Notify n8n
    """
    from app.services.calling.transcription_engine import TranscriptionEngine
    from app.services.calling.lead_qualifier import LeadQualifier
    from app.services.shared.data_bridge import DataBridge
    from app.services.automation.event_bus import EventBus
    from app.core.database import AsyncSessionLocal

    logger.info(f"[AUTO PIPELINE] Starting for call {call_id}")

    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Transcribe
            transcriber = TranscriptionEngine(model_size="large-v3", language=None)
            segments = await transcriber.transcribe_call(call_id, recording_path, db)

            if not segments:
                logger.warning(f"No transcript for call {call_id}")
                return

            logger.info(f"[AUTO PIPELINE] {len(segments)} segments transcribed")

            # Step 2: AI Analysis
            qualifier = LeadQualifier()
            analysis = await qualifier.analyze_call(call_id, segments, db)

            # Step 3: Update lead if exists
            call_r = await db.execute(
                text("SELECT lead_id, workspace_id, contact_id FROM calls WHERE id = :id"),
                {"id": call_id}
            )
            call_row = call_r.fetchone()

            if call_row and call_row.lead_id:
                bridge = DataBridge(db, str(call_row.workspace_id))
                await bridge.update_lead_from_call(str(call_row.lead_id), analysis)

                # Check if lead became hot
                if analysis.get("qualification_score", 0) >= 75:
                    contact_r = await db.execute(
                        text("SELECT full_name FROM contacts WHERE id = :id"),
                        {"id": call_row.contact_id}
                    )
                    contact = contact_r.fetchone()
                    bus = EventBus(db, str(call_row.workspace_id))
                    await bus.publish("lead_became_hot", "calling", {
                        "lead_id": str(call_row.lead_id),
                        "contact_name": contact.full_name if contact else "Unknown",
                        "score": analysis.get("qualification_score", 0),
                        "call_id": call_id
                    })

            # Step 4: Publish call_completed event
            if call_row:
                duration_r = await db.execute(
                    text("SELECT duration_seconds FROM calls WHERE id = :id"),
                    {"id": call_id}
                )
                dur_row = duration_r.fetchone()
                bus = EventBus(db, str(call_row.workspace_id))
                await bus.publish("call_completed", "calling", {
                    "call_id": call_id,
                    "lead_id": str(call_row.lead_id) if call_row.lead_id else None,
                    "duration_seconds": dur_row.duration_seconds if dur_row else 0,
                    "qualification_score": analysis.get("qualification_score", 0),
                    "qualification_category": analysis.get("qualification_category", "unknown")
                })

            logger.info(f"[AUTO PIPELINE] Complete for call {call_id}: score={analysis.get('qualification_score')}")

        except Exception as e:
            logger.error(f"[AUTO PIPELINE] Failed for call {call_id}: {e}", exc_info=True)
            await db.execute(
                text("UPDATE calls SET analysis_status='failed' WHERE id=:id"),
                {"id": call_id}
            )
            await db.commit()
```

### B2: LiveKit integration for browser-based calling

Install LiveKit:
```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
pip install livekit==0.11.1 livekit-api==0.7.0
echo "livekit==0.11.1" >> requirements.txt
echo "livekit-api==0.7.0" >> requirements.txt

cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/web"
npm install livekit-client @livekit/components-react
```

Create `apps/api/app/services/calling/livekit_engine.py`:

```python
"""
LiveKit Engine — browser-based WebRTC calling with automatic recording.
Self-hosted, zero per-minute cost, full control.
"""
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")


class LiveKitEngine:
    """
    Manages LiveKit rooms for browser-based calls.
    Each call gets its own room. Recording via LiveKit Egress.
    """

    def generate_token(self, room_name: str, participant_identity: str,
                       is_agent: bool = False) -> str:
        """Generate a JWT token for room access."""
        try:
            from livekit.api import AccessToken, VideoGrants
            token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            token.with_identity(participant_identity)
            token.with_name(participant_identity)
            grants = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
            token.with_grants(grants)
            return token.to_jwt()
        except ImportError:
            logger.error("livekit-api not installed")
            return ""
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return ""

    def create_room_name(self, call_id: str) -> str:
        return f"call-{call_id}"

    async def start_room_recording(self, call_id: str,
                                    output_path: str) -> Optional[str]:
        """Start recording a LiveKit room via Egress API."""
        try:
            from livekit.api import LiveKitAPI, EgressInfo
            room_name = self.create_room_name(call_id)
            async with LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) as api:
                egress = await api.egress.start_room_composite_egress(
                    room_name=room_name,
                    audio_only=True,
                    file_outputs=[{"filepath": output_path, "audio_only": True}]
                )
                return egress.egress_id
        except Exception as e:
            logger.error(f"LiveKit recording start failed: {e}")
            return None

    async def stop_recording(self, egress_id: str) -> bool:
        """Stop a LiveKit recording."""
        try:
            from livekit.api import LiveKitAPI
            async with LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) as api:
                await api.egress.stop_egress(egress_id=egress_id)
            return True
        except Exception as e:
            logger.error(f"LiveKit stop recording failed: {e}")
            return False
```

Add LiveKit endpoints to calling router:

```python
# Add to apps/api/app/api/endpoints/calling.py

@router.post("/livekit/token")
async def get_livekit_token(
    data: dict,  # {"call_id": "...", "identity": "agent_name"}
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate LiveKit room token for browser-based calling.
    Creates a new call record and returns token for WebRTC connection.
    """
    from app.services.calling.livekit_engine import LiveKitEngine
    import os

    call_id = data.get("call_id") or str(uuid.uuid4())
    contact_id = data.get("contact_id")
    identity = data.get("identity", f"user_{current_user.id}")

    engine = LiveKitEngine()
    room_name = engine.create_room_name(call_id)
    token = engine.generate_token(room_name, identity)

    if not token:
        raise HTTPException(500, "LiveKit not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env")

    # Create call record
    await db.execute(
        text("""
            INSERT INTO calls(id, workspace_id, contact_id, direction, status, provider, consent_given)
            VALUES(:id, :wid, :cid, 'outbound', 'active', 'livekit', true)
            ON CONFLICT(id) DO NOTHING
        """),
        {"id": call_id, "wid": str(current_user.workspace_id), "cid": contact_id}
    )
    await db.commit()

    return {
        "call_id": call_id,
        "room_name": room_name,
        "token": token,
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
    }
```

Add LiveKit .env variables:
```bash
cat >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env" << 'EOF'

# LIVEKIT (self-hosted WebRTC)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
EOF
```

### B3: Browser calling component

Create `apps/web/src/components/BrowserCaller.tsx`:

```typescript
'use client'
import { useState, useEffect, useRef } from 'react'
import { Phone, PhoneOff, Mic, MicOff, Volume2 } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json',
})

interface BrowserCallerProps {
  contactId?: string
  contactName?: string
  onCallEnd?: (callId: string) => void
}

export default function BrowserCaller({ contactId, contactName, onCallEnd }: BrowserCallerProps) {
  const [status, setStatus] = useState<'idle'|'connecting'|'connected'|'ended'>('idle')
  const [muted, setMuted] = useState(false)
  const [callId, setCallId] = useState<string|null>(null)
  const [duration, setDuration] = useState(0)
  const roomRef = useRef<any>(null)
  const timerRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  async function startCall() {
    setStatus('connecting')
    try {
      // Get LiveKit token
      const r = await fetch(`${API}/api/v1/calls/livekit/token`, {
        method: 'POST',
        headers: hdrs(),
        body: JSON.stringify({ contact_id: contactId, identity: 'agent' })
      })
      if (!r.ok) throw new Error('Failed to get call token')
      const { call_id, token, livekit_url, room_name } = await r.json()
      setCallId(call_id)

      // Connect to LiveKit room
      const { Room, RoomEvent } = await import('livekit-client')
      const room = new Room()
      roomRef.current = room

      room.on(RoomEvent.Connected, () => {
        setStatus('connected')
        timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)
      })
      room.on(RoomEvent.Disconnected, () => {
        setStatus('ended')
        if (timerRef.current) clearInterval(timerRef.current)
        if (call_id) onCallEnd?.(call_id)
      })

      await room.connect(livekit_url, token)
      await room.localParticipant.setMicrophoneEnabled(true)

    } catch (e: any) {
      console.error('Call failed:', e)
      setStatus('idle')
      alert(`Call failed: ${e.message}`)
    }
  }

  async function endCall() {
    if (roomRef.current) {
      await roomRef.current.disconnect()
    }
    setStatus('ended')
    if (timerRef.current) clearInterval(timerRef.current)
    if (callId) {
      await fetch(`${API}/api/v1/calls/status-webhook/${callId}`, {
        method: 'POST',
        headers: hdrs(),
        body: JSON.stringify({ call_status: 'completed' })
      })
      onCallEnd?.(callId)
    }
  }

  function toggleMute() {
    if (roomRef.current) {
      const enabled = !muted
      roomRef.current.localParticipant.setMicrophoneEnabled(enabled)
      setMuted(!enabled)
    }
  }

  const formatDuration = (s: number) =>
    `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`

  return (
    <div className="bg-white rounded-xl border p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-medium text-gray-800">
            {contactName || 'Browser Call'}
          </div>
          {status === 'connected' && (
            <div className="text-sm text-green-600 font-mono">{formatDuration(duration)}</div>
          )}
          {status === 'connecting' && (
            <div className="text-sm text-yellow-600 animate-pulse">Connecting...</div>
          )}
          {status === 'ended' && (
            <div className="text-sm text-gray-500">Call ended. Processing transcript...</div>
          )}
        </div>
        <div className="flex gap-2">
          {status === 'connected' && (
            <button onClick={toggleMute}
              className={`p-2 rounded-full ${muted ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'}`}>
              {muted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}
          {status === 'idle' && (
            <button onClick={startCall}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
              <Phone className="w-4 h-4" /> Start Call
            </button>
          )}
          {(status === 'connecting' || status === 'connected') && (
            <button onClick={endCall}
              className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700">
              <PhoneOff className="w-4 h-4" /> End Call
            </button>
          )}
        </div>
      </div>
      {status === 'idle' && (
        <p className="text-xs text-gray-400">
          🔴 This call will be recorded. The other party will be notified.
        </p>
      )}
    </div>
  )
}
```

---

## MODULE C: CONTRIBUTION MARGIN ROAS + KILL/SCALE ENGINE

### C1: Product costs database table

```python
# Add to scripts/create_shared_tables.py or run separately:
import asyncio, asyncpg, os

async def create():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    await conn.execute("""
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
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS campaign_profit_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id UUID REFERENCES ad_campaigns(id),
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

        CREATE INDEX IF NOT EXISTS idx_product_costs_workspace
            ON product_costs(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_profit_analysis_campaign
            ON campaign_profit_analysis(campaign_id, analysis_date DESC);
    """)
    print("✅ Profitability tables created")
    await conn.close()

asyncio.run(create())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 -c "
import asyncio, asyncpg, os
async def f():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS product_costs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL,
            product_name VARCHAR(500),
            sku VARCHAR(255),
            cogs NUMERIC(12,4) NOT NULL DEFAULT 0,
            shipping_cost NUMERIC(12,4) DEFAULT 0,
            return_rate NUMERIC(5,4) DEFAULT 0.05,
            currency VARCHAR(10) DEFAULT \"USD\",
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS campaign_profit_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id UUID REFERENCES ad_campaigns(id),
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
    ''')
    print('Tables created')
    await conn.close()
asyncio.run(f())
"
```

### C2: True Profitability Engine

Create `apps/api/app/services/ad_analytics/profitability_engine.py`:

```python
"""
True Profitability Engine
Calculates real ad profit accounting for COGS, shipping, returns.
Generates kill/scale signals beyond simple ROAS thresholds.
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProductCost:
    cogs: float = 0.0            # Cost of goods sold per unit
    shipping_cost: float = 0.0   # Shipping per order
    return_rate: float = 0.05    # 5% return rate default
    currency: str = "USD"


@dataclass
class TrueProfitAnalysis:
    campaign_id: str
    campaign_name: str
    reported_roas: float
    estimated_true_roas: float
    contribution_margin: float       # (Revenue - COGS - Shipping) / Revenue
    gross_profit: float              # Revenue - all costs - ad spend
    break_even_roas: float          # Minimum ROAS to not lose money
    kill_signal: bool
    scale_signal: bool
    signal_reason: str
    confidence: float               # 0-1 how confident we are
    period_days: int


class ProfitabilityEngine:
    """
    Transforms raw ROAS metrics into true profitability signals.

    Why platform ROAS is misleading:
    - Doesn't account for COGS or shipping
    - Includes organic conversions (especially retargeting)
    - Double-counts across platforms
    - Ignores return rates

    This engine applies contribution margin logic to find real profit.
    """

    # Rule thresholds
    KILL_THRESHOLDS = {
        "roas_below_breakeven": True,     # Below break-even → kill
        "roas_declining_pct": 0.20,       # >20% decline week-over-week → warn
        "cpa_overrun_pct": 0.50,          # CPA >50% above target → warn
        "min_days_before_kill": 5,        # Wait 5 days minimum before killing
        "frequency_fatigue": 7.0,         # Frequency >7 → creative dead
        "budget_waste_utilization": 0.40, # <40% budget used with low ROAS → waste
    }

    SCALE_THRESHOLDS = {
        "min_true_roas_to_scale": 2.5,    # True ROAS must be at least 2.5x breakeven
        "max_frequency_to_scale": 4.0,    # Frequency must be <4
        "min_budget_headroom": 0.15,      # Must have >15% budget headroom
        "roas_improving_pct": 0.10,       # ROAS improving >10% is bullish signal
    }

    def calculate_break_even_roas(self, product_cost: ProductCost,
                                   avg_order_value: float) -> float:
        """
        Minimum ROAS needed to cover all costs.
        break_even = (AOV - COGS - Shipping - Returns) / AOV
        break_even_roas = 1 / contribution_margin
        """
        if avg_order_value <= 0:
            return 3.0  # Conservative default

        net_revenue_per_order = (
            avg_order_value
            - product_cost.cogs
            - product_cost.shipping_cost
            - (avg_order_value * product_cost.return_rate)
        )
        contribution_margin = net_revenue_per_order / avg_order_value

        if contribution_margin <= 0:
            return 10.0  # Very high break-even if margins are negative

        # Break-even ROAS = 1 / contribution_margin
        # e.g., 40% margin → need 2.5x ROAS to break even
        return round(1.0 / contribution_margin, 2)

    def calculate_true_roas(self, reported_roas: float,
                             product_cost: ProductCost,
                             avg_order_value: float,
                             is_retargeting: bool = False) -> float:
        """
        Estimate true incremental ROAS from reported ROAS.

        Adjustments applied:
        1. Retargeting discount: ~40-60% of retargeting conversions are organic
        2. Contribution margin: only profitable revenue counts
        3. Return rate adjustment
        """
        if avg_order_value <= 0 or reported_roas <= 0:
            return 0.0

        adjusted_roas = reported_roas

        # Retargeting discount (industry average: 50-75% organic)
        if is_retargeting:
            adjusted_roas *= 0.35  # Conservative: assume 65% would convert organically

        # Contribution margin adjustment
        net_per_order = (
            avg_order_value
            - product_cost.cogs
            - product_cost.shipping_cost
            - (avg_order_value * product_cost.return_rate)
        )
        margin = net_per_order / avg_order_value if avg_order_value > 0 else 0

        true_roas = adjusted_roas * margin
        return round(max(true_roas, 0), 3)

    def analyze_campaign(
        self,
        campaign_id: str,
        campaign_name: str,
        metrics_7d: dict,
        metrics_prev_7d: dict,
        product_cost: ProductCost,
        avg_order_value: float,
        target_cpa: Optional[float] = None,
        is_retargeting: bool = False,
        days_active: int = 14
    ) -> TrueProfitAnalysis:
        """
        Full profitability analysis for a campaign.

        metrics_7d: {roas, spend, revenue, conversions, ctr, frequency, budget_utilization}
        """
        reported_roas = float(metrics_7d.get("roas", 0))
        spend = float(metrics_7d.get("spend", 0))
        revenue = float(metrics_7d.get("revenue", 0))
        conversions = float(metrics_7d.get("conversions", 0))
        frequency = float(metrics_7d.get("frequency", 0))
        budget_util = float(metrics_7d.get("budget_utilization", 0.8))

        prev_roas = float(metrics_prev_7d.get("roas", reported_roas))
        roas_trend = ((reported_roas - prev_roas) / prev_roas
                      if prev_roas > 0 else 0)

        # Calculate break-even
        break_even = self.calculate_break_even_roas(product_cost, avg_order_value)

        # Calculate true ROAS
        true_roas = self.calculate_true_roas(
            reported_roas, product_cost, avg_order_value, is_retargeting
        )

        # Contribution margin
        net_rev = (
            revenue
            - (conversions * product_cost.cogs)
            - (conversions * product_cost.shipping_cost)
            - (revenue * product_cost.return_rate)
        )
        contrib_margin = net_rev / revenue if revenue > 0 else 0
        gross_profit = net_rev - spend

        # Kill signals
        kill = False
        scale = False
        reasons = []

        if days_active >= self.KILL_THRESHOLDS["min_days_before_kill"]:
            if true_roas < break_even and true_roas > 0:
                kill = True
                reasons.append(
                    f"True ROAS {true_roas:.2f}x below break-even {break_even:.2f}x"
                )
            elif reported_roas < break_even * 0.8:
                kill = True
                reasons.append(
                    f"Reported ROAS {reported_roas:.2f}x critically low"
                )

        if frequency > self.KILL_THRESHOLDS["frequency_fatigue"]:
            reasons.append(
                f"Creative fatigue: frequency {frequency:.1f}x (limit: 7.0)"
            )
            if kill is False:
                kill = True  # Fatigue alone triggers kill recommendation

        if roas_trend <= -self.KILL_THRESHOLDS["roas_declining_pct"]:
            reasons.append(
                f"ROAS declining {abs(roas_trend)*100:.0f}% week-over-week"
            )

        # Scale signals
        if (true_roas >= break_even * self.SCALE_THRESHOLDS["min_true_roas_to_scale"]
                and frequency < self.SCALE_THRESHOLDS["max_frequency_to_scale"]
                and budget_util < (1 - self.SCALE_THRESHOLDS["min_budget_headroom"])
                and not kill):
            scale = True
            reasons.append(
                f"True ROAS {true_roas:.2f}x ({self.SCALE_THRESHOLDS['min_true_roas_to_scale']}x break-even), "
                f"frequency {frequency:.1f}x, budget headroom available"
            )
        elif (roas_trend >= self.SCALE_THRESHOLDS["roas_improving_pct"]
              and reported_roas > break_even
              and not kill):
            reasons.append(
                f"Improving trend +{roas_trend*100:.0f}% WoW with profitable ROAS"
            )

        # Confidence scoring
        confidence = 0.5
        if days_active >= 14:
            confidence += 0.2
        if conversions >= 10:
            confidence += 0.2
        if spend >= 100:
            confidence += 0.1
        confidence = min(confidence, 0.95)

        return TrueProfitAnalysis(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            reported_roas=round(reported_roas, 3),
            estimated_true_roas=true_roas,
            contribution_margin=round(contrib_margin, 4),
            gross_profit=round(gross_profit, 2),
            break_even_roas=break_even,
            kill_signal=kill,
            scale_signal=scale,
            signal_reason="; ".join(reasons) if reasons else "No significant signal",
            confidence=round(confidence, 3),
            period_days=7
        )

    def analyze_portfolio(
        self,
        campaigns: list[dict],
        product_cost: ProductCost,
        avg_order_value: float,
        total_budget: float
    ) -> dict:
        """
        Portfolio-level analysis: redistribute budget from losers to winners.
        Returns recommended budget allocation.
        """
        analyses = []
        for camp in campaigns:
            analysis = self.analyze_campaign(
                campaign_id=camp["id"],
                campaign_name=camp["name"],
                metrics_7d=camp,
                metrics_prev_7d=camp.get("prev", {}),
                product_cost=product_cost,
                avg_order_value=avg_order_value,
                is_retargeting="retarget" in camp.get("name","").lower()
            )
            analyses.append((camp, analysis))

        # Winners: scale signals, no kill signal
        winners = [(c, a) for c, a in analyses if a.scale_signal and not a.kill_signal]
        # Losers: kill signals
        losers = [(c, a) for c, a in analyses if a.kill_signal]
        # Neutral
        neutral = [(c, a) for c, a in analyses
                   if not a.scale_signal and not a.kill_signal]

        # Budget freed from losers
        loser_budget = sum(float(c.get("spend", 0)) for c, _ in losers)

        # Reallocate to winners proportionally
        allocation = {}
        winner_roas_sum = sum(a.estimated_true_roas for _, a in winners) or 1
        for camp, analysis in analyses:
            if analysis.kill_signal:
                allocation[camp["id"]] = 0  # Kill → 0 budget
            elif analysis.scale_signal:
                # Give proportional share of reallocated budget
                extra = (loser_budget *
                         (analysis.estimated_true_roas / winner_roas_sum))
                current = float(camp.get("spend", 0))
                allocation[camp["id"]] = round(current + extra, 2)
            else:
                allocation[camp["id"]] = float(camp.get("spend", 0))

        return {
            "winners": [(c["name"], a.estimated_true_roas) for c, a in winners],
            "losers": [(c["name"], a.signal_reason) for c, a in losers],
            "budget_freed": round(loser_budget, 2),
            "recommended_allocation": allocation,
            "analyses": [
                {
                    "campaign_id": a.campaign_id,
                    "campaign_name": a.campaign_name,
                    "reported_roas": a.reported_roas,
                    "true_roas": a.estimated_true_roas,
                    "break_even_roas": a.break_even_roas,
                    "gross_profit": a.gross_profit,
                    "contribution_margin": a.contribution_margin,
                    "kill": a.kill_signal,
                    "scale": a.scale_signal,
                    "reason": a.signal_reason,
                    "confidence": a.confidence
                }
                for _, a in analyses
            ]
        }
```

### C3: Profitability API Endpoints

Add to `apps/api/app/api/endpoints/ad_analytics.py`:

```python
@router.get("/profitability/settings")
async def get_profitability_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get product cost settings for true ROAS calculation."""
    r = await db.execute(
        text("SELECT * FROM product_costs WHERE workspace_id=:wid AND is_default=true LIMIT 1"),
        {"wid": str(current_user.workspace_id)}
    )
    row = r.fetchone()
    if row:
        return {"settings": dict(row._mapping)}
    return {"settings": {"cogs": 0, "shipping_cost": 0, "return_rate": 0.05,
                         "avg_order_value": 0, "currency": "USD"}}


@router.post("/profitability/settings")
async def save_profitability_settings(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save product cost settings for true ROAS calculation."""
    await db.execute(
        text("UPDATE product_costs SET is_default=false WHERE workspace_id=:wid"),
        {"wid": str(current_user.workspace_id)}
    )
    await db.execute(
        text("""
            INSERT INTO product_costs
                (workspace_id, cogs, shipping_cost, return_rate, is_default, currency)
            VALUES (:wid, :cogs, :ship, :ret, true, :curr)
        """),
        {
            "wid": str(current_user.workspace_id),
            "cogs": data.get("cogs", 0),
            "ship": data.get("shipping_cost", 0),
            "ret": data.get("return_rate", 0.05),
            "curr": data.get("currency", "USD")
        }
    )
    await db.commit()
    return {"success": True}


@router.get("/profitability/analysis")
async def get_profitability_analysis(
    account_id: Optional[str] = None,
    avg_order_value: float = 50.0,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run true profitability analysis on all campaigns.
    Returns kill/scale signals with contribution margin data.
    """
    from app.services.ad_analytics.profitability_engine import (
        ProfitabilityEngine, ProductCost
    )

    wid = str(current_user.workspace_id)

    # Get product costs
    cost_r = await db.execute(
        text("SELECT * FROM product_costs WHERE workspace_id=:wid AND is_default=true LIMIT 1"),
        {"wid": wid}
    )
    cost_row = cost_r.fetchone()
    if cost_row:
        cost_row = dict(cost_row._mapping)
        product_cost = ProductCost(
            cogs=float(cost_row.get("cogs", 0)),
            shipping_cost=float(cost_row.get("shipping_cost", 0)),
            return_rate=float(cost_row.get("return_rate", 0.05))
        )
    else:
        product_cost = ProductCost()

    # Get campaigns with recent performance
    camp_r = await db.execute(
        text("""
            SELECT
                c.id, c.name, c.platform,
                AVG(p.roas) as roas,
                AVG(p.cpa) as cpa,
                SUM(p.spend) as spend,
                SUM(p.revenue) as revenue,
                SUM(p.conversions) as conversions,
                AVG(p.frequency) as frequency,
                COUNT(p.date) as days_active
            FROM ad_campaigns c
            JOIN ad_performance_daily p ON p.campaign_id = c.id
            JOIN ad_accounts a ON a.id = c.ad_account_id
            WHERE a.workspace_id = :wid
            AND p.date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY c.id, c.name, c.platform
            HAVING SUM(p.spend) > 0
        """),
        {"wid": wid}
    )
    campaigns = [dict(r._mapping) for r in camp_r.fetchall()]

    if not campaigns:
        return {"message": "No campaign data available", "analyses": []}

    engine = ProfitabilityEngine()
    results = []

    for camp in campaigns:
        analysis = engine.analyze_campaign(
            campaign_id=str(camp["id"]),
            campaign_name=camp["name"],
            metrics_7d={
                "roas": float(camp["roas"] or 0),
                "spend": float(camp["spend"] or 0),
                "revenue": float(camp["revenue"] or 0),
                "conversions": float(camp["conversions"] or 0),
                "frequency": float(camp["frequency"] or 0),
                "budget_utilization": 0.8
            },
            metrics_prev_7d={},
            product_cost=product_cost,
            avg_order_value=avg_order_value,
            is_retargeting="retarget" in (camp["name"] or "").lower(),
            days_active=int(camp["days_active"] or 0)
        )

        results.append({
            "campaign_id": str(camp["id"]),
            "campaign_name": camp["name"],
            "platform": camp["platform"],
            "reported_roas": analysis.reported_roas,
            "true_roas": analysis.estimated_true_roas,
            "break_even_roas": analysis.break_even_roas,
            "contribution_margin_pct": round(analysis.contribution_margin * 100, 1),
            "gross_profit": analysis.gross_profit,
            "kill_signal": analysis.kill_signal,
            "scale_signal": analysis.scale_signal,
            "signal_reason": analysis.signal_reason,
            "confidence": analysis.confidence
        })

    # Summary
    kills = [r for r in results if r["kill_signal"]]
    scales = [r for r in results if r["scale_signal"]]
    total_waste = sum(
        float(c["spend"]) for c in campaigns
        if any(r["campaign_id"] == str(c["id"]) and r["kill_signal"] for r in results)
    )

    return {
        "analyses": results,
        "summary": {
            "kill_campaigns": len(kills),
            "scale_campaigns": len(scales),
            "estimated_weekly_waste": round(total_waste, 2),
            "product_cost_configured": cost_row is not None
        },
        "note": "True ROAS estimates apply contribution margin and retargeting discount. Configure product costs for accuracy."
    }
```

### C4: Profitability Frontend Page

Create `apps/web/src/app/dashboard/ads/profitability/page.tsx`:

```typescript
'use client'
import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, DollarSign, AlertCircle, Settings, Zap } from 'lucide-react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json',
})

export default function ProfitabilityDashboard() {
  const [analyses, setAnalyses] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [settings, setSettings] = useState({ cogs: 0, shipping_cost: 0, return_rate: 5, avg_order_value: 50 })
  const [showSettings, setShowSettings] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadAll() }, [])

  async function loadAll() {
    setLoading(true)
    const [ar, sr] = await Promise.all([
      fetch(`${API}/api/v1/ads/profitability/analysis?avg_order_value=${settings.avg_order_value}`, { headers: hdrs() }),
      fetch(`${API}/api/v1/ads/profitability/settings`, { headers: hdrs() }),
    ])
    if (ar.ok) {
      const d = await ar.json()
      setAnalyses(d.analyses || [])
      setSummary(d.summary)
    }
    if (sr.ok) {
      const d = await sr.json()
      if (d.settings) {
        setSettings(prev => ({
          ...prev,
          cogs: d.settings.cogs || 0,
          shipping_cost: d.settings.shipping_cost || 0,
          return_rate: (d.settings.return_rate || 0.05) * 100
        }))
      }
    }
    setLoading(false)
  }

  async function saveSettings() {
    setSaving(true)
    await fetch(`${API}/api/v1/ads/profitability/settings`, {
      method: 'POST', headers: hdrs(),
      body: JSON.stringify({
        cogs: settings.cogs,
        shipping_cost: settings.shipping_cost,
        return_rate: settings.return_rate / 100,
        currency: 'USD'
      })
    })
    setSaving(false)
    setShowSettings(false)
    loadAll()
  }

  const kills = analyses.filter(a => a.kill_signal)
  const scales = analyses.filter(a => a.scale_signal)
  const neutral = analyses.filter(a => !a.kill_signal && !a.scale_signal)

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">True Profitability Analysis</h1>
          <p className="text-sm text-gray-500 mt-1">Real ad profit accounting for COGS, shipping, and returns</p>
        </div>
        <button onClick={() => setShowSettings(!showSettings)}
          className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
          <Settings className="w-4 h-4" /> Product Costs
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-white rounded-xl border p-5 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Product Cost Settings</h3>
          <p className="text-sm text-gray-500">
            These values are used to calculate true profitability. Without them, only ROAS thresholds are used.
          </p>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Avg Order Value ($)', key: 'avg_order_value', placeholder: '50' },
              { label: 'COGS per unit ($)', key: 'cogs', placeholder: '15' },
              { label: 'Shipping per order ($)', key: 'shipping_cost', placeholder: '5' },
              { label: 'Return rate (%)', key: 'return_rate', placeholder: '5' },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-sm text-gray-600 mb-1">{label}</label>
                <input
                  type="number" step="0.01"
                  value={settings[key as keyof typeof settings]}
                  onChange={e => setSettings(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                  placeholder={placeholder}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
          <button onClick={saveSettings} disabled={saving}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save & Recalculate'}
          </button>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Kill Signals', val: summary.kill_campaigns, color: 'text-red-600', bg: 'bg-red-50', icon: TrendingDown },
            { label: 'Scale Signals', val: summary.scale_campaigns, color: 'text-green-600', bg: 'bg-green-50', icon: TrendingUp },
            { label: 'Est. Weekly Waste', val: `$${summary.estimated_weekly_waste?.toLocaleString()}`, color: 'text-red-600', bg: 'bg-red-50', icon: DollarSign },
            { label: 'Total Campaigns', val: analyses.length, color: 'text-gray-700', bg: 'bg-gray-50', icon: Zap },
          ].map(k => (
            <div key={k.label} className={`${k.bg} rounded-xl border p-4`}>
              <div className={`flex items-center gap-2 text-sm mb-1 ${k.color}`}>
                <k.icon className="w-4 h-4" /> {k.label}
              </div>
              <div className={`text-2xl font-bold ${k.color}`}>{k.val}</div>
            </div>
          ))}
        </div>
      )}

      {!summary?.product_cost_configured && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600" />
          <div className="text-sm text-yellow-800">
            <strong>Product costs not configured.</strong> Set COGS and shipping above for true profitability analysis.
            Without it, only ROAS thresholds are used.
          </div>
        </div>
      )}

      {/* Kill Signals */}
      {kills.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-red-700 flex items-center gap-2">
            <TrendingDown className="w-5 h-5" /> Kill Signals ({kills.length})
          </h2>
          {kills.map(a => (
            <div key={a.campaign_id} className="bg-red-50 border border-red-200 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-red-800">{a.campaign_name}</div>
                  <div className="text-sm text-red-600 mt-1">{a.signal_reason}</div>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span className="text-gray-600">Reported: <strong>{a.reported_roas?.toFixed(2)}x</strong></span>
                    <span className="text-red-700">True: <strong>{a.true_roas?.toFixed(2)}x</strong></span>
                    <span className="text-gray-600">Break-even: <strong>{a.break_even_roas?.toFixed(2)}x</strong></span>
                    <span className="text-red-700">Profit: <strong>${a.gross_profit?.toFixed(0)}</strong></span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0 ml-4">
                  <div className="text-xs text-gray-400 mb-1">Confidence</div>
                  <div className="text-sm font-medium text-gray-600">{(a.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Scale Signals */}
      {scales.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-green-700 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" /> Scale Signals ({scales.length})
          </h2>
          {scales.map(a => (
            <div key={a.campaign_id} className="bg-green-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-green-800">{a.campaign_name}</div>
                  <div className="text-sm text-green-600 mt-1">{a.signal_reason}</div>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span className="text-gray-600">Reported: <strong>{a.reported_roas?.toFixed(2)}x</strong></span>
                    <span className="text-green-700">True: <strong>{a.true_roas?.toFixed(2)}x</strong></span>
                    <span className="text-gray-600">Margin: <strong>{a.contribution_margin_pct?.toFixed(0)}%</strong></span>
                    <span className="text-green-700">Profit: <strong>${a.gross_profit?.toFixed(0)}</strong></span>
                  </div>
                </div>
                <div className="text-xs text-gray-400 ml-4">{(a.confidence * 100).toFixed(0)}% confident</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Neutral / Watch */}
      {neutral.length > 0 && (
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Monitoring ({neutral.length})</h2>
          </div>
          <div className="divide-y">
            {neutral.map(a => (
              <div key={a.campaign_id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-800">{a.campaign_name}</div>
                  <div className="text-sm text-gray-500">{a.signal_reason}</div>
                </div>
                <div className="flex gap-4 text-sm text-right">
                  <div>
                    <div className="text-gray-400 text-xs">True ROAS</div>
                    <div className="font-bold text-gray-700">{a.true_roas?.toFixed(2)}x</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">Profit/wk</div>
                    <div className={`font-bold ${a.gross_profit >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                      ${a.gross_profit?.toFixed(0)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

Add to ad analytics sidebar: `{ label: 'True Profitability', href: '/dashboard/ads/profitability', icon: DollarSign }`

---

## MODULE D: COMPANY INTELLIGENCE — ADAPTIVE AI DISCOVERY PANEL

### D1: Database tables for company intelligence

```bash
python3 -c "
import asyncio, asyncpg, os
async def f():
    url = os.getenv('DATABASE_URL','').replace('+asyncpg','')
    conn = await asyncpg.connect(url)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS company_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL UNIQUE,
            company_name TEXT,
            industry TEXT,
            stage TEXT,
            business_model TEXT,
            primary_goal TEXT,
            biggest_challenge TEXT,
            success_metric TEXT,
            target_customer TEXT,
            avg_order_value NUMERIC(12,2),
            customer_ltv NUMERIC(12,2),
            monthly_ad_spend NUMERIC(12,2),
            current_roas NUMERIC(10,4),
            break_even_roas NUMERIC(10,4),
            active_channels TEXT[],
            ai_summary TEXT,
            ai_insights TEXT[],
            discovery_transcript JSONB DEFAULT \"[]\"::jsonb,
            discovery_completed BOOLEAN DEFAULT FALSE,
            discovery_completed_at TIMESTAMPTZ,
            question_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_company_profiles_workspace
            ON company_profiles(workspace_id);
    ''')
    print('Tables created')
    await conn.close()
asyncio.run(f())
"
```

### D2: Adaptive Discovery Engine

Create `apps/api/app/services/discovery/discovery_engine.py`:

```python
"""
Adaptive AI Company Discovery Engine
Conducts a 30-minute intelligent interview to deeply understand the company.
Questions adapt based on previous answers using local Ollama.
"""
import logging
import json
from typing import Optional
from app.services.ai.model_config import call_ollama, call_ollama_json, TaskType

logger = logging.getLogger(__name__)

DISCOVERY_SYSTEM = """You are an elite business strategist and growth consultant.
Your role: conduct a deep discovery interview to understand this company thoroughly.

Rules:
1. Ask ONE focused question at a time
2. Each question must build on previous answers
3. Adapt to the company type, industry, and stage
4. Go from broad to specific as you learn more
5. Cover: business model, customers, revenue, marketing, goals, challenges
6. Be conversational, not robotic
7. If an answer is vague, ask a clarifying follow-up
8. Signal [COMPLETE] when you have enough for a comprehensive profile (usually 12-20 questions)
9. Never ask the same topic twice
10. Industry-specific: use relevant terminology and context

Tone: Professional but warm. Like a senior consultant in a strategy session."""

FIRST_QUESTIONS_BY_CONTEXT = {
    "default": "Tell me about your business — what do you do and who do you serve?",
    "ecommerce": "What products do you sell, and what makes your offering different in the market?",
    "saas": "What problem does your software solve, and who is your primary user?",
    "agency": "What services do you offer, and what types of clients do you work with?",
    "local": "What's your business, where are you located, and who are your typical customers?",
}


class DiscoveryEngine:
    """
    Manages an adaptive company discovery conversation.
    Uses Ollama to generate intelligent follow-up questions.
    """

    def get_opening_question(self, business_type: Optional[str] = None) -> str:
        if business_type and business_type in FIRST_QUESTIONS_BY_CONTEXT:
            return FIRST_QUESTIONS_BY_CONTEXT[business_type]
        return FIRST_QUESTIONS_BY_CONTEXT["default"]

    def generate_next_question(
        self,
        transcript: list[dict],
        company_knowledge: dict
    ) -> str:
        """
        Generate the next question based on conversation history.
        Returns [COMPLETE] if enough information gathered.
        """
        q_count = len([t for t in transcript if t.get("role") == "assistant"])

        if q_count >= 20:
            return "[COMPLETE]"

        # Build conversation context
        conv_text = "\n".join([
            f"{t['role'].upper()}: {t['content']}"
            for t in transcript[-10:]  # Last 10 exchanges
        ])

        known = json.dumps(company_knowledge, indent=2)

        prompt = f"""You are conducting a company discovery interview.

CONVERSATION SO FAR (last 10 exchanges):
{conv_text}

WHAT WE KNOW SO FAR:
{known}

QUESTION COUNT: {q_count} of maximum 20

Based on the conversation, what is the single most important question to ask next?

Rules:
- If we have enough for a comprehensive business profile (after 12+ questions), respond with exactly: [COMPLETE]
- Otherwise, ask ONE specific question that will reveal important new information
- Do NOT ask about anything already clearly answered above
- Make it feel natural and conversational
- If the previous answer was vague, ask for clarification on that specific point first

Respond with ONLY the question (or [COMPLETE]). Nothing else."""

        response = call_ollama(
            prompt=prompt,
            task=TaskType.MULTILINGUAL,
            max_tokens=150,
            temperature=0.4,
            system=DISCOVERY_SYSTEM,
            timeout=90
        )

        return response.strip()

    def extract_company_knowledge(self, transcript: list[dict]) -> dict:
        """
        Extract structured company profile from conversation.
        """
        conv_text = "\n".join([
            f"{t['role'].upper()}: {t['content']}"
            for t in transcript
        ])

        schema = {
            "company_name": "Acme Corp",
            "industry": "E-commerce",
            "stage": "growth",
            "business_model": "B2C DTC",
            "primary_goal": "Scale revenue 3x in 12 months",
            "biggest_challenge": "Rising CAC and attribution problems",
            "success_metric": "ROAS and profitable growth",
            "target_customer": "25-45 year old professionals",
            "avg_order_value": 85,
            "customer_ltv": 250,
            "monthly_ad_spend": 15000,
            "current_roas": 3.2,
            "break_even_roas": 2.5,
            "active_channels": ["Meta", "Google", "Email"],
            "key_insights": ["Price sensitive market", "High repeat purchase rate"],
            "recommendations": ["Focus on LTV over CAC", "Test incrementality"]
        }

        prompt = f"""Extract a structured company profile from this discovery conversation.

FULL CONVERSATION:
{conv_text}

Extract all available information. Use null for anything not mentioned.
For break_even_roas: estimate from margins if mentioned (e.g., 40% margin → 2.5x break-even).
For key_insights: list 3-5 important observations about their business.
For recommendations: suggest 2-3 specific actions based on what you learned."""

        result = call_ollama_json(
            prompt=prompt,
            schema_example=schema,
            task=TaskType.REASONING,
            timeout=120
        )

        return result

    def generate_company_summary(self, knowledge: dict, transcript: list[dict]) -> str:
        """Generate a comprehensive AI summary of the company."""
        prompt = f"""Write a comprehensive 3-paragraph business intelligence summary.

COMPANY PROFILE:
{json.dumps(knowledge, indent=2)}

Write:
1. Company overview (what they do, who they serve, their market position)
2. Current situation (challenges, goals, metrics, marketing approach)
3. Strategic recommendations (3 specific, actionable priorities)

Be specific, insightful, and business-focused. No generic advice."""

        return call_ollama(
            prompt=prompt,
            task=TaskType.REASONING,
            max_tokens=500,
            temperature=0.3,
            timeout=120
        )
```

### D3: Discovery API Endpoints

Create `apps/api/app/api/endpoints/discovery.py`:

```python
"""Company Intelligence Discovery — Adaptive AI Interview."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.discovery.discovery_engine import DiscoveryEngine

router = APIRouter(prefix="/api/v1/discovery", tags=["Discovery"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_discovery_status(current_user=Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    """Get current discovery status for this workspace."""
    r = await db.execute(
        text("SELECT * FROM company_profiles WHERE workspace_id=:wid"),
        {"wid": str(current_user.workspace_id)}
    )
    row = r.fetchone()
    if not row:
        return {"status": "not_started", "profile": None, "question_count": 0}
    profile = dict(row._mapping)
    return {
        "status": "completed" if profile.get("discovery_completed") else "in_progress",
        "profile": profile,
        "question_count": profile.get("question_count", 0)
    }


@router.post("/start")
async def start_discovery(data: dict = {},
                           current_user=Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    """Start or restart the discovery process."""
    engine = DiscoveryEngine()
    first_question = engine.get_opening_question(data.get("business_type"))

    # Create or reset profile
    await db.execute(
        text("""
            INSERT INTO company_profiles
                (workspace_id, discovery_transcript, discovery_completed, question_count)
            VALUES (:wid, :transcript::jsonb, false, 0)
            ON CONFLICT(workspace_id) DO UPDATE SET
                discovery_transcript = :transcript::jsonb,
                discovery_completed = false,
                question_count = 0,
                updated_at = NOW()
        """),
        {
            "wid": str(current_user.workspace_id),
            "transcript": json.dumps([{
                "role": "assistant",
                "content": first_question,
                "type": "question"
            }])
        }
    )
    await db.commit()
    return {"question": first_question, "question_number": 1}


@router.post("/answer")
async def submit_answer(data: dict,  # {"answer": "..."}
                         current_user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Submit an answer and get the next question."""
    answer = data.get("answer", "").strip()
    if not answer:
        raise HTTPException(400, "Answer cannot be empty")

    # Get current transcript
    r = await db.execute(
        text("SELECT discovery_transcript, question_count FROM company_profiles WHERE workspace_id=:wid"),
        {"wid": str(current_user.workspace_id)}
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Discovery not started. Call /start first.")

    transcript = row.discovery_transcript or []
    if not isinstance(transcript, list):
        transcript = []

    # Add user answer
    transcript.append({"role": "user", "content": answer, "type": "answer"})

    # Extract current knowledge
    engine = DiscoveryEngine()
    knowledge = engine.extract_company_knowledge(transcript)

    # Generate next question
    next_question = engine.generate_next_question(transcript, knowledge)
    completed = next_question == "[COMPLETE]"

    if not completed:
        transcript.append({
            "role": "assistant",
            "content": next_question,
            "type": "question"
        })

    q_count = len([t for t in transcript if t.get("role") == "assistant"])

    # Update profile
    if completed:
        summary = engine.generate_company_summary(knowledge, transcript)
        await db.execute(
            text("""
                UPDATE company_profiles SET
                    discovery_transcript = :transcript::jsonb,
                    discovery_completed = true,
                    discovery_completed_at = NOW(),
                    question_count = :qc,
                    ai_summary = :summary,
                    company_name = :company_name,
                    industry = :industry,
                    stage = :stage,
                    business_model = :bm,
                    primary_goal = :goal,
                    biggest_challenge = :challenge,
                    target_customer = :customer,
                    avg_order_value = :aov,
                    monthly_ad_spend = :spend,
                    current_roas = :roas,
                    break_even_roas = :be_roas,
                    active_channels = :channels,
                    updated_at = NOW()
                WHERE workspace_id = :wid
            """),
            {
                "wid": str(current_user.workspace_id),
                "transcript": json.dumps(transcript),
                "qc": q_count,
                "summary": summary,
                "company_name": knowledge.get("company_name"),
                "industry": knowledge.get("industry"),
                "stage": knowledge.get("stage"),
                "bm": knowledge.get("business_model"),
                "goal": knowledge.get("primary_goal"),
                "challenge": knowledge.get("biggest_challenge"),
                "customer": knowledge.get("target_customer"),
                "aov": knowledge.get("avg_order_value"),
                "spend": knowledge.get("monthly_ad_spend"),
                "roas": knowledge.get("current_roas"),
                "be_roas": knowledge.get("break_even_roas"),
                "channels": knowledge.get("active_channels", []),
            }
        )
    else:
        await db.execute(
            text("""
                UPDATE company_profiles SET
                    discovery_transcript = :transcript::jsonb,
                    question_count = :qc,
                    updated_at = NOW()
                WHERE workspace_id = :wid
            """),
            {
                "wid": str(current_user.workspace_id),
                "transcript": json.dumps(transcript),
                "qc": q_count
            }
        )
    await db.commit()

    return {
        "completed": completed,
        "next_question": next_question if not completed else None,
        "question_number": q_count,
        "profile": knowledge if completed else None,
        "summary": summary if completed else None
    }


@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Get the completed company profile."""
    r = await db.execute(
        text("SELECT * FROM company_profiles WHERE workspace_id=:wid"),
        {"wid": str(current_user.workspace_id)}
    )
    row = r.fetchone()
    if not row:
        return {"profile": None}
    return {"profile": dict(row._mapping)}
```

Register in main.py:
```python
from app.api.endpoints.discovery import router as discovery_router
app.include_router(discovery_router)
```

### D4: Company Intelligence Frontend

Create `apps/web/src/app/dashboard/company-intelligence/page.tsx`:

```typescript
'use client'
import { useState, useEffect, useRef } from 'react'
import { Brain, ChevronRight, CheckCircle, Building2, RefreshCw } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const hdrs = () => ({
  Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}`,
  'Content-Type': 'application/json',
})

export default function CompanyIntelligence() {
  const [status, setStatus] = useState<'not_started'|'in_progress'|'completed'>('not_started')
  const [question, setQuestion] = useState('')
  const [questionNumber, setQuestionNumber] = useState(0)
  const [answer, setAnswer] = useState('')
  const [profile, setProfile] = useState<any>(null)
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [transcript, setTranscript] = useState<{role:string,content:string}[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { loadStatus() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [transcript])

  async function loadStatus() {
    setLoading(true)
    const r = await fetch(`${API}/api/v1/discovery/status`, { headers: hdrs() })
    if (r.ok) {
      const d = await r.json()
      setStatus(d.status)
      if (d.profile) {
        setProfile(d.profile)
        if (d.profile.ai_summary) setSummary(d.profile.ai_summary)
        const t = d.profile.discovery_transcript || []
        setTranscript(t)
        if (d.status === 'in_progress') {
          const lastQ = t.filter((x: any) => x.role === 'assistant').slice(-1)[0]
          if (lastQ) setQuestion(lastQ.content)
          setQuestionNumber(d.question_count || 0)
        }
      }
    }
    setLoading(false)
  }

  async function startDiscovery() {
    setLoading(true)
    const r = await fetch(`${API}/api/v1/discovery/start`, {
      method: 'POST', headers: hdrs(), body: JSON.stringify({})
    })
    if (r.ok) {
      const d = await r.json()
      setStatus('in_progress')
      setQuestion(d.question)
      setQuestionNumber(1)
      setTranscript([{ role: 'assistant', content: d.question }])
    }
    setLoading(false)
  }

  async function submitAnswer() {
    if (!answer.trim()) return
    setSubmitting(true)
    const userMsg = { role: 'user', content: answer }
    setTranscript(prev => [...prev, userMsg])
    const submitted = answer
    setAnswer('')

    const r = await fetch(`${API}/api/v1/discovery/answer`, {
      method: 'POST', headers: hdrs(),
      body: JSON.stringify({ answer: submitted })
    })
    if (r.ok) {
      const d = await r.json()
      if (d.completed) {
        setStatus('completed')
        setProfile(d.profile)
        setSummary(d.summary || '')
      } else {
        setQuestion(d.next_question)
        setQuestionNumber(d.question_number)
        setTranscript(prev => [...prev, { role: 'assistant', content: d.next_question }])
      }
    }
    setSubmitting(false)
  }

  if (loading) return (
    <div className="p-6 flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Company Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-powered discovery — helps personalize all platform recommendations
          </p>
        </div>
        {status === 'completed' && (
          <button onClick={startDiscovery}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
            <RefreshCw className="w-4 h-4" /> Redo Discovery
          </button>
        )}
      </div>

      {/* Not Started */}
      {status === 'not_started' && (
        <div className="bg-white rounded-2xl border p-8 text-center shadow-sm">
          <Brain className="w-16 h-16 text-indigo-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Start Company Discovery
          </h2>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">
            Our AI will ask you 12-20 adaptive questions to deeply understand your business.
            This takes about 15-30 minutes and personalizes all platform recommendations.
          </p>
          <div className="grid grid-cols-3 gap-4 mb-8 text-sm text-gray-600">
            {['Adaptive questions based on your answers',
              'Builds your complete company profile',
              'Personalizes ads, email & AI recommendations'].map((item, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                {item}
              </div>
            ))}
          </div>
          <button onClick={startDiscovery} disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-xl
              font-medium hover:bg-indigo-700 mx-auto">
            <Brain className="w-5 h-5" /> Begin Discovery
          </button>
        </div>
      )}

      {/* In Progress */}
      {status === 'in_progress' && (
        <div className="space-y-4">
          {/* Progress */}
          <div className="bg-white rounded-xl border p-3 flex items-center gap-3">
            <div className="text-sm text-gray-500">Question {questionNumber} of ~15</div>
            <div className="flex-1 bg-gray-100 rounded-full h-2">
              <div className="bg-indigo-500 h-2 rounded-full transition-all"
                   style={{width:`${Math.min((questionNumber/15)*100, 95)}%`}} />
            </div>
            <div className="text-sm text-gray-400">{Math.round((questionNumber/15)*100)}%</div>
          </div>

          {/* Conversation */}
          <div className="bg-white rounded-xl border shadow-sm">
            <div className="p-4 border-b bg-gray-50 rounded-t-xl">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-indigo-600" />
                <span className="font-medium text-gray-800">AI Consultant</span>
              </div>
            </div>
            <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
              {transcript.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {submitting && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-xl px-4 py-3">
                    <div className="flex gap-1">
                      {[0,1,2].map(i => (
                        <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                             style={{animationDelay:`${i*0.1}s`}} />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <div className="p-4 border-t">
              <div className="flex gap-3">
                <textarea
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitAnswer() } }}
                  placeholder="Type your answer... (Enter to submit)"
                  rows={3}
                  className="flex-1 border rounded-xl px-4 py-3 text-sm resize-none focus:ring-2 focus:ring-indigo-300"
                />
                <button onClick={submitAnswer} disabled={submitting || !answer.trim()}
                  className="bg-indigo-600 text-white px-4 py-3 rounded-xl hover:bg-indigo-700
                    disabled:opacity-50 flex items-center gap-2 text-sm font-medium">
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Completed */}
      {status === 'completed' && profile && (
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <p className="text-green-800 font-medium">
              Discovery complete! Platform is now personalized for {profile.company_name || 'your company'}.
            </p>
          </div>

          {/* Summary */}
          {summary && (
            <div className="bg-white rounded-xl border p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-indigo-600" />
                <h3 className="font-semibold text-gray-800">AI Business Summary</h3>
              </div>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line text-sm">{summary}</p>
            </div>
          )}

          {/* Profile Grid */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Industry', value: profile.industry },
              { label: 'Stage', value: profile.stage },
              { label: 'Business Model', value: profile.business_model },
              { label: 'Primary Goal', value: profile.primary_goal },
              { label: 'Biggest Challenge', value: profile.biggest_challenge },
              { label: 'Target Customer', value: profile.target_customer },
              { label: 'Avg Order Value', value: profile.avg_order_value ? `$${profile.avg_order_value}` : null },
              { label: 'Monthly Ad Spend', value: profile.monthly_ad_spend ? `$${profile.monthly_ad_spend?.toLocaleString()}` : null },
              { label: 'Current ROAS', value: profile.current_roas ? `${profile.current_roas}x` : null },
              { label: 'Break-even ROAS', value: profile.break_even_roas ? `${profile.break_even_roas}x` : null },
            ].filter(i => i.value).map(item => (
              <div key={item.label} className="bg-white rounded-xl border p-4">
                <div className="text-xs text-gray-400 mb-1">{item.label}</div>
                <div className="text-sm font-medium text-gray-800">{item.value}</div>
              </div>
            ))}
          </div>

          {profile.active_channels?.length > 0 && (
            <div className="bg-white rounded-xl border p-4">
              <div className="text-xs text-gray-400 mb-2">Active Channels</div>
              <div className="flex flex-wrap gap-2">
                {profile.active_channels.map((ch: string) => (
                  <span key={ch} className="bg-indigo-50 text-indigo-700 text-sm px-3 py-1 rounded-full border border-indigo-200">
                    {ch}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

---

## MODULE E + F: ROAS ALERT N8N + PLATFORM EVENTS INTEGRATION

### E1: Wire event bus into all existing modules

Update `apps/api/app/api/endpoints/ad_analytics.py` — add event publishing:

In the `analyze_campaign` endpoint, after analysis is complete, add:
```python
# Publish event if ROAS is critical
if roas_7d < 1.0:
    from app.services.automation.event_bus import EventBus
    bus = EventBus(db, wid)
    await bus.publish("roas_critical", "ad_analytics", {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name"),
        "roas": roas_7d,
        "spend_7d": sum(r.get('spend', 0) for r in recent_7)
    })
```

Update finance endpoint — after invoice processed:
```python
# After successful invoice processing, publish event
from app.services.automation.event_bus import EventBus
bus = EventBus(db, workspace_id)
await bus.publish("invoice_processed", "finance", {
    "invoice_id": str(invoice_id),
    "vendor_name": data.get("vendor_name"),
    "total_amount": data.get("total_amount"),
    "direction": data.get("direction")
})
```

### E2: Events API endpoint

Add to system router:
```python
@router.get("/events")
async def get_recent_events(
    event_type: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent platform events for monitoring."""
    from app.services.automation.event_bus import EventBus
    bus = EventBus(db, str(current_user.workspace_id))
    events = await bus.get_recent_events(limit=limit, event_type=event_type)
    return {"events": events, "total": len(events)}
```

---

## FINAL INTEGRATION

### Register ALL new routers in main.py:

```python
# Add to apps/api/app/main.py:
from app.api.endpoints.system import router as system_router
from app.api.endpoints.discovery import router as discovery_router
from app.services.automation.n8n_client import N8NClient  # noqa (ensure import)

app.include_router(system_router)
app.include_router(discovery_router)
```

### Add ALL new sidebar navigation items:

Find sidebar component and add:

```typescript
// Add to imports:
import { Activity, Brain, DollarSign, Building2, Workflow } from 'lucide-react'

// INTELLIGENCE section:
{ label: 'Company Intelligence', href: '/dashboard/company-intelligence', icon: Building2 },

// AD ANALYTICS section (add to existing):
{ label: 'True Profitability', href: '/dashboard/ads/profitability', icon: DollarSign },

// SYSTEM section:
{ label: 'System Health', href: '/dashboard/system', icon: Activity },
```

### Add ALL new .env variables (consolidated):

```bash
cat >> "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api/.env" << 'EOF'

# CALLING (Twilio)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
WEBHOOK_BASE_URL=http://localhost:8000
HUGGINGFACE_TOKEN=

# LIVEKIT (browser calling)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# N8N
N8N_URL=http://localhost:5678
N8N_API_KEY=

# MAUTIC
MAUTIC_URL=http://localhost:8181
MAUTIC_USER=admin
MAUTIC_PASS=
MAUTIC_CAMPAIGN_HOT=2
MAUTIC_CAMPAIGN_WARM=1
MAUTIC_CAMPAIGN_COLD=3
EOF
```

---

## VERIFICATION

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "=== BACKEND STARTUP ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 3
cd "$BASE/apps/api"
uvicorn app.main:app --reload --port 8000 > /tmp/phase2_startup.log 2>&1 &
sleep 12
grep -E "ERROR|Import|Module" /tmp/phase2_startup.log | head -20

echo "=== IMPORT CHECKS ==="
python3 -c "from app.services.automation.n8n_client import N8NClient; print('n8n_client ✅')"
python3 -c "from app.services.automation.event_bus import EventBus; print('event_bus ✅')"
python3 -c "from app.services.ad_analytics.profitability_engine import ProfitabilityEngine; print('profitability ✅')"
python3 -c "from app.services.discovery.discovery_engine import DiscoveryEngine; print('discovery ✅')"
python3 -c "from app.services.calling.livekit_engine import LiveKitEngine; print('livekit ✅')"

echo "=== DATABASE TABLES ==="
python3 -c "
import asyncio, asyncpg, os
async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL','').replace('+asyncpg',''))
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
    names = [r['tablename'] for r in rows]
    for t in ['platform_events','product_costs','campaign_profit_analysis','company_profiles']:
        print(f\"{'✅' if t in names else '❌'} {t}\")
    await conn.close()
asyncio.run(main())
"

echo "=== ENDPOINT TESTS ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAILED'))")

for ep in \
  "GET /api/v1/system/health" \
  "GET /api/v1/system/events" \
  "GET /api/v1/discovery/status" \
  "GET /api/v1/ads/profitability/settings" \
  "GET /api/v1/ads/profitability/analysis?avg_order_value=50" \
  "GET /api/v1/calls/livekit/token" \
  "GET /api/v1/calls" \
  "GET /api/v1/finance/dashboard?months=3"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  status=$(curl -s -o /tmp/r.json -w "%{http_code}" \
    -X "$method" "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN")
  if [[ "$status" == "200" ]] || [[ "$status" == "201" ]] || [[ "$status" == "422" ]]; then
    echo "✅ $status $ep"
  else
    echo "❌ $status $ep"
    cat /tmp/r.json | head -2
  fi
done

echo "=== FRONTEND PAGES ==="
for page in \
  "dashboard/system/page.tsx" \
  "dashboard/company-intelligence/page.tsx" \
  "dashboard/ads/profitability/page.tsx" \
  "components/BrowserCaller.tsx"; do
  full="$BASE/apps/web/src/$page"
  echo "$([ -f "$full" ] && echo ✅ || echo ❌) $page"
done

echo "=== FRONTEND BUILD ==="
cd "$BASE/apps/web"
npx tsc --noEmit 2>&1 | grep "error TS" | wc -l | xargs echo "TypeScript errors:"
npx next build 2>&1 | grep -E "✓ Compiled|error" | tail -5

echo "=== CI FIX ==="
cd "$BASE/apps/api"
pip install ruff --quiet
ruff check app/ --fix 2>/dev/null
ruff check app/ 2>&1 | grep -v "^$" | wc -l | xargs echo "Remaining lint issues:"

echo "=== MAUTIC STATUS ==="
curl -s -o /dev/null -w "Mautic HTTP: %{http_code}\n" http://localhost:8181

echo "=== N8N STATUS ==="
curl -s http://localhost:5678/healthz 2>/dev/null && echo "n8n: online" || echo "n8n: offline"

echo ""
echo "=== COMMIT ALL FIXES ==="
cd "$BASE"
git add -A
git commit -m "feat: Phase 2 complete — True Profitability, Company Intelligence, LiveKit, Event Bus, System Health"
git push origin main
```

Fix every ❌ before committing. Do not stop until all checks pass.

---

## SUCCESS CRITERIA

```
╔══════════════════════════════════════════════════════════════════╗
║          PHASE 2 — FULL TRANSFORMATION COMPLETE                  ║
╠══════════════════════════════════════════════════════════════════╣
║ A: MAUTIC FIX + N8N           ✅ Health monitoring active       ║
║ B: AUTO CALL PIPELINE          ✅ Twilio + LiveKit + WhisperX   ║
║ C: TRUE PROFITABILITY          ✅ COGS-aware ROAS + Kill/Scale  ║
║ D: COMPANY INTELLIGENCE        ✅ Adaptive AI discovery (30min) ║
║ E: EVENT BUS                   ✅ Cross-module event publishing  ║
║ F: SYSTEM CONNECTIVITY         ✅ n8n webhooks wired            ║
╠══════════════════════════════════════════════════════════════════╣
║ New DB tables: platform_events, product_costs,                   ║
║                campaign_profit_analysis, company_profiles        ║
║ New pages: System Health, Company Intelligence, True Profitability║
║ New component: BrowserCaller (LiveKit WebRTC)                    ║
║ New services: n8n_client, event_bus, profitability_engine,       ║
║               discovery_engine, livekit_engine                   ║
╠══════════════════════════════════════════════════════════════════╣
║ NEXT STEPS:                                                      ║
║ 1. Add TWILIO credentials → calls auto-record                   ║
║ 2. Add HUGGINGFACE_TOKEN → speaker diarization                  ║
║ 3. Start Company Intelligence discovery                          ║
║ 4. Set product costs for True Profitability                     ║
║ 5. Build n8n workflows at localhost:5678                         ║
╚══════════════════════════════════════════════════════════════════╝
```
