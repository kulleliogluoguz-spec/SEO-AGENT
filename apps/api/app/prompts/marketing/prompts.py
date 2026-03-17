"""
Marketing Prompt Registry — Versioned, Channel-Specific Prompts
Used by marketing agents when calling LLMs.
"""
from __future__ import annotations

PROMPT_VERSION = "1.0.0"

# ═════════════════════════════════════════════════════════════════════════════
#  SOCIAL POST GENERATION PROMPTS
# ═════════════════════════════════════════════════════════════════════════════

INSTAGRAM_POST_PROMPT = """You are a social media strategist specializing in Instagram.
Generate an Instagram post for the following:

TOPIC: {topic}
TONE: {tone}
KEY POINTS: {key_points}
FUNNEL STAGE: {funnel_stage}
TARGET PERSONA: {persona}

Requirements:
- Write a compelling hook (first line must stop the scroll)
- Body should deliver value in 3-5 short paragraphs
- Include a clear CTA
- Suggest 10-15 relevant hashtags (mix of broad + niche)
- Include media/visual instructions
- Max 2200 characters
- Use line breaks for readability
- No spam language, no fake engagement tactics

Output JSON:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["..."],
  "media_instructions": "...",
  "channel_metadata": {{
    "carousel_slides": null,
    "aspect_ratio": "1:1"
  }}
}}"""

TIKTOK_SCRIPT_PROMPT = """You are a TikTok content strategist.
Generate a TikTok video script:

TOPIC: {topic}
TONE: {tone}
KEY POINTS: {key_points}
TARGET DURATION: 15-60 seconds

Requirements:
- Hook must grab attention in first 2-3 seconds
- Use pattern interrupts to maintain retention
- Conversational, authentic voice
- Clear CTA at the end
- Include visual direction for each section

Output JSON:
{{
  "hook": "...",
  "body": "HOOK: ...\\nBODY: ...\\nCTA: ...",
  "cta": "...",
  "hashtags": ["..."],
  "media_instructions": "...",
  "channel_metadata": {{
    "script_sections": [
      {{"time": "0-3s", "text": "...", "visual": "..."}},
      {{"time": "3-15s", "text": "...", "visual": "..."}},
      {{"time": "15-25s", "text": "...", "visual": "..."}}
    ],
    "duration_target": 25,
    "music_suggestion": "..."
  }}
}}"""

TWITTER_THREAD_PROMPT = """You are a Twitter/X engagement strategist.
Generate a Twitter thread:

TOPIC: {topic}
TONE: {tone}
KEY POINTS: {key_points}

Requirements:
- First tweet is the hook (must be compelling standalone)
- Each tweet max 280 characters
- Thread should be 3-7 tweets
- Final tweet has CTA
- Sharp, insight-driven writing
- No excessive hashtags (1-2 max per tweet)

Output JSON:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": [],
  "channel_metadata": {{
    "thread": ["tweet 1", "tweet 2", "tweet 3", "..."]
  }}
}}"""

LINKEDIN_POST_PROMPT = """You are a LinkedIn content strategist.
Generate a LinkedIn post:

TOPIC: {topic}
TONE: {tone}
KEY POINTS: {key_points}
FUNNEL STAGE: {funnel_stage}

Requirements:
- Professional but engaging first line (hook)
- Story-driven or insight-led structure
- End with a discussion question or clear takeaway
- 1-3 relevant hashtags
- Max 3000 characters
- Use white space / line breaks strategically

Output JSON:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["..."],
  "media_instructions": "...",
  "channel_metadata": {{
    "article_mode": false,
    "document_carousel": false
  }}
}}"""

META_ADS_PROMPT = """You are a paid social advertising strategist.
Generate Meta Ads copy:

PRODUCT/SERVICE: {topic}
OBJECTIVE: {objective}
KEY BENEFITS: {key_points}
TARGET AUDIENCE: {persona}

Requirements:
- Primary text: max 125 chars (benefit-driven)
- Headline: max 40 chars (clear value proposition)
- Description: max 125 chars (supporting detail)
- Audience angle: who this speaks to and why
- No deceptive claims, no false urgency
- Must comply with Meta Advertising Policies

Output JSON:
{{
  "hook": "...",
  "body": "...",
  "cta": "Learn More",
  "hashtags": [],
  "channel_metadata": {{
    "headline": "...",
    "description": "...",
    "audience_angle": "...",
    "placement": ["feed", "stories"]
  }}
}}"""


# ═════════════════════════════════════════════════════════════════════════════
#  CAMPAIGN PLANNING PROMPT
# ═════════════════════════════════════════════════════════════════════════════

CAMPAIGN_PLAN_PROMPT = """You are a growth marketing strategist.
Create a comprehensive campaign plan:

OBJECTIVE: {objective}
CHANNELS: {channels}
BUDGET: ${budget}
DURATION: {duration_days} days
INDUSTRY: {industry}

Generate a structured plan with:
1. Campaign phases (launch, engage, convert)
2. Content themes per phase
3. Channel-specific strategies
4. KPI targets
5. Posting cadence per channel
6. Budget allocation

Output as structured JSON."""


# ═════════════════════════════════════════════════════════════════════════════
#  REPURPOSING PROMPT
# ═════════════════════════════════════════════════════════════════════════════

REPURPOSE_PROMPT = """You are a content repurposing strategist.
Take the following content and create a {channel} post:

ORIGINAL CONTENT:
{source_text}

SOURCE TYPE: {source_type}
TARGET CHANNEL: {channel}
TONE: {tone}

Rules:
- Extract the most compelling insight or takeaway
- Adapt format and length for the target channel
- Maintain the core message but optimize for the platform
- Add appropriate hooks and CTAs for the channel
- Do NOT simply copy-paste or truncate

Output the post in the channel's format."""


# ═════════════════════════════════════════════════════════════════════════════
#  PROMPT REGISTRY
# ═════════════════════════════════════════════════════════════════════════════

PROMPT_REGISTRY = {
    "instagram_post": {"template": INSTAGRAM_POST_PROMPT, "version": PROMPT_VERSION},
    "tiktok_script": {"template": TIKTOK_SCRIPT_PROMPT, "version": PROMPT_VERSION},
    "twitter_thread": {"template": TWITTER_THREAD_PROMPT, "version": PROMPT_VERSION},
    "linkedin_post": {"template": LINKEDIN_POST_PROMPT, "version": PROMPT_VERSION},
    "meta_ads_copy": {"template": META_ADS_PROMPT, "version": PROMPT_VERSION},
    "campaign_plan": {"template": CAMPAIGN_PLAN_PROMPT, "version": PROMPT_VERSION},
    "repurpose": {"template": REPURPOSE_PROMPT, "version": PROMPT_VERSION},
}


def get_prompt(name: str, **kwargs) -> str:
    entry = PROMPT_REGISTRY.get(name)
    if not entry:
        raise ValueError(f"Prompt not found: {name}")
    return entry["template"].format(**kwargs)
