"""
Platform Event Bus

All modules publish events here. Events are persisted to `platform_events`
and routed to n8n via the singleton client. Dispatch is non-blocking and
never raises so caller modules can't be broken by the bus.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.automation.n8n_client import n8n

logger = logging.getLogger(__name__)


class EventBus:
    """Central event publisher for cross-module communication."""

    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    async def publish(self, event_type: str, source_module: str, payload: dict) -> str:
        """Publish an event. Returns event ID."""
        result = await self.db.execute(
            text(
                """
                INSERT INTO platform_events(event_type, source_module, workspace_id, payload)
                VALUES (:et, :src, :wid, CAST(:payload AS jsonb))
                RETURNING id
                """
            ),
            {
                "et": event_type,
                "src": source_module,
                "wid": self.workspace_id,
                "payload": json.dumps(payload),
            },
        )
        event_id = str(result.fetchone()[0])
        await self.db.commit()

        try:
            await self._dispatch_to_n8n(event_type, payload)
        except Exception as e:
            logger.warning("Event bus n8n dispatch failed (non-critical): %s", e)

        logger.info("Event published: %s from %s", event_type, source_module)
        return event_id

    async def _dispatch_to_n8n(self, event_type: str, payload: dict) -> None:
        """Route events to the appropriate n8n webhook."""
        if event_type == "lead_became_hot":
            await n8n.notify_lead_hot(
                lead_id=payload.get("lead_id", ""),
                contact_name=payload.get("contact_name", ""),
                score=payload.get("score", 0),
                workspace_id=self.workspace_id,
            )
        elif event_type == "call_completed":
            await n8n.notify_call_completed(
                call_id=payload.get("call_id", ""),
                lead_id=payload.get("lead_id"),
                duration=payload.get("duration_seconds", 0),
                workspace_id=self.workspace_id,
            )
        elif event_type == "roas_critical":
            await n8n.notify_roas_critical(
                campaign_id=payload.get("campaign_id", ""),
                campaign_name=payload.get("campaign_name", ""),
                roas=payload.get("roas", 0),
                workspace_id=self.workspace_id,
            )
        elif event_type == "invoice_processed":
            await n8n.notify_invoice_processed(
                invoice_id=payload.get("invoice_id", ""),
                vendor=payload.get("vendor_name", ""),
                total=payload.get("total_amount", 0),
                workspace_id=self.workspace_id,
            )

    async def get_recent_events(self, limit: int = 50, event_type: str | None = None) -> list[dict]:
        where = "WHERE workspace_id = :wid"
        params: dict = {"wid": self.workspace_id, "lim": limit}
        if event_type:
            where += " AND event_type = :et"
            params["et"] = event_type
        r = await self.db.execute(
            text(
                f"""
                SELECT id, event_type, source_module, payload, created_at
                FROM platform_events
                {where}
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            params,
        )
        out: list[dict] = []
        for row in r.fetchall():
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            out.append(d)
        return out
