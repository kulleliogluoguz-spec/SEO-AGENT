"""
Adaptive AI Company Discovery Engine

Conducts a 15-30 minute intelligent interview to deeply understand the
company. Questions adapt based on previous answers using local Ollama.
"""

from __future__ import annotations

import json
import logging

from app.services.ai.model_config import TaskType, call_ollama, call_ollama_json

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
    """Manages an adaptive company discovery conversation."""

    def get_opening_question(self, business_type: str | None = None) -> str:
        if business_type and business_type in FIRST_QUESTIONS_BY_CONTEXT:
            return FIRST_QUESTIONS_BY_CONTEXT[business_type]
        return FIRST_QUESTIONS_BY_CONTEXT["default"]

    # Hard minimum number of questions before the model is allowed to
    # complete. Smaller models love to short-circuit a discovery interview
    # after 2-3 questions; this guard refuses to honor a [COMPLETE] until we
    # have at least this many turns of real conversation.
    MIN_QUESTIONS = 10

    # Fallbacks used when the model tries to complete too early. Cycled by
    # `q_count % len(...)` so we don't repeat ourselves.
    _FALLBACK_QUESTIONS = [
        "What is your average order value and customer lifetime value?",
        "Who are your main competitors and how do you differentiate?",
        "What is your current biggest marketing challenge?",
        "How do you currently acquire new customers?",
        "What does success look like for you in the next 12 months?",
        "What is your gross margin on products?",
        "Which sales channels generate the most revenue?",
        "How large is your team and what stage is the business?",
        "What marketing tools or platforms are you currently using?",
        "What has worked well in your marketing so far?",
    ]

    def generate_next_question(self, transcript: list[dict], company_knowledge: dict) -> str:
        """Generate the next question (or [COMPLETE]) from conversation history."""
        q_count = len([t for t in transcript if t.get("role") == "assistant"])
        if q_count >= 20:
            return "[COMPLETE]"

        conv_text = "\n".join(
            f"{t['role'].upper()}: {t.get('content', '')}" for t in transcript[-10:]
        )

        # Build the completion instruction based on whether we've hit the
        # hard minimum yet. Below the minimum we forbid completion entirely.
        if q_count < self.MIN_QUESTIONS:
            completion_instruction = (
                f"IMPORTANT: You have only asked {q_count} questions. "
                "You MUST ask more. DO NOT output [COMPLETE] under any circumstances."
            )
        else:
            completion_instruction = (
                "You may output [COMPLETE] if you have comprehensive answers about: "
                "industry, business model, target customer, monthly ad spend, "
                "biggest challenge, and primary goal."
            )

        prompt = f"""You are conducting a company discovery interview. Your only job right now is to ask the next question.

CONVERSATION SO FAR:
{conv_text}

QUESTIONS ASKED SO FAR: {q_count}
MINIMUM REQUIRED: {self.MIN_QUESTIONS}

{completion_instruction}

RULES:
1. Output ONLY the next question as plain text. Nothing else. No preamble.
2. Do NOT output [COMPLETE] unless q_count >= {self.MIN_QUESTIONS} AND profile is comprehensive
3. Ask about something NEW not yet covered
4. Be conversational and specific to what you learned

Next question:"""

        response = call_ollama(
            prompt=prompt,
            task=TaskType.MULTILINGUAL,
            max_tokens=100,
            temperature=0.4,
            system=DISCOVERY_SYSTEM,
            timeout=60,
        )
        result = (response or "").strip()

        # Hard guard: never complete early regardless of model output.
        if q_count < self.MIN_QUESTIONS and ("[COMPLETE]" in result or not result):
            # Model tried to complete too early (or returned an empty
            # response) — fall back to a deterministic question.
            return self._FALLBACK_QUESTIONS[q_count % len(self._FALLBACK_QUESTIONS)]

        return result or "[COMPLETE]"

    def extract_company_knowledge(self, transcript: list[dict]) -> dict:
        """Extract a structured company profile from conversation."""
        conv_text = "\n".join(f"{t['role'].upper()}: {t.get('content', '')}" for t in transcript)

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
            "recommendations": ["Focus on LTV over CAC", "Test incrementality"],
        }

        prompt = f"""Extract a structured company profile from this discovery conversation.

FULL CONVERSATION:
{conv_text}

Extract all available information. Use null for anything not mentioned.
For break_even_roas: estimate from margins if mentioned (e.g., 40% margin → 2.5x break-even).
For key_insights: list 3-5 important observations about their business.
For recommendations: suggest 2-3 specific actions based on what you learned."""

        return call_ollama_json(
            prompt=prompt,
            schema_example=schema,
            task=TaskType.REASONING,
            timeout=120,
        )

    def generate_company_summary(self, knowledge: dict, transcript: list[dict]) -> str:
        """Generate a comprehensive 3-paragraph business intelligence summary."""
        prompt = f"""Write a comprehensive 3-paragraph business intelligence summary.

COMPANY PROFILE:
{json.dumps(knowledge, indent=2, default=str)}

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
            timeout=120,
        )
