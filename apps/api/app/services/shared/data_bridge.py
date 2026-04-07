"""
Cross-Module Data Bridge — shared contact/lead data across all Phase 2 modules.

The bridge owns all writes to `contacts`, `leads`, `lead_timeline`, and is the
single place where call analytics, finance, ad attribution, and email modules
push updates against a unified contact/lead profile.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row._mapping)


class DataBridge:
    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    async def get_or_create_contact(
        self,
        email: str | None = None,
        phone: str | None = None,
        full_name: str | None = None,
        company_name: str | None = None,
        source: str = "manual",
    ) -> dict:
        for field, val in (("email", email), ("phone", phone)):
            if val:
                r = await self.db.execute(
                    text(
                        f"SELECT * FROM contacts WHERE workspace_id=:wid AND {field}=:val LIMIT 1"
                    ),
                    {"wid": self.workspace_id, "val": val},
                )
                row = r.fetchone()
                if row:
                    return _row_to_dict(row)
        r = await self.db.execute(
            text(
                """
                INSERT INTO contacts(workspace_id, full_name, company_name, email, phone, source)
                VALUES(:wid, :name, :co, :email, :phone, :src)
                RETURNING *
                """
            ),
            {
                "wid": self.workspace_id,
                "name": full_name,
                "co": company_name,
                "email": email,
                "phone": phone,
                "src": source,
            },
        )
        await self.db.commit()
        return _row_to_dict(r.fetchone())

    async def get_or_create_lead(self, contact_id: str) -> dict:
        r = await self.db.execute(
            text("SELECT * FROM leads WHERE contact_id=:cid AND workspace_id=:wid LIMIT 1"),
            {"cid": contact_id, "wid": self.workspace_id},
        )
        row = r.fetchone()
        if row:
            return _row_to_dict(row)
        r = await self.db.execute(
            text(
                """
                INSERT INTO leads(contact_id, workspace_id, status, qualification_score)
                VALUES(:cid, :wid, 'new', 0)
                RETURNING *
                """
            ),
            {"cid": contact_id, "wid": self.workspace_id},
        )
        await self.db.commit()
        return _row_to_dict(r.fetchone())

    async def add_timeline_event(
        self,
        lead_id: str,
        event_type: str,
        title: str,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO lead_timeline(lead_id, event_type, title, description, metadata)
                VALUES(:lid, :et, :title, :desc, :meta::jsonb)
                """
            ),
            {
                "lid": lead_id,
                "et": event_type,
                "title": title,
                "desc": description,
                "meta": json.dumps(metadata or {}),
            },
        )
        await self.db.commit()

    async def update_lead_from_call(self, lead_id: str, analysis: dict) -> None:
        await self.db.execute(
            text(
                """
                UPDATE leads SET
                    qualification_score = GREATEST(
                        qualification_score,
                        COALESCE(:score, qualification_score)
                    ),
                    category = COALESCE(:cat, category),
                    ai_summary = :summary,
                    ai_intent = :intent,
                    ai_urgency = :urgency,
                    ai_next_action = :next_action,
                    last_contact_date = NOW(),
                    call_count = call_count + 1,
                    updated_at = NOW()
                WHERE id = :lid
                """
            ),
            {
                "lid": lead_id,
                "score": analysis.get("qualification_score"),
                "cat": analysis.get("qualification_category"),
                "summary": analysis.get("summary"),
                "intent": analysis.get("intent"),
                "urgency": analysis.get("urgency"),
                "next_action": analysis.get("next_action"),
            },
        )
        await self.db.commit()

    async def get_lead_full_profile(self, lead_id: str) -> dict:
        r = await self.db.execute(
            text(
                """
                SELECT l.*, c.full_name, c.company_name, c.email, c.phone, c.industry
                FROM leads l
                JOIN contacts c ON c.id = l.contact_id
                WHERE l.id = :lid
                """
            ),
            {"lid": lead_id},
        )
        row = r.fetchone()
        if not row:
            return {}
        lead = _row_to_dict(row)

        tl = await self.db.execute(
            text(
                "SELECT * FROM lead_timeline WHERE lead_id=:lid ORDER BY created_at DESC LIMIT 20"
            ),
            {"lid": lead_id},
        )
        lead["timeline"] = [_row_to_dict(r) for r in tl.fetchall()]

        calls = await self.db.execute(
            text(
                """
                SELECT COUNT(*) AS cnt,
                       AVG(duration_seconds) AS avg_dur,
                       MAX(started_at) AS last
                FROM calls WHERE lead_id = :lid
                """
            ),
            {"lid": lead_id},
        )
        lead["call_stats"] = _row_to_dict(calls.fetchone())
        return lead
