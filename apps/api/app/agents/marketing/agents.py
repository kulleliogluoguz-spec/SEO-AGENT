"""
Marketing Agent System — 13 Specialized Agents
Each agent: clear input/output schema, tool permissions, observable, safe.
Designed for LangGraph orchestration.
"""
from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Agent Base ──────────────────────────────────────────────────────────────

@dataclass
class AgentInput:
    workspace_id: str
    payload: dict
    context: dict = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class AgentOutput:
    success: bool
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace_id: str = ""
    agent_name: str = ""
    execution_ms: float = 0.0


class ToolPermission(str, Enum):
    READ_CONTENT = "read_content"
    WRITE_CONTENT = "write_content"
    READ_ANALYTICS = "read_analytics"
    SCHEDULE_CONTENT = "schedule_content"
    PUBLISH_CONTENT = "publish_content"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    MANAGE_ADS = "manage_ads"
    LLM_GENERATE = "llm_generate"


class BaseMarketingAgent(ABC):
    name: str = "base"
    description: str = ""
    permissions: list[ToolPermission] = []

    async def run(self, input: AgentInput) -> AgentOutput:
        """
        Observable wrapper around execute().
        Logs agent name, trace_id, execution time, success/failure.
        Use this instead of calling execute() directly.
        """
        import time
        start = time.monotonic()
        try:
            output = await self.execute(input)
            output.execution_ms = round((time.monotonic() - start) * 1000, 2)
            output.agent_name = self.name
            output.trace_id = input.trace_id
            logger.info(
                f"[Agent:{self.name}] trace={input.trace_id[:8]} "
                f"ok={output.success} ms={output.execution_ms} "
                f"warnings={len(output.warnings)} errors={len(output.errors)}"
            )
            return output
        except Exception as e:
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.error(f"[Agent:{self.name}] trace={input.trace_id[:8]} CRASHED ms={elapsed}: {e}")
            return AgentOutput(
                success=False, errors=[str(e)], trace_id=input.trace_id,
                agent_name=self.name, execution_ms=elapsed,
            )

    @abstractmethod
    async def execute(self, input: AgentInput) -> AgentOutput:
        ...

    def _output(self, success: bool, data: dict = None,
                errors: list = None, warnings: list = None, trace_id: str = "") -> AgentOutput:
        return AgentOutput(
            success=success, data=data or {}, errors=errors or [],
            warnings=warnings or [], trace_id=trace_id, agent_name=self.name,
        )


# ═════════════════════════════════════════════════════════════════════════════
#  1. CAMPAIGN PLANNER AGENT
# ═════════════════════════════════════════════════════════════════════════════

class CampaignPlannerAgent(BaseMarketingAgent):
    name = "campaign_planner"
    description = "Creates structured campaign plans from objectives and audience data."
    permissions = [ToolPermission.MANAGE_CAMPAIGNS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        """
        Input: { objective, target_audience, budget, duration_days, channels }
        Output: { campaign_plan: { name, phases, channels, content_themes, kpis } }
        """
        p = input.payload
        objective = p.get("objective", "brand awareness")
        channels = p.get("channels", ["instagram", "twitter", "linkedin"])
        duration = p.get("duration_days", 30)
        budget = p.get("budget", 0)

        # In production: call LLM with structured prompt
        plan = {
            "name": f"{objective.title()} Campaign — {datetime.utcnow().strftime('%b %Y')}",
            "objective": objective,
            "channels": channels,
            "duration_days": duration,
            "budget": budget,
            "phases": [
                {"name": "Launch", "days": "1-7", "focus": "awareness", "content_volume": "high"},
                {"name": "Engage", "days": "8-21", "focus": "engagement", "content_volume": "medium"},
                {"name": "Convert", "days": "22-30", "focus": "conversion", "content_volume": "targeted"},
            ],
            "content_themes": [
                "problem_agitation", "social_proof", "educational_value",
                "behind_the_scenes", "direct_offer",
            ],
            "kpis": {
                "impressions_target": 50000,
                "engagement_rate_target": 3.5,
                "click_target": 2000,
                "conversion_target": 100,
            },
            "posting_cadence": {ch: "daily" if ch in ["twitter", "instagram"] else "3x/week" for ch in channels},
        }

        return self._output(True, {"campaign_plan": plan}, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  2. CONTENT CALENDAR AGENT
# ═════════════════════════════════════════════════════════════════════════════

class ContentCalendarAgent(BaseMarketingAgent):
    name = "content_calendar"
    description = "Generates a time-slotted content calendar from a campaign plan."
    permissions = [ToolPermission.WRITE_CONTENT, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        """
        Input: { campaign_plan, start_date, timezone }
        Output: { calendar: [ { date, channel, content_type, theme, time_slot } ] }
        """
        plan = input.payload.get("campaign_plan", {})
        start = input.payload.get("start_date", datetime.utcnow().isoformat())
        channels = plan.get("channels", ["instagram", "twitter"])
        duration = plan.get("duration_days", 30)

        calendar = []
        start_dt = datetime.fromisoformat(start) if isinstance(start, str) else start

        optimal_times = {
            "instagram": ["09:00", "12:00", "18:00"],
            "tiktok": ["07:00", "12:00", "19:00"],
            "twitter": ["08:00", "12:00", "17:00"],
            "linkedin": ["08:00", "10:00", "17:00"],
            "meta_ads": ["06:00"],
        }

        themes = plan.get("content_themes", ["educational", "engagement"])

        for day_offset in range(duration):
            date = start_dt + timedelta(days=day_offset)
            for ch in channels:
                times = optimal_times.get(ch, ["12:00"])
                # Vary frequency by channel
                if ch == "twitter" or day_offset % 1 == 0:
                    time_slot = times[day_offset % len(times)]
                elif day_offset % 2 == 0:
                    time_slot = times[0]
                else:
                    continue  # skip this day for this channel

                calendar.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "day_of_week": date.strftime("%A"),
                    "channel": ch,
                    "time_slot": time_slot,
                    "theme": themes[day_offset % len(themes)],
                    "content_type": "post",
                    "status": "planned",
                })

        return self._output(True, {"calendar": calendar, "total_slots": len(calendar)},
                            trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  3. CHANNEL STRATEGY AGENT
# ═════════════════════════════════════════════════════════════════════════════

class ChannelStrategyAgent(BaseMarketingAgent):
    name = "channel_strategy"
    description = "Recommends optimal channel mix and strategy based on audience + goals."
    permissions = [ToolPermission.READ_ANALYTICS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        """
        Input: { industry, target_audience, goals, current_performance }
        Output: { strategy: { recommended_channels, rationale, budget_split } }
        """
        goals = input.payload.get("goals", ["awareness"])
        audience = input.payload.get("target_audience", "general")

        # In production: LLM analyzes audience data + industry benchmarks
        strategy = {
            "recommended_channels": [
                {"channel": "linkedin", "priority": "high", "rationale": "B2B audience, thought leadership"},
                {"channel": "instagram", "priority": "high", "rationale": "Visual storytelling, brand building"},
                {"channel": "twitter", "priority": "medium", "rationale": "Real-time engagement, industry discourse"},
                {"channel": "tiktok", "priority": "medium", "rationale": "Younger demographic reach, viral potential"},
            ],
            "budget_allocation": {
                "organic_content": 0.40, "paid_social": 0.35,
                "influencer": 0.15, "community": 0.10,
            },
            "posting_frequency": {
                "linkedin": "3-5x/week", "instagram": "daily",
                "twitter": "3-5x/day", "tiktok": "3-5x/week",
            },
        }
        return self._output(True, {"strategy": strategy}, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  4. SOCIAL POST GENERATOR AGENT
# ═════════════════════════════════════════════════════════════════════════════

class SocialPostGeneratorAgent(BaseMarketingAgent):
    name = "social_post_generator"
    description = "Generates channel-specific social media posts from a topic or brief."
    permissions = [ToolPermission.WRITE_CONTENT, ToolPermission.LLM_GENERATE]

    CHANNEL_TEMPLATES = {
        "instagram": {
            "format": "caption_with_hashtags",
            "max_length": 2200,
            "structure": ["hook", "value", "cta", "hashtags"],
            "tone": "conversational, visual-focused",
        },
        "tiktok": {
            "format": "hook_first_script",
            "max_length": 2200,
            "structure": ["hook (0-3s)", "problem (3-8s)", "solution (8-20s)", "cta (20-25s)"],
            "tone": "energetic, authentic, fast-paced",
        },
        "twitter": {
            "format": "thread_or_single",
            "max_length": 280,
            "structure": ["hook tweet", "supporting tweets", "cta tweet"],
            "tone": "sharp, witty, insight-led",
        },
        "linkedin": {
            "format": "professional_narrative",
            "max_length": 3000,
            "structure": ["hook line", "story/insight", "key takeaway", "discussion prompt"],
            "tone": "professional, thoughtful, story-driven",
        },
        "meta_ads": {
            "format": "ad_copy",
            "max_length": 125,
            "structure": ["primary_text", "headline", "description", "audience_angle"],
            "tone": "benefit-driven, clear, action-oriented",
        },
    }

    async def execute(self, input: AgentInput) -> AgentOutput:
        """
        Input: { topic, channel, tone, key_points, funnel_stage, persona }
        Output: { post: { body, hook, cta, hashtags, channel_metadata, media_instructions } }
        """
        channel = input.payload.get("channel", "instagram")
        topic = input.payload.get("topic", "")
        tone = input.payload.get("tone", "professional")
        key_points = input.payload.get("key_points", [])
        template = self.CHANNEL_TEMPLATES.get(channel, self.CHANNEL_TEMPLATES["instagram"])

        # In production: LLM generates with channel-specific prompt
        # This is a structured placeholder that shows the generation pattern
        post = self._generate_placeholder(channel, topic, tone, key_points, template)
        return self._output(True, {"post": post}, trace_id=input.trace_id)

    def _generate_placeholder(self, channel, topic, tone, key_points, template):
        """Structured placeholder — replace with LLM call in production."""
        hook = f"Here's what nobody tells you about {topic}..."
        points_text = " ".join(f"→ {p}" for p in key_points[:3]) if key_points else f"Key insight about {topic}."
        cta = "Save this for later ↓" if channel == "instagram" else "What's your take?"

        if channel == "instagram":
            return {
                "body": f"{hook}\n\n{points_text}\n\n{cta}",
                "hook": hook, "cta": cta,
                "hashtags": [f"#{topic.replace(' ', '')}", "#growth", "#marketing", "#strategy"],
                "channel_metadata": {"carousel_slides": None, "aspect_ratio": "1:1"},
                "media_instructions": f"Create a clean infographic about {topic} with bold typography.",
            }
        elif channel == "tiktok":
            return {
                "body": f"HOOK: {hook}\n\nBODY: {points_text}\n\nCTA: {cta}",
                "hook": hook, "cta": cta, "hashtags": [f"#{topic.replace(' ', '')}", "#fyp"],
                "channel_metadata": {
                    "script_sections": [
                        {"time": "0-3s", "text": hook, "visual": "face to camera"},
                        {"time": "3-15s", "text": points_text, "visual": "b-roll or text overlay"},
                        {"time": "15-20s", "text": cta, "visual": "face to camera"},
                    ],
                    "duration_target": 20, "music_suggestion": "trending audio",
                },
                "media_instructions": f"Short-form video about {topic}. Hook-first, fast cuts.",
            }
        elif channel == "twitter":
            return {
                "body": hook,
                "hook": hook, "cta": cta, "hashtags": [],
                "channel_metadata": {
                    "thread": [
                        hook,
                        points_text,
                        cta + " 🧵",
                    ]
                },
                "media_instructions": None,
            }
        elif channel == "linkedin":
            return {
                "body": f"{hook}\n\n{points_text}\n\nThe takeaway? {cta}\n\n#marketing #{topic.replace(' ', '')}",
                "hook": hook, "cta": cta, "hashtags": [f"#{topic.replace(' ', '')}", "#leadership"],
                "channel_metadata": {"article_mode": False},
                "media_instructions": f"Professional graphic or photo related to {topic}.",
            }
        elif channel == "meta_ads":
            return {
                "body": f"{hook} {points_text}",
                "hook": hook, "cta": "Learn More",
                "hashtags": [],
                "channel_metadata": {
                    "headline": f"Unlock the Power of {topic.title()}",
                    "description": f"Discover how {topic} can transform your results.",
                    "audience_angle": f"People interested in {topic} and growth",
                    "placement": ["feed", "stories"],
                },
                "media_instructions": f"Eye-catching ad creative about {topic}.",
            }
        return {"body": f"Post about {topic}", "hook": hook, "cta": cta}


# ═════════════════════════════════════════════════════════════════════════════
#  5. AD CAMPAIGN GENERATOR AGENT
# ═════════════════════════════════════════════════════════════════════════════

class AdCampaignGeneratorAgent(BaseMarketingAgent):
    name = "ad_campaign_generator"
    description = "Generates Meta Ads campaign structures with ad copy and targeting."
    permissions = [ToolPermission.MANAGE_ADS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        p = input.payload
        ad_campaign = {
            "name": p.get("name", "New Ad Campaign"),
            "objective": p.get("objective", "traffic"),
            "ad_sets": [
                {
                    "name": "Broad Interest",
                    "targeting": {"interests": p.get("interests", []), "age_min": 25, "age_max": 55},
                    "budget_share": 0.5,
                },
                {
                    "name": "Lookalike",
                    "targeting": {"lookalike_source": "website_visitors", "age_min": 25, "age_max": 55},
                    "budget_share": 0.3,
                },
                {
                    "name": "Retargeting",
                    "targeting": {"custom_audience": "website_visitors_30d"},
                    "budget_share": 0.2,
                },
            ],
            "ad_creatives": [
                {
                    "variant": "A",
                    "primary_text": p.get("primary_text", "Discover what's possible."),
                    "headline": p.get("headline", "Transform Your Growth"),
                    "description": p.get("description", "Start today."),
                    "cta": "Learn More",
                },
                {
                    "variant": "B",
                    "primary_text": f"Still {p.get('pain_point', 'struggling with growth')}?",
                    "headline": f"The {p.get('solution', 'AI-Powered')} Solution",
                    "description": "See the difference.",
                    "cta": "Sign Up",
                },
            ],
            "daily_budget": p.get("daily_budget", 20.0),
            "status": "PAUSED",  # Always start paused
        }
        return self._output(True, {"ad_campaign": ad_campaign}, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  6. HOOK OPTIMIZATION AGENT
# ═════════════════════════════════════════════════════════════════════════════

class HookOptimizationAgent(BaseMarketingAgent):
    name = "hook_optimization"
    description = "Generates and scores attention hooks for content across channels."
    permissions = [ToolPermission.LLM_GENERATE]

    HOOK_PATTERNS = [
        "contrarian",       # "Everyone says X, but here's why Y"
        "curiosity_gap",    # "I discovered something about X that changed everything"
        "number_driven",    # "3 things about X that will surprise you"
        "question",         # "What if I told you X?"
        "story_open",       # "Last week, I made a mistake that taught me X"
        "bold_claim",       # "X is dead. Here's what's replacing it"
        "social_proof",     # "After helping 100+ companies with X..."
    ]

    async def execute(self, input: AgentInput) -> AgentOutput:
        topic = input.payload.get("topic", "growth")
        channel = input.payload.get("channel", "instagram")
        num_hooks = input.payload.get("num_hooks", 5)

        hooks = []
        for i, pattern in enumerate(self.HOOK_PATTERNS[:num_hooks]):
            hooks.append({
                "text": self._generate_hook(pattern, topic),
                "pattern": pattern,
                "predicted_score": round(0.5 + (0.5 * (num_hooks - i) / num_hooks), 2),
                "channel_fit": channel,
            })

        return self._output(True, {"hooks": hooks}, trace_id=input.trace_id)

    def _generate_hook(self, pattern, topic):
        templates = {
            "contrarian": f"Everyone says {topic} works this way — they're wrong.",
            "curiosity_gap": f"I discovered something about {topic} that nobody talks about.",
            "number_driven": f"3 {topic} strategies that outperform everything else.",
            "question": f"What if everything you knew about {topic} was outdated?",
            "story_open": f"I failed at {topic} for 2 years. Then I found this.",
            "bold_claim": f"Traditional {topic} is dead. Here's what's next.",
            "social_proof": f"After analyzing 500+ {topic} campaigns, here's what actually works.",
        }
        return templates.get(pattern, f"The truth about {topic}.")


# ═════════════════════════════════════════════════════════════════════════════
#  7. HASHTAG STRATEGY AGENT
# ═════════════════════════════════════════════════════════════════════════════

class HashtagStrategyAgent(BaseMarketingAgent):
    name = "hashtag_strategy"
    description = "Generates optimized hashtag sets by channel and niche."
    permissions = [ToolPermission.READ_ANALYTICS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        topic = input.payload.get("topic", "marketing")
        channel = input.payload.get("channel", "instagram")
        niche = input.payload.get("niche", "saas")

        # Structured hashtag tiers
        hashtags = {
            "primary": [f"#{topic.replace(' ', '')}", f"#{niche}"],
            "secondary": [f"#{topic.replace(' ', '')}tips", f"#{niche}growth", "#digitalmarketing"],
            "niche": [f"#{niche}founders", f"#{topic.replace(' ', '')}strategy"],
            "trending": ["#growthhacking", "#ai", "#startup"],
            "branded": [],  # User fills in
        }

        strategy = {
            "hashtags": hashtags,
            "total_count": sum(len(v) for v in hashtags.values()),
            "recommended_count": 15 if channel == "instagram" else 5,
            "mix_ratio": "40% primary, 30% secondary, 20% niche, 10% trending",
        }

        return self._output(True, {"hashtag_strategy": strategy}, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  8. AUDIENCE TARGETING AGENT
# ═════════════════════════════════════════════════════════════════════════════

class AudienceTargetingAgent(BaseMarketingAgent):
    name = "audience_targeting"
    description = "Builds audience personas and targeting recommendations."
    permissions = [ToolPermission.READ_ANALYTICS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        product = input.payload.get("product", "SaaS tool")
        current_audience = input.payload.get("current_audience", {})

        personas = [
            {
                "name": "Growth-Focused Founder",
                "demographics": {"age": "28-45", "role": "Founder/CEO", "company_size": "1-50"},
                "interests": ["startup growth", "AI tools", "marketing automation"],
                "pain_points": ["limited time", "budget constraints", "scaling content"],
                "channels": ["linkedin", "twitter"],
                "content_preferences": ["data-driven insights", "case studies", "quick tips"],
            },
            {
                "name": "Marketing Manager",
                "demographics": {"age": "25-40", "role": "Marketing Manager", "company_size": "50-500"},
                "interests": ["SEO", "content marketing", "social media strategy"],
                "pain_points": ["proving ROI", "content volume", "multi-channel management"],
                "channels": ["instagram", "linkedin", "tiktok"],
                "content_preferences": ["how-tos", "templates", "trend analysis"],
            },
            {
                "name": "Agency Owner",
                "demographics": {"age": "30-50", "role": "Agency Founder", "company_size": "5-30"},
                "interests": ["client growth", "efficiency", "white-label tools"],
                "pain_points": ["client retention", "scaling operations", "talent"],
                "channels": ["linkedin", "twitter"],
                "content_preferences": ["industry insights", "tool reviews", "efficiency hacks"],
            },
        ]

        return self._output(True, {"personas": personas, "total": len(personas)}, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
#  9. POST TIMING AGENT
# ═════════════════════════════════════════════════════════════════════════════

class PostTimingAgent(BaseMarketingAgent):
    name = "post_timing"
    description = "Recommends optimal posting times based on channel and audience data."
    permissions = [ToolPermission.READ_ANALYTICS]

    OPTIMAL_TIMES = {
        "instagram": {"weekday": ["09:00", "12:00", "18:00"], "weekend": ["10:00", "14:00"]},
        "tiktok": {"weekday": ["07:00", "12:00", "19:00", "22:00"], "weekend": ["09:00", "14:00", "19:00"]},
        "twitter": {"weekday": ["08:00", "12:00", "17:00"], "weekend": ["09:00", "12:00"]},
        "linkedin": {"weekday": ["07:30", "10:00", "12:00", "17:00"], "weekend": []},
        "meta_ads": {"weekday": ["06:00", "12:00", "18:00"], "weekend": ["08:00", "14:00"]},
    }

    async def execute(self, input: AgentInput) -> AgentOutput:
        channel = input.payload.get("channel", "instagram")
        timezone = input.payload.get("timezone", "UTC")

        times = self.OPTIMAL_TIMES.get(channel, self.OPTIMAL_TIMES["instagram"])
        return self._output(True, {
            "channel": channel,
            "timezone": timezone,
            "optimal_times": times,
            "best_days": ["Tuesday", "Wednesday", "Thursday"] if channel == "linkedin" else
                         ["Monday", "Wednesday", "Friday"],
            "avoid": ["Sunday late night", "Monday early morning"],
        }, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
# 10. ENGAGEMENT OPTIMIZATION AGENT
# ═════════════════════════════════════════════════════════════════════════════

class EngagementOptimizationAgent(BaseMarketingAgent):
    name = "engagement_optimization"
    description = "Analyzes content performance and suggests optimization strategies."
    permissions = [ToolPermission.READ_ANALYTICS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        performance_data = input.payload.get("performance_data", [])
        channel = input.payload.get("channel", "all")

        recommendations = [
            {"type": "hook", "suggestion": "Use question-based hooks — they get 2x more comments."},
            {"type": "timing", "suggestion": "Shift posting 1 hour earlier for better reach."},
            {"type": "format", "suggestion": "Carousels outperform single images by 3x on Instagram."},
            {"type": "cta", "suggestion": "End posts with a discussion question instead of a link."},
            {"type": "hashtags", "suggestion": "Reduce hashtag count to 8-12 for optimal reach."},
        ]

        return self._output(True, {
            "recommendations": recommendations,
            "channel": channel,
            "analysis_based_on": len(performance_data),
        }, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
# 11. A/B VARIANT GENERATOR AGENT
# ═════════════════════════════════════════════════════════════════════════════

class ABVariantGeneratorAgent(BaseMarketingAgent):
    name = "ab_variant_generator"
    description = "Creates A/B test variants of content with systematic differences."
    permissions = [ToolPermission.WRITE_CONTENT, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        original = input.payload.get("original_content", {})
        num_variants = input.payload.get("num_variants", 2)
        test_dimension = input.payload.get("test_dimension", "hook")  # hook, cta, tone, format

        variant_group = uuid.uuid4().hex
        variants = [{"variant_label": "A", "content": original, "is_control": True}]

        for i in range(1, num_variants):
            label = chr(65 + i)  # B, C, D...
            variant = dict(original)
            if test_dimension == "hook":
                variant["hook"] = f"[Variant {label} hook] " + original.get("hook", "")
            elif test_dimension == "cta":
                ctas = ["Save this ↓", "Share with a friend", "Drop a 🔥 if you agree", "Link in bio"]
                variant["cta"] = ctas[i % len(ctas)]
            elif test_dimension == "tone":
                variant["body"] = f"[{label} tone variant] " + original.get("body", "")

            variants.append({"variant_label": label, "content": variant, "is_control": False})

        return self._output(True, {
            "variant_group": variant_group,
            "variants": variants,
            "test_dimension": test_dimension,
        }, trace_id=input.trace_id)


# ═════════════════════════════════════════════════════════════════════════════
# 12. CONTENT REPURPOSING AGENT
# ═════════════════════════════════════════════════════════════════════════════

class ContentRepurposingAgent(BaseMarketingAgent):
    name = "content_repurposing"
    description = "Takes one piece of content and generates multi-channel variants."
    permissions = [ToolPermission.WRITE_CONTENT, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        """
        Input: { source_text, source_type, target_channels }
        Output: { repurposed: [ { channel, content } ] }
        """
        source = input.payload.get("source_text", "")
        channels = input.payload.get("target_channels", ["instagram", "twitter", "linkedin", "tiktok"])

        # Lazily cache the post generator — avoid creating per-call
        if not hasattr(self, '_post_gen'):
            self._post_gen = SocialPostGeneratorAgent()
        repurposed = []

        for ch in channels:
            gen_input = AgentInput(
                workspace_id=input.workspace_id,
                payload={
                    "topic": source[:200],
                    "channel": ch,
                    "key_points": self._extract_key_points(source),
                },
                trace_id=input.trace_id,
            )
            result = await self._post_gen.execute(gen_input)
            if result.success:
                repurposed.append({"channel": ch, "content": result.data.get("post", {})})

        return self._output(True, {
            "repurposed": repurposed,
            "source_length": len(source),
            "channels_generated": len(repurposed),
        }, trace_id=input.trace_id)

    def _extract_key_points(self, text: str, max_points: int = 5) -> list[str]:
        """Simple extraction — in production, use LLM."""
        sentences = text.split(". ")
        return [s.strip()[:100] for s in sentences[:max_points] if len(s.strip()) > 20]


# ═════════════════════════════════════════════════════════════════════════════
# 13. PERFORMANCE FEEDBACK AGENT
# ═════════════════════════════════════════════════════════════════════════════

class PerformanceFeedbackAgent(BaseMarketingAgent):
    name = "performance_feedback"
    description = "Analyzes campaign/content performance and generates actionable feedback."
    permissions = [ToolPermission.READ_ANALYTICS, ToolPermission.LLM_GENERATE]

    async def execute(self, input: AgentInput) -> AgentOutput:
        metrics = input.payload.get("metrics", [])
        channel = input.payload.get("channel")

        if not metrics:
            return self._output(True, {
                "feedback": "No performance data available yet. Publish content to start tracking.",
                "recommendations": [],
            }, trace_id=input.trace_id)

        # Analyze aggregate metrics
        total_impressions = sum(m.get("impressions", 0) for m in metrics)
        total_engagement = sum(m.get("likes", 0) + m.get("comments", 0) + m.get("shares", 0) for m in metrics)
        avg_er = (total_engagement / max(total_impressions, 1)) * 100

        feedback = {
            "summary": {
                "total_posts": len(metrics),
                "total_impressions": total_impressions,
                "total_engagement": total_engagement,
                "avg_engagement_rate": round(avg_er, 2),
            },
            "insights": [
                f"Average engagement rate: {avg_er:.1f}% ({'above' if avg_er > 3 else 'below'} industry avg)",
                f"Total reach across {len(metrics)} posts: {total_impressions:,} impressions",
            ],
            "recommendations": [
                "Double down on content formats that drive saves and shares.",
                "Test posting 2 hours earlier for improved reach.",
                "Increase video content — it typically gets 2-3x more engagement.",
            ],
        }

        return self._output(True, {"feedback": feedback}, trace_id=input.trace_id)


# ─── Agent Registry ──────────────────────────────────────────────────────────

MARKETING_AGENTS = {
    "campaign_planner": CampaignPlannerAgent,
    "content_calendar": ContentCalendarAgent,
    "channel_strategy": ChannelStrategyAgent,
    "social_post_generator": SocialPostGeneratorAgent,
    "ad_campaign_generator": AdCampaignGeneratorAgent,
    "hook_optimization": HookOptimizationAgent,
    "hashtag_strategy": HashtagStrategyAgent,
    "audience_targeting": AudienceTargetingAgent,
    "post_timing": PostTimingAgent,
    "engagement_optimization": EngagementOptimizationAgent,
    "ab_variant_generator": ABVariantGeneratorAgent,
    "content_repurposing": ContentRepurposingAgent,
    "performance_feedback": PerformanceFeedbackAgent,
}


def get_agent(name: str) -> BaseMarketingAgent:
    cls = MARKETING_AGENTS.get(name)
    if not cls:
        raise ValueError(f"Unknown marketing agent: {name}")
    return cls()
