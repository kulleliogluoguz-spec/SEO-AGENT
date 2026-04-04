"""
Call Intelligence Endpoint
Hybrid architecture:
- Outbound: Twilio Voice SDK (automatic recording via webhook)
- Inbound:  Manual upload after GSM call
- Analysis: Local Whisper + Ollama qwen3:8b (no external AI)
"""

import os
import json
import uuid
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

CALLS_STORAGE = Path(os.getenv("CALLS_STORAGE_PATH", "./storage/calls"))
CALLS_STORAGE.mkdir(parents=True, exist_ok=True)
CALLS_DB = CALLS_STORAGE / "calls.json"

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".aac"}


# ─── Database helpers ────────────────────────────────────────────────────────

def load_db() -> dict:
    if not CALLS_DB.exists():
        return {"calls": []}
    with open(CALLS_DB) as f:
        return json.load(f)


def save_db(data: dict):
    with open(CALLS_DB, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_call(call_id: str) -> Optional[dict]:
    for c in load_db()["calls"]:
        if c["id"] == call_id:
            return c
    return None


def update_call(call_id: str, updates: dict):
    db = load_db()
    for i, c in enumerate(db["calls"]):
        if c["id"] == call_id:
            db["calls"][i].update(updates)
            break
    save_db(db)


def add_call(call: dict):
    db = load_db()
    db["calls"].insert(0, call)
    save_db(db)


# ─── Transcription ───────────────────────────────────────────────────────────

async def transcribe_audio(audio_path: str) -> str:
    """Transcribe using local Whisper. No external API calls."""
    loop = asyncio.get_running_loop()

    def _transcribe():
        # Try whisper CLI first
        try:
            result = subprocess.run(
                ["whisper", audio_path, "--model", "base",
                 "--output_format", "txt", "--output_dir", str(CALLS_STORAGE),
                 "--language", "auto"],
                capture_output=True, text=True, timeout=300
            )
            txt = CALLS_STORAGE / (Path(audio_path).stem + ".txt")
            if txt.exists():
                t = txt.read_text().strip()
                txt.unlink()
                if t:
                    return t
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fall back to Python whisper library
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"].strip()
        except ImportError:
            pass

        return "[Transcription unavailable — install whisper: pip install openai-whisper]"

    return await loop.run_in_executor(None, _transcribe)


# ─── AI Analysis ─────────────────────────────────────────────────────────────

async def analyze_with_ollama(transcript: str) -> dict:
    """
    Analyze call with local Ollama qwen3:8b.
    100% local — no data leaves the machine.
    """
    import httpx

    prompt = f"""You are an expert sales call analyst. Analyze this call transcript.

TRANSCRIPT:
{transcript[:5000]}

Respond ONLY with valid JSON, no other text:
{{
    "customer_name": "name or Unknown",
    "customer_phone": "phone or Unknown",
    "company_name": "company they represent or Unknown",
    "call_summary": "2-3 sentence summary",
    "customer_intent": "what they wanted",
    "key_requests": ["request1", "request2"],
    "objections": ["objection1", "objection2"],
    "sentiment": "positive/neutral/negative/mixed",
    "sales_potential": "hot/warm/cold/not_interested",
    "sales_score": 75,
    "sales_reasoning": "why this score",
    "follow_up_recommended": true,
    "follow_up_actions": ["action1", "action2"],
    "rep_score": 80,
    "rep_strengths": ["strength1"],
    "rep_improvements": ["improvement1"],
    "keywords": ["kw1", "kw2"]
}}

Scoring:
- hot (80-100): Strong buying intent, confirmed budget/timeline
- warm (50-79): Interested but needs follow-up
- cold (20-49): Low interest, major objections
- not_interested (0-19): Explicit rejection"""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3:8b", "prompt": prompt, "stream": False}
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
    except Exception as e:
        print(f"Ollama analysis error: {e}")

    return {
        "customer_name": "Unknown",
        "customer_phone": "Unknown",
        "company_name": "Unknown",
        "call_summary": "Analysis failed",
        "customer_intent": "Unknown",
        "key_requests": [],
        "objections": [],
        "sentiment": "neutral",
        "sales_potential": "cold",
        "sales_score": 0,
        "sales_reasoning": "AI analysis failed",
        "follow_up_recommended": False,
        "follow_up_actions": [],
        "rep_score": 0,
        "rep_strengths": [],
        "rep_improvements": [],
        "keywords": [],
    }


# ─── Background pipeline ─────────────────────────────────────────────────────

async def process_call(call_id: str, audio_path: str):
    """Full pipeline: transcribe → analyze → save."""
    try:
        update_call(call_id, {"status": "transcribing"})
        transcript = await transcribe_audio(audio_path)
        update_call(call_id, {"transcript": transcript, "status": "analyzing"})

        analysis = await analyze_with_ollama(transcript)
        update_call(call_id, {
            "analysis": analysis,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        update_call(call_id, {"status": "failed", "error": str(e)})


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_calls(limit: int = 50, offset: int = 0):
    """List all calls with pagination."""
    db = load_db()
    calls = db["calls"]
    return {
        "calls": calls[offset:offset + limit],
        "total": len(calls),
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_stats():
    """Get call statistics for dashboard."""
    db = load_db()
    calls = db["calls"]
    completed = [c for c in calls if c.get("status") == "completed"]

    now = datetime.utcnow()
    week_ago = (now - timedelta(days=7)).isoformat()
    this_week = [c for c in completed if c.get("created_at", "") >= week_ago]

    scores = {
        "hot": len([c for c in completed if c.get("analysis", {}).get("sales_potential") == "hot"]),
        "warm": len([c for c in completed if c.get("analysis", {}).get("sales_potential") == "warm"]),
        "cold": len([c for c in completed if c.get("analysis", {}).get("sales_potential") == "cold"]),
        "not_interested": len([c for c in completed if c.get("analysis", {}).get("sales_potential") == "not_interested"]),
    }

    return {
        "total_calls": len(calls),
        "completed": len(completed),
        "this_week": len(this_week),
        "sales_breakdown": scores,
        "avg_sales_score": sum(
            c.get("analysis", {}).get("sales_score", 0) for c in completed
        ) / max(len(completed), 1),
    }


@router.get("/weekly-report")
async def weekly_report():
    """Generate weekly sales intelligence report."""
    db = load_db()
    now = datetime.utcnow()
    week_ago = (now - timedelta(days=7)).isoformat()

    weekly = [
        c for c in db["calls"]
        if c.get("created_at", "") >= week_ago and c.get("status") == "completed"
    ]

    customers = []
    for call in weekly:
        analysis = call.get("analysis", {})
        customers.append({
            "customer_name": analysis.get("customer_name", "Unknown"),
            "customer_phone": call.get("phone_number", analysis.get("customer_phone", "Unknown")),
            "company": analysis.get("company_name", "Unknown"),
            "call_date": call.get("created_at"),
            "duration": call.get("duration"),
            "sales_potential": analysis.get("sales_potential", "cold"),
            "sales_score": analysis.get("sales_score", 0),
            "summary": analysis.get("call_summary", ""),
            "key_requests": analysis.get("key_requests", []),
            "follow_up": analysis.get("follow_up_recommended", False),
            "follow_up_actions": analysis.get("follow_up_actions", []),
            "reasoning": analysis.get("sales_reasoning", ""),
        })

    customers.sort(key=lambda x: x["sales_score"], reverse=True)

    return {
        "period": {"from": week_ago, "to": now.isoformat()},
        "total_calls": len(weekly),
        "customers": customers,
        "hot_leads": [c for c in customers if c["sales_potential"] == "hot"],
        "warm_leads": [c for c in customers if c["sales_potential"] == "warm"],
        "cold_leads": [c for c in customers if c["sales_potential"] == "cold"],
        "not_interested": [c for c in customers if c["sales_potential"] == "not_interested"],
    }


@router.post("/upload")
async def upload_call(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    phone_number: str = Form(""),
    rep_name: str = Form(""),
    call_type: str = Form("inbound"),
    notes: str = Form(""),
):
    """Upload a call recording (inbound GSM calls logged manually)."""
    ext = Path(file.filename or "audio.wav").suffix.lower()
    if ext not in SUPPORTED_AUDIO:
        raise HTTPException(400, f"Unsupported format. Use: {', '.join(sorted(SUPPORTED_AUDIO))}")

    call_id = str(uuid.uuid4())
    audio_path = CALLS_STORAGE / f"{call_id}{ext}"

    async with aiofiles.open(audio_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    call = {
        "id": call_id,
        "type": call_type,
        "phone_number": phone_number,
        "rep_name": rep_name,
        "notes": notes,
        "filename": file.filename,
        "audio_path": str(audio_path),
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "transcript": None,
        "analysis": None,
    }
    add_call(call)
    background_tasks.add_task(process_call, call_id, str(audio_path))

    return {"call_id": call_id, "status": "queued", "message": "Processing started"}


@router.post("/{call_id}/reanalyze")
async def reanalyze_call(call_id: str, background_tasks: BackgroundTasks):
    """Re-run AI analysis on an existing call."""
    call = get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    audio_path = call.get("audio_path", "")
    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=422, detail="Audio file not found — cannot reanalyze")
    update_call(call_id, {"status": "queued"})
    background_tasks.add_task(process_call, call_id, audio_path)
    return {"status": "reanalysis started"}


@router.delete("/{call_id}")
async def delete_call(call_id: str):
    """Delete a call and its audio file."""
    call = get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")

    audio = Path(call.get("audio_path", ""))
    if audio.exists():
        audio.unlink()

    db = load_db()
    db["calls"] = [c for c in db["calls"] if c["id"] != call_id]
    save_db(db)
    return {"deleted": True}


@router.get("/{call_id}")
async def get_call_detail(call_id: str):
    """Get full call detail including transcript and analysis."""
    call = get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


# ─── Twilio Routes ────────────────────────────────────────────────────────────

@router.post("/twilio/token")
async def get_twilio_token(identity: str = "user"):
    """Generate Twilio access token for React Native SDK."""
    try:
        from twilio.jwt.access_token import AccessToken
        from twilio.jwt.access_token.grants import VoiceGrant
        from app.core.config.settings import get_settings

        s = get_settings()
        if not s.twilio_account_sid:
            raise HTTPException(503, "Twilio not configured")

        token = AccessToken(
            s.twilio_account_sid,
            s.twilio_api_key_sid,
            s.twilio_api_key_secret,
            identity=identity,
            ttl=3600,
        )
        grant = VoiceGrant(
            outgoing_application_sid=s.twilio_twiml_app_sid,
            incoming_allow=True,
        )
        token.add_grant(grant)
        return {"token": token.to_jwt()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Token generation failed: {e}")


@router.post("/twiml/outbound")
async def twiml_outbound(request: Request):
    """TwiML for outbound calls — enables dual-channel recording."""
    form = await request.form()
    to_number = form.get("To", "")
    caller_id = os.getenv("TWILIO_PHONE_NUMBER", "")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial callerId="{caller_id}"
          record="record-from-ringing-dual"
          recordingStatusCallback="/api/v1/calls/twilio/recording-complete"
          recordingStatusCallbackMethod="POST">
        <Number>{to_number}</Number>
    </Dial>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/recording-complete")
async def recording_complete(request: Request, background_tasks: BackgroundTasks):
    """Twilio webhook — called when a recording is ready to download."""
    form = await request.form()
    recording_url = form.get("RecordingUrl", "")
    call_sid = form.get("CallSid", "")
    duration = form.get("RecordingDuration", "0")

    if not recording_url:
        return {"status": "no recording"}

    call_id = str(uuid.uuid4())
    audio_path = CALLS_STORAGE / f"{call_id}.wav"

    import httpx
    from app.core.config.settings import get_settings

    s = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{recording_url}.wav",
            auth=(s.twilio_account_sid, s.twilio_auth_token),
        )
        async with aiofiles.open(audio_path, "wb") as f:
            await f.write(resp.content)

    call = {
        "id": call_id,
        "type": "outbound",
        "twilio_call_sid": call_sid,
        "duration": int(duration),
        "audio_path": str(audio_path),
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "transcript": None,
        "analysis": None,
    }
    add_call(call)
    background_tasks.add_task(process_call, call_id, str(audio_path))

    return {"status": "processing", "call_id": call_id}
