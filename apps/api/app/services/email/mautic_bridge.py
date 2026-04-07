"""
Mautic Integration Bridge — lead sync and AI-assisted outreach.
All email sends require human approval. Never auto-send.
"""

from __future__ import annotations

import logging
import os

import requests

from app.services.ai.model_config import TaskType, call_ollama

logger = logging.getLogger(__name__)
MAUTIC_URL = os.getenv("MAUTIC_URL", "http://localhost:8181")
MAUTIC_USER = os.getenv("MAUTIC_USER", "admin")
MAUTIC_PASS = os.getenv("MAUTIC_PASS", "")


class MauticBridge:
    def __init__(self) -> None:
        self.base = f"{MAUTIC_URL}/api"
        self.auth = (MAUTIC_USER, MAUTIC_PASS)

    def _get(self, ep: str) -> dict:
        try:
            r = requests.get(f"{self.base}/{ep}", auth=self.auth, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Mautic GET %s: %s", ep, e)
            return {}

    def _post(self, ep: str, data: dict) -> dict:
        try:
            r = requests.post(f"{self.base}/{ep}", json=data, auth=self.auth, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Mautic POST %s: %s", ep, e)
            return {}

    def sync_contact(self, contact: dict, score: int = 0) -> str | None:
        name_parts = (contact.get("full_name") or "").split()
        payload = {
            "email": contact.get("email"),
            "firstname": name_parts[0] if name_parts else "",
            "lastname": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            "company": contact.get("company_name"),
            "phone": contact.get("phone"),
            "points": score,
        }
        result = self._post("contacts/new", {k: v for k, v in payload.items() if v})
        return (result.get("contact") or {}).get("id")

    def trigger_sequence(self, mautic_id: str, sequence: str) -> bool:
        campaign_map = {
            "hot_lead_followup": os.getenv("MAUTIC_CAMPAIGN_HOT", "2"),
            "warm_lead_nurture": os.getenv("MAUTIC_CAMPAIGN_WARM", "1"),
            "cold_lead_reactivation": os.getenv("MAUTIC_CAMPAIGN_COLD", "3"),
        }
        cid = campaign_map.get(sequence)
        if not cid:
            return False
        result = self._post(f"campaigns/{cid}/contact/{mautic_id}/add", {})
        return bool(result)

    def generate_email_draft(
        self, contact: dict, analysis: dict, purpose: str = "follow_up"
    ) -> dict:
        """Generate AI draft. Human MUST approve before sending."""
        objections = analysis.get("objections") or []
        objection_str = ", ".join(objections) if objections else "none"
        prompt = f"""Generate a professional, personalized B2B email.

Contact: {contact.get('full_name')} at {contact.get('company_name')}
Lead Status: {analysis.get('qualification_category', 'warm')}
Intent: {analysis.get('intent', 'evaluating')}
Objections: {objection_str}
Previous summary: {analysis.get('summary', 'Initial contact')}
Purpose: {purpose}

Write concise email (max 150 words):
1. Reference previous conversation naturally
2. Address main concern if any
3. Propose clear next step
4. Simple call to action

Format: Subject line first, blank line, then body.
Do NOT use "I hope this email finds you well"."""

        draft = call_ollama(
            prompt,
            task=TaskType.CREATIVE,
            max_tokens=300,
            temperature=0.6,
            timeout=90,
        )
        lines = draft.strip().split("\n")
        subject = lines[0].replace("Subject:", "").strip() if lines else "Following up"
        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else draft

        return {
            "subject": subject,
            "body": body,
            "requires_human_approval": True,
            "note": "AI draft — review and edit before sending.",
        }
