"""
Lead Qualification Engine — BANT-style scoring + AI analysis via local Ollama.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.model_config import TaskType, call_ollama_json

logger = logging.getLogger(__name__)


class LeadQualifier:
    SYSTEM = (
        "You are an expert B2B sales analyst. "
        "Analyze call transcripts objectively. Only report what is present in the transcript. "
        "Never fabricate information."
    )

    async def analyze_call(self, call_id: str, segments: list[dict], db: AsyncSession) -> dict:
        t0 = time.time()
        transcript = "\n".join(
            f"{s.get('speaker', '?')}: {(s.get('text') or '').strip()}"
            for s in segments
            if (s.get("text") or "").strip()
        )
        if len(transcript) < 50:
            return {}

        qual = self._extract_qualification(transcript) or {}
        sent = self._extract_sentiment(transcript) or {}
        summ = self._extract_summary(transcript) or {}

        score = self._compute_score(qual, sent)
        ms = int((time.time() - t0) * 1000)

        analysis = {
            **qual,
            **sent,
            **summ,
            "qualification_score": score,
            "qualification_category": self._category(score),
            "processing_duration_ms": ms,
        }

        await db.execute(
            text(
                """
                INSERT INTO call_analysis(
                    call_id, overall_sentiment, customer_sentiment, agent_sentiment,
                    intent, urgency, objections, buying_signals, action_items,
                    qualification_score, qualification_category, summary, key_points,
                    next_action, follow_up_days, ai_model_used, processing_duration_ms
                )
                VALUES(
                    :cid, :os, :cs, :as2, :intent, :urgency, :obj, :buy, :act,
                    :score, :cat, :summary, :kp, :next_action, :days, :model, :ms
                )
                ON CONFLICT(call_id) DO UPDATE SET
                    qualification_score = EXCLUDED.qualification_score,
                    qualification_category = EXCLUDED.qualification_category,
                    summary = EXCLUDED.summary,
                    intent = EXCLUDED.intent,
                    urgency = EXCLUDED.urgency,
                    next_action = EXCLUDED.next_action
                """
            ),
            {
                "cid": call_id,
                "os": analysis.get("overall_sentiment"),
                "cs": analysis.get("customer_sentiment"),
                "as2": analysis.get("agent_sentiment"),
                "intent": analysis.get("intent"),
                "urgency": analysis.get("urgency"),
                "obj": analysis.get("objections", []) or [],
                "buy": analysis.get("buying_signals", []) or [],
                "act": analysis.get("action_items", []) or [],
                "score": score,
                "cat": analysis.get("qualification_category"),
                "summary": analysis.get("summary"),
                "kp": analysis.get("key_points", []) or [],
                "next_action": analysis.get("next_action"),
                "days": analysis.get("follow_up_days", 3),
                "model": "ollama-local",
                "ms": ms,
            },
        )
        await db.execute(
            text("UPDATE calls SET analysis_status='completed' WHERE id=:id"),
            {"id": call_id},
        )
        await db.commit()
        return analysis

    # ── Internal extractors ──────────────────────────────────────────────────
    def _extract_qualification(self, transcript: str) -> dict:
        schema = {
            "intent": "interested",
            "urgency": "medium",
            "buying_signals": ["asked about pricing"],
            "objections": ["price concern"],
            "has_budget": True,
            "has_authority": False,
            "has_need": True,
            "has_timeline": False,
            "follow_up_days": 3,
            "action_items": ["send proposal"],
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
        schema = {
            "overall_sentiment": "mixed_positive",
            "customer_sentiment": "positive",
            "agent_sentiment": "professional",
        }
        prompt = f"""Sentiment analysis for this call transcript.
TRANSCRIPT:
{transcript[:2000]}
overall_sentiment: 'positive'|'negative'|'neutral'|'mixed_positive'|'mixed_negative'
customer_sentiment: how the customer felt
agent_sentiment: how professional the agent was"""
        return call_ollama_json(prompt, schema, task=TaskType.FAST, timeout=60)

    def _extract_summary(self, transcript: str) -> dict:
        schema = {
            "summary": "Call summary",
            "key_points": ["point 1"],
            "next_action": "Send proposal",
        }
        prompt = f"""Summarize this sales call.
TRANSCRIPT:
{transcript[:4000]}
summary: 2-3 sentence overview
key_points: 3-5 most important things discussed
next_action: single most important next step
Be concise. Factual, no fabrication."""
        return call_ollama_json(prompt, schema, task=TaskType.MULTILINGUAL, timeout=90)

    def _compute_score(self, qual: dict, sent: dict) -> int:
        score = 20
        if qual.get("has_budget"):
            score += 20
        if qual.get("has_authority"):
            score += 20
        if qual.get("has_need"):
            score += 20
        if qual.get("has_timeline"):
            score += 10
        score += {
            "interested": 10,
            "evaluating": 5,
            "follow_up_needed": 3,
            "not_interested": -30,
        }.get(qual.get("intent", ""), 0)
        cs = (sent.get("customer_sentiment") or "").lower()
        if "positive" in cs:
            score += 5
        elif "negative" in cs:
            score -= 10
        score += min(len(qual.get("buying_signals", []) or []) * 3, 10)
        score -= min(len(qual.get("objections", []) or []) * 2, 10)
        return max(0, min(100, score))

    def _category(self, score: int) -> str:
        if score >= 75:
            return "hot"
        if score >= 55:
            return "warm"
        if score >= 35:
            return "cold"
        if score >= 15:
            return "nurture"
        return "disqualified"
