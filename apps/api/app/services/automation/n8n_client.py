"""
n8n Integration Client

Sends events to n8n webhooks for workflow automation.
Non-blocking — platform continues if n8n is down.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


class N8NClient:
    """Fire-and-forget webhook dispatcher with graceful degradation."""

    async def trigger_webhook(self, webhook_path: str, payload: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(f"{N8N_URL}/webhook/{webhook_path}", json=payload)
                return r.status_code < 300
        except Exception as e:
            logger.warning("n8n webhook %s failed (non-critical): %s", webhook_path, e)
            return False

    async def notify_lead_hot(
        self, lead_id: str, contact_name: str, score: int, workspace_id: str
    ) -> bool:
        return await self.trigger_webhook(
            "lead-hot",
            {
                "lead_id": lead_id,
                "contact_name": contact_name,
                "score": score,
                "workspace_id": workspace_id,
                "action": "lead_became_hot",
            },
        )

    async def notify_call_completed(
        self,
        call_id: str,
        lead_id: str | None,
        duration: int,
        workspace_id: str,
    ) -> bool:
        return await self.trigger_webhook(
            "call-completed",
            {
                "call_id": call_id,
                "lead_id": lead_id,
                "duration_seconds": duration,
                "workspace_id": workspace_id,
            },
        )

    async def notify_roas_critical(
        self,
        campaign_id: str,
        campaign_name: str,
        roas: float,
        workspace_id: str,
    ) -> bool:
        return await self.trigger_webhook(
            "roas-alert",
            {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "roas": roas,
                "workspace_id": workspace_id,
                "severity": "critical",
            },
        )

    async def notify_invoice_processed(
        self,
        invoice_id: str,
        vendor: str,
        total: float,
        workspace_id: str,
    ) -> bool:
        return await self.trigger_webhook(
            "invoice-processed",
            {
                "invoice_id": invoice_id,
                "vendor": vendor,
                "total": total,
                "workspace_id": workspace_id,
            },
        )

    async def notify_weekly_report_ready(self, workspace_id: str, report_url: str) -> bool:
        return await self.trigger_webhook(
            "weekly-report",
            {"workspace_id": workspace_id, "report_url": report_url},
        )


# Singleton
n8n = N8NClient()
