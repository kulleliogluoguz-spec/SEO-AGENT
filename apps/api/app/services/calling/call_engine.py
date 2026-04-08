"""
Call Engine — manages call lifecycle across Twilio/Manual Upload.

Writes to the `calls` table (renamed to avoid clash with the legacy
JSON-file-based `calls` endpoint that already ships with the platform).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

RECORDINGS_DIR = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class CallEngine:
    def __init__(self, db: AsyncSession | None, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    # ── Twilio outbound ──────────────────────────────────────────────────────
    async def initiate_twilio_call(
        self,
        to_phone: str,
        from_phone: str,
        contact_id: str | None = None,
        lead_id: str | None = None,
        record: bool = True,
    ) -> dict:
        try:
            from twilio.rest import Client as TwilioClient
        except ImportError:
            return {"error": "twilio package not installed"}

        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        webhook = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        if not sid or not token:
            return {
                "error": "Twilio credentials missing. Set TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN in .env"
            }

        client = TwilioClient(sid, token)
        call_id = str(uuid.uuid4())

        await self.db.execute(
            text(
                """
                INSERT INTO calls(
                    id, workspace_id, contact_id, lead_id, direction,
                    status, provider, consent_given, consent_timestamp
                )
                VALUES(:id, :wid, :cid, :lid, 'outbound', 'active', 'twilio', true, NOW())
                """
            ),
            {"id": call_id, "wid": self.workspace_id, "cid": contact_id, "lid": lead_id},
        )
        await self.db.commit()

        try:
            call = client.calls.create(
                to=to_phone,
                from_=from_phone,
                url=f"{webhook}/api/v1/calling/twiml/{call_id}",
                record=record,
                recording_status_callback=f"{webhook}/api/v1/calling/recording-webhook/{call_id}",
                recording_status_callback_event=["completed"],
                status_callback=f"{webhook}/api/v1/calling/status-webhook/{call_id}",
            )
            await self.db.execute(
                text("UPDATE calls SET provider_call_id=:sid, started_at=NOW() WHERE id=:id"),
                {"sid": call.sid, "id": call_id},
            )
            await self.db.commit()
            return {"call_id": call_id, "provider_call_id": call.sid, "status": "initiated"}
        except Exception as e:
            logger.error("Twilio call create failed: %s", e)
            await self.db.execute(
                text("UPDATE calls SET status='failed' WHERE id=:id"), {"id": call_id}
            )
            await self.db.commit()
            return {"error": str(e), "call_id": call_id}

    def get_twiml_response(self, call_id: str) -> str:
        # KVKK compliance: announce that the call is being recorded.
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

    async def handle_recording_webhook(
        self, call_id: str, recording_url: str, duration: int
    ) -> None:
        import requests as req_lib

        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        dest = RECORDINGS_DIR / f"{call_id}.wav"
        try:
            r = req_lib.get(f"{recording_url}.wav", auth=(sid, token), stream=True, timeout=60)
            with open(dest, "wb") as f:
                shutil.copyfileobj(r.raw, f)
            size_mb = dest.stat().st_size / 1e6
            await self.db.execute(
                text(
                    """
                    UPDATE calls SET
                        recording_path=:path,
                        recording_size_mb=:size,
                        duration_seconds=:dur,
                        status='completed',
                        ended_at=NOW()
                    WHERE id=:id
                    """
                ),
                {"path": str(dest), "size": size_mb, "dur": duration, "id": call_id},
            )
            await self.db.commit()
            import asyncio

            asyncio.create_task(self._process_async(call_id, str(dest)))
        except Exception as e:
            logger.error(f"Recording download failed for {call_id}: {e}")

    async def _process_async(self, call_id: str, recording_path: str) -> None:
        """
        Full automatic pipeline after a call recording is received:

        1. Transcribe (WhisperX preferred, faster-whisper fallback)
        2. Analyze (LeadQualifier via local Ollama)
        3. Update lead score via DataBridge
        4. Publish lead_became_hot event if score >= 75
        5. Publish call_completed event

        Spawns its own DB session because Twilio webhooks run in a separate
        request context and the original session may already be closed.
        """
        from app.core.db.database import AsyncSessionLocal
        from app.services.automation.event_bus import EventBus
        from app.services.calling.lead_qualifier import LeadQualifier
        from app.services.calling.transcription_engine import TranscriptionEngine
        from app.services.shared.data_bridge import DataBridge

        logger.info("[AUTO PIPELINE] Starting for call %s", call_id)

        async with AsyncSessionLocal() as db:
            try:
                # Step 1: transcribe
                segments = await TranscriptionEngine().transcribe_call(call_id, recording_path, db)
                if not segments:
                    logger.warning("No transcript produced for call %s", call_id)
                    return

                logger.info(
                    "[AUTO PIPELINE] %d segments transcribed for %s",
                    len(segments),
                    call_id,
                )

                # Step 2: AI analysis
                analysis = await LeadQualifier().analyze_call(call_id, segments, db)

                # Step 3: update lead if associated
                call_r = await db.execute(
                    text(
                        "SELECT lead_id, workspace_id, contact_id, duration_seconds "
                        "FROM calls WHERE id = :id"
                    ),
                    {"id": call_id},
                )
                call_row = call_r.fetchone()
                if not call_row:
                    return

                call_mapping = call_row._mapping
                lead_id = call_mapping.get("lead_id")
                workspace_id = str(call_mapping.get("workspace_id") or self.workspace_id)
                contact_id = call_mapping.get("contact_id")
                duration = int(call_mapping.get("duration_seconds") or 0)

                if lead_id:
                    bridge = DataBridge(db, workspace_id)
                    await bridge.update_lead_from_call(str(lead_id), analysis)

                    # Step 4: hot-lead escalation
                    if analysis.get("qualification_score", 0) >= 75:
                        contact_name = "Unknown"
                        if contact_id:
                            contact_r = await db.execute(
                                text("SELECT full_name FROM contacts WHERE id = :id"),
                                {"id": contact_id},
                            )
                            contact = contact_r.fetchone()
                            if contact:
                                contact_name = contact._mapping.get("full_name") or "Unknown"

                        bus = EventBus(db, workspace_id)
                        await bus.publish(
                            "lead_became_hot",
                            "calling",
                            {
                                "lead_id": str(lead_id),
                                "contact_name": contact_name,
                                "score": analysis.get("qualification_score", 0),
                                "call_id": call_id,
                            },
                        )

                # Step 5: call_completed event
                bus = EventBus(db, workspace_id)
                await bus.publish(
                    "call_completed",
                    "calling",
                    {
                        "call_id": call_id,
                        "lead_id": str(lead_id) if lead_id else None,
                        "duration_seconds": duration,
                        "qualification_score": analysis.get("qualification_score", 0),
                        "qualification_category": analysis.get("qualification_category", "unknown"),
                    },
                )

                logger.info(
                    "[AUTO PIPELINE] Complete for call %s: score=%s",
                    call_id,
                    analysis.get("qualification_score"),
                )

            except Exception as e:
                logger.error("[AUTO PIPELINE] Failed for call %s: %s", call_id, e, exc_info=True)
                try:
                    await db.execute(
                        text("UPDATE calls SET analysis_status='failed' WHERE id = :id"),
                        {"id": call_id},
                    )
                    await db.commit()
                except Exception:
                    pass

    # ── Manual upload ────────────────────────────────────────────────────────
    async def upload_recording(
        self,
        call_id: str,
        file_path: str,
        contact_id: str | None = None,
        lead_id: str | None = None,
    ) -> dict:
        dest = RECORDINGS_DIR / f"{call_id}.wav"
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", str(dest), "-y"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # Fall back: copy the file as-is so the upload still records.
                shutil.copy(file_path, dest)
        except FileNotFoundError:
            # ffmpeg missing — copy raw bytes so upload still works.
            shutil.copy(file_path, dest)

        size_mb = dest.stat().st_size / 1e6
        await self.db.execute(
            text(
                """
                INSERT INTO calls(
                    id, workspace_id, contact_id, lead_id, direction,
                    status, recording_path, recording_size_mb, provider, consent_given,
                    started_at
                )
                VALUES(:id, :wid, :cid, :lid, 'inbound', 'completed', :path, :size,
                       'manual_upload', true, NOW())
                ON CONFLICT(id) DO UPDATE
                    SET recording_path = EXCLUDED.recording_path,
                        recording_size_mb = EXCLUDED.recording_size_mb
                """
            ),
            {
                "id": call_id,
                "wid": self.workspace_id,
                "cid": contact_id,
                "lid": lead_id,
                "path": str(dest),
                "size": size_mb,
            },
        )
        await self.db.commit()
        return {
            "call_id": call_id,
            "recording_path": str(dest),
            "size_mb": size_mb,
            "status": "uploaded",
        }
