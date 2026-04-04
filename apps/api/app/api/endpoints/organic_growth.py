"""
Organic Growth Engine
Strategies drawn from github.com/coreyhaines31/marketingskills:
  ai-seo, social-content, cold-email, competitor-alternatives,
  lead-magnets, referral-program, content-strategy

All AI calls use local Ollama qwen3:8b — zero external API cost.
"""

import json
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

# No prefix here — main.py registers with prefix="/api/v1/organic"
router = APIRouter(tags=["organic-growth"])


# ─── Request Models (match frontend field names exactly) ─────────────────────

class GrowthScoreRequest(BaseModel):
    business_name: str = ""
    industry: str = ""
    target_audience: str = ""
    current_monthly_revenue: str = ""
    main_product_service: str = ""
    geographic_focus: str = ""
    current_channels: List[str] = []
    monthly_budget: str = "0"
    team_size: str = "1"
    biggest_challenge: str = ""


class SEOAnalyzeRequest(BaseModel):
    topic: str
    target_audience: str
    industry: str = ""


class ContentBriefRequest(BaseModel):
    keyword: str
    target_audience: str = ""
    industry: str = ""


class SocialStrategyRequest(BaseModel):
    target_audience: str
    niche: str
    platform_focus: str = "both"
    current_followers: int = 0


class HookRequest(BaseModel):
    topic: str
    target_audience: str
    platform: str = "twitter"
    frameworks: Optional[List[str]] = None


class AudienceIntelRequest(BaseModel):
    product_service: str
    target_audience: str
    industry: str = ""


class OutreachStrategyRequest(BaseModel):
    business_type: str
    target_audience: str
    industry: str = ""
    monthly_budget: int = 0


class GrowthLoopRequest(BaseModel):
    business_model: str
    target_audience: str
    current_channels: List[str] = []


# ─── Ollama helper ───────────────────────────────────────────────────────────

async def ask_ollama(prompt: str) -> str:
    """Call local Ollama qwen3:8b. No external API calls."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3:8b", "prompt": prompt, "stream": False}
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception as e:
        return f"AI unavailable: {e}"
    return ""


def extract_json(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


# ─── Growth Score ─────────────────────────────────────────────────────────────

@router.post("/growth-score")
async def calculate_growth_score(req: GrowthScoreRequest):
    """Organic growth score with channel breakdown, quick wins, 30-day plan."""
    channels = ", ".join(req.current_channels) if req.current_channels else "none"
    prompt = f"""You are an expert organic growth strategist. Analyze this business and output a growth score.

Business: {req.business_name or 'unnamed'}
Industry: {req.industry}
Target Audience: {req.target_audience}
Main Product/Service: {req.main_product_service}
Geographic Focus: {req.geographic_focus}
Monthly Revenue: {req.current_monthly_revenue}
Monthly Budget: ${req.monthly_budget}
Team Size: {req.team_size}
Active Channels: {channels}
Biggest Challenge: {req.biggest_challenge}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "overall_score": 45,
    "channel_scores": {{"Twitter/X": 60, "SEO": 30, "Instagram": 50, "Email": 20}},
    "quick_wins": [
        "Specific action #1 the business can do today",
        "Specific action #2 that takes under 1 hour",
        "Specific action #3 for this week",
        "Specific action #4 for this month"
    ],
    "thirty_day_plan": [
        "Week 1: Foundation — specific focus and 2-3 concrete actions",
        "Week 2: Content — specific focus and 2-3 concrete actions",
        "Week 3: Distribution — specific focus and 2-3 concrete actions",
        "Week 4: Optimization — specific focus and 2-3 concrete actions"
    ],
    "channel_priority": ["Twitter/X", "SEO", "Email"],
    "biggest_opportunity": "The single most impactful opportunity for this specific business",
    "risk_factors": ["risk 1 relevant to their situation", "risk 2"]
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Analysis failed — is Ollama running?", "raw": response[:300]}
    return data


# ─── SEO Intelligence ─────────────────────────────────────────────────────────

@router.post("/seo/analyze")
async def analyze_seo(req: SEOAnalyzeRequest):
    """Keyword research, content calendar, technical checklist."""
    prompt = f"""You are an expert SEO strategist. Create a complete organic SEO strategy.

Topic/Niche: {req.topic}
Target Audience: {req.target_audience}
Industry: {req.industry}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "primary_keywords": [
        "main keyword 1",
        "main keyword 2",
        "main keyword 3",
        "main keyword 4",
        "main keyword 5"
    ],
    "long_tail_keywords": [
        "specific long-tail keyword 1",
        "specific long-tail keyword 2",
        "specific long-tail keyword 3",
        "specific long-tail keyword 4",
        "specific long-tail keyword 5",
        "specific long-tail keyword 6"
    ],
    "content_calendar": [
        {{"week": 1, "topic": "Article title week 1", "keyword": "target keyword", "format": "How-to guide"}},
        {{"week": 2, "topic": "Article title week 2", "keyword": "target keyword", "format": "List post"}},
        {{"week": 3, "topic": "Article title week 3", "keyword": "target keyword", "format": "Case study"}},
        {{"week": 4, "topic": "Article title week 4", "keyword": "target keyword", "format": "Comparison"}}
    ],
    "technical_checklist": [
        "Add XML sitemap to Google Search Console",
        "Improve page speed to under 3 seconds",
        "Add schema markup to key pages",
        "Optimize all meta descriptions",
        "Fix broken internal links",
        "Enable HTTPS if not already done",
        "Add alt text to all images"
    ],
    "competitor_gaps": [
        "Content gap opportunity 1",
        "Content gap opportunity 2",
        "Content gap opportunity 3"
    ],
    "estimated_traffic_potential": "2,000–5,000 organic visitors/month at 6 months",
    "time_to_rank": "3–6 months with consistent publishing"
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "SEO analysis failed", "raw": response[:300]}
    return data


@router.post("/seo/content-brief")
async def generate_content_brief(req: ContentBriefRequest):
    """Full SEO content brief for a specific keyword."""
    prompt = f"""Create a detailed SEO content brief for the keyword "{req.keyword}".
Target Audience: {req.target_audience}
Industry: {req.industry}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "title": "SEO-optimized article title including the keyword",
    "meta_description": "Compelling 155-character meta description with keyword",
    "outline": [
        "Introduction — hook + what reader will learn",
        "Section 1: First major topic",
        "Section 2: Second major topic",
        "Section 3: Third major topic",
        "Section 4: Common mistakes to avoid",
        "Conclusion — summary + CTA"
    ],
    "word_count_target": 1800,
    "internal_links": [
        "Link to homepage",
        "Link to product/service page",
        "Link to related blog post"
    ],
    "call_to_action": "Specific CTA that aligns with the content goal",
    "seo_tips": [
        "Use the keyword in H1, first paragraph, and 2-3 H2s",
        "Add 3-5 images with keyword-rich alt text",
        "Include an FAQ section with voice-search questions",
        "Get 2-3 backlinks from guest posts within 30 days of publishing"
    ]
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    return data or {"error": "Brief generation failed"}


# ─── Social Media Organic Growth ─────────────────────────────────────────────

@router.post("/social/strategy")
async def get_social_strategy(req: SocialStrategyRequest):
    """Platform-specific organic growth strategy with follower projections."""
    prompt = f"""You are a social media organic growth expert. Create a strategy to reach the target audience for FREE.

Target Audience: {req.target_audience}
Niche: {req.niche}
Platform Focus: {req.platform_focus}
Current Followers: {req.current_followers}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "twitter_strategy": {{
        "content_pillars": [
            "Educational threads on niche topics",
            "Hot takes and contrarian opinions",
            "Behind-the-scenes and personal stories",
            "Engagement questions and polls"
        ],
        "posting_frequency": "3 posts per day",
        "best_times": ["9am ET", "12pm ET", "6pm ET"],
        "thread_topics": [
            "Thread topic idea 1 specific to the niche",
            "Thread topic idea 2",
            "Thread topic idea 3",
            "Thread topic idea 4",
            "Thread topic idea 5"
        ],
        "engagement_tactics": [
            "Reply to 10 posts in your niche daily",
            "Quote-tweet top performers with your take",
            "Follow 50 target audience accounts per day"
        ],
        "growth_hacks": [
            "Specific growth hack 1 for this niche",
            "Specific growth hack 2",
            "Specific growth hack 3"
        ]
    }},
    "instagram_strategy": {{
        "content_mix": {{"Reels": "40%", "Carousels": "35%", "Static posts": "15%", "Stories": "10%"}},
        "posting_frequency": "5 posts per week",
        "hashtag_strategy": ["#niche1", "#niche2", "#niche3", "#niche4", "#niche5"],
        "reel_ideas": [
            "Reel idea 1 specific to this niche",
            "Reel idea 2",
            "Reel idea 3",
            "Reel idea 4"
        ],
        "story_tactics": [
            "Poll about a relevant topic",
            "Behind-the-scenes daily story",
            "Q&A sessions weekly"
        ],
        "growth_hacks": [
            "Instagram growth hack 1",
            "Instagram growth hack 2",
            "Instagram growth hack 3"
        ]
    }},
    "follower_growth_projection": [
        {{"month": 1, "followers": {req.current_followers + 150}, "milestone": "First 150 new followers — foundation built"}},
        {{"month": 2, "followers": {req.current_followers + 400}, "milestone": ""}},
        {{"month": 3, "followers": {req.current_followers + 800}, "milestone": "Algorithm starts amplifying content"}},
        {{"month": 4, "followers": {req.current_followers + 1300}, "milestone": ""}},
        {{"month": 5, "followers": {req.current_followers + 1900}, "milestone": ""}},
        {{"month": 6, "followers": {req.current_followers + 2600}, "milestone": "Sustainable organic growth established"}}
    ],
    "cross_platform_synergies": [
        "Turn Twitter threads into Instagram carousels",
        "Use Instagram Reels audio for TikTok reposts",
        "Convert high-performing posts into email newsletter content"
    ],
    "content_repurposing": [
        "Record one Reel → post clips to Twitter + LinkedIn",
        "Transcribe video → blog post → pull quotes for carousels",
        "Top tweet threads → LinkedIn articles"
    ]
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Strategy generation failed", "raw": response[:300]}
    return data


# ─── Viral Hook Generator ─────────────────────────────────────────────────────

@router.post("/hooks/generate")
async def generate_hooks(req: HookRequest):
    """Viral hooks using proven copywriting frameworks."""
    platform_specs = {
        "twitter": "280 chars max, punchy, stops the scroll",
        "instagram": "first line before 'more' cutoff, emoji-friendly",
        "linkedin": "professional, first 3 lines before 'see more' matter most",
        "tiktok": "first 2 seconds of spoken word or on-screen text",
        "email": "subject line, 50 chars ideal",
    }
    fw_text = ", ".join(req.frameworks) if req.frameworks else "curiosity gap, contrarian, social proof, pain point, story, data-driven"
    prompt = f"""You are a viral copywriting expert. Generate hooks that stop the scroll.

Platform: {req.platform} — {platform_specs.get(req.platform, 'general')}
Topic: {req.topic}
Audience: {req.target_audience}
Frameworks to use: {fw_text}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "hooks": [
        {{
            "framework": "Curiosity Gap",
            "hook": "The actual hook text goes here — platform-appropriate length",
            "explanation": "Why this hook works for this specific audience and topic",
            "engagement_score": 8,
            "variations": [
                "Variation A of this hook",
                "Variation B with different angle"
            ]
        }},
        {{
            "framework": "Contrarian",
            "hook": "The contrarian hook text",
            "explanation": "Why contrarian works here",
            "engagement_score": 9,
            "variations": [
                "Variation A",
                "Variation B"
            ]
        }},
        {{
            "framework": "Social Proof",
            "hook": "The social proof hook text",
            "explanation": "Why social proof works here",
            "engagement_score": 7,
            "variations": [
                "Variation A",
                "Variation B"
            ]
        }},
        {{
            "framework": "Pain Point",
            "hook": "The pain point hook text",
            "explanation": "Why this pain point resonates",
            "engagement_score": 8,
            "variations": [
                "Variation A",
                "Variation B"
            ]
        }},
        {{
            "framework": "Specific Numbers",
            "hook": "A hook with specific numbers or data",
            "explanation": "Why numbers work here",
            "engagement_score": 7,
            "variations": [
                "Variation A",
                "Variation B"
            ]
        }}
    ],
    "best_performing_type": "Contrarian",
    "usage_tips": [
        "Test 2-3 hooks on the same day at different times",
        "The first 3 words determine if someone stops scrolling — make them count",
        "Match the hook energy to your content — don't over-promise"
    ],
    "a_b_test_suggestions": [
        "Test Hook 1 (curiosity) vs Hook 2 (contrarian) — post same day, different times",
        "Test question format vs statement format",
        "Test with numbers vs without numbers"
    ]
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Hook generation failed", "raw": response[:300]}
    return data


# ─── Audience Intelligence ─────────────────────────────────────────────────────

@router.post("/audience/intelligence")
async def get_audience_intelligence(req: AudienceIntelRequest):
    """Deep ICP mapping — free audience targeting methods."""
    prompt = f"""You are an audience intelligence expert. Map out the target audience and how to reach them for free.

Product/Service: {req.product_service}
Target Audience: {req.target_audience}
Industry: {req.industry}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "icp_profiles": [
        {{
            "persona_name": "Primary Persona — give a descriptive name",
            "demographics": "Age range, job title, income level, location in 1-2 sentences",
            "psychographics": [
                "Core value or belief 1",
                "Core value or belief 2",
                "Aspiration they have",
                "Fear they have"
            ],
            "pain_points": [
                "Primary pain point that your product solves",
                "Secondary pain point",
                "Frustration with current solutions"
            ],
            "goals": [
                "What they want to achieve",
                "How they measure success",
                "Timeline they're working on"
            ],
            "where_they_hang_out": [
                "Twitter — specific accounts/hashtags they follow",
                "Reddit — specific subreddit name",
                "LinkedIn groups",
                "Slack communities",
                "Specific websites or newsletters"
            ],
            "buying_triggers": [
                "Event that makes them ready to buy",
                "Emotional trigger",
                "Practical trigger"
            ]
        }},
        {{
            "persona_name": "Secondary Persona — give a descriptive name",
            "demographics": "Age range, job title, income level in 1-2 sentences",
            "psychographics": [
                "Core value 1",
                "Core value 2"
            ],
            "pain_points": [
                "Pain point 1",
                "Pain point 2"
            ],
            "goals": [
                "Goal 1",
                "Goal 2"
            ],
            "where_they_hang_out": [
                "Platform 1 — specifics",
                "Platform 2 — specifics"
            ],
            "buying_triggers": [
                "Trigger 1",
                "Trigger 2"
            ]
        }}
    ],
    "free_targeting_methods": [
        "Search Twitter for '[keyword]' — engage top posts daily",
        "Join Reddit r/[specific subreddit] — answer questions before promoting",
        "Monitor Instagram hashtag #[relevant] — comment genuinely on 20 posts/day",
        "Engage competitor followers on Twitter — follow 50/day",
        "Answer questions on Quora in your niche — include link in bio"
    ],
    "communities_to_join": [
        "Reddit r/[specific community]",
        "Facebook Group: [community type]",
        "Slack: [community name or type]",
        "Discord: [community type]",
        "LinkedIn Group: [group type]"
    ],
    "influencers_to_engage": [
        "Micro-influencers (5k-50k) in [niche] — more engaged audiences",
        "Newsletter writers covering [topic]",
        "Podcast hosts interviewing [audience type]",
        "YouTube creators with [audience type] subscribers"
    ],
    "outreach_templates": [
        {{
            "channel": "Twitter DM",
            "template": "Hey [name], saw your post about [specific topic] — great point about [specific thing]. I've been building something that helps with exactly [their pain point]. Mind if I share a quick look?",
            "personalization_tips": [
                "Reference a specific post they made",
                "Engage with their content 2-3 times before DM-ing",
                "Keep under 280 characters"
            ]
        }},
        {{
            "channel": "Cold Email",
            "template": "Subject: [Specific result] for [their company type]\\n\\nHi [name],\\n\\nI noticed [specific observation about them]. I help [their type] achieve [specific result] — [one proof point].\\n\\nWould a 10-min call this week be useful?\\n\\n[Your name]",
            "personalization_tips": [
                "Research their LinkedIn before emailing",
                "Reference something specific about their business",
                "Keep the ask small — 10 min call, not a demo"
            ]
        }}
    ],
    "audience_segments": [
        "Segment 1: [describe segment]",
        "Segment 2: [describe segment]",
        "Segment 3: [describe segment]"
    ],
    "content_themes_by_segment": {{
        "Segment 1": ["Theme A", "Theme B", "Theme C"],
        "Segment 2": ["Theme D", "Theme E"],
        "Segment 3": ["Theme F", "Theme G"]
    }}
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Audience analysis failed", "raw": response[:300]}
    return data


# ─── Free Outreach / User Acquisition ────────────────────────────────────────

@router.post("/outreach/strategy")
async def get_outreach_strategy(req: OutreachStrategyRequest):
    """Zero-budget acquisition channels + cold email sequences + growth loop."""
    prompt = f"""Create a complete zero-budget user acquisition strategy.

Business Type: {req.business_type}
Target Audience: {req.target_audience}
Industry: {req.industry}
Monthly Budget: ${req.monthly_budget}

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "acquisition_channels": [
        {{
            "channel": "Twitter Organic",
            "effort": "Medium",
            "time_to_results": "4-8 weeks",
            "tactics": [
                "Post a value thread every Tuesday",
                "Reply to 10 industry posts daily",
                "Follow 50 target audience accounts per day"
            ],
            "free_tools": ["Buffer free tier", "Twitter Analytics", "Followerwonk free"]
        }},
        {{
            "channel": "Reddit Communities",
            "effort": "Low",
            "time_to_results": "2-4 weeks",
            "tactics": [
                "Answer 3 questions per day in niche subreddits",
                "Share case studies with transparent results",
                "Build 10+ karma before any mention of your product"
            ],
            "free_tools": ["Reddit search", "Reddit analytics (native)"]
        }},
        {{
            "channel": "Cold Outreach",
            "effort": "High",
            "time_to_results": "1-2 weeks",
            "tactics": [
                "Send 20 personalized cold emails per day",
                "DM engaged Twitter users after engaging with their content",
                "LinkedIn connection requests with a specific value offer"
            ],
            "free_tools": ["Gmail", "Hunter.io free tier", "LinkedIn free"]
        }}
    ],
    "cold_email_sequences": [
        {{
            "sequence_name": "Outbound Prospects",
            "emails": [
                {{
                    "subject": "Quick question about [their specific situation]",
                    "body": "Hi [name],\\n\\nI noticed [specific observation about them or their company].\\n\\nI help {req.business_type}s achieve [specific result] — [one-line proof point].\\n\\nAre you currently dealing with [pain point]?\\n\\n[Your name]",
                    "send_day": 0,
                    "purpose": "Initial outreach — open a conversation, not pitch a product"
                }},
                {{
                    "subject": "Re: Quick question",
                    "body": "Hi [name],\\n\\nFollowing up briefly — I know your inbox is busy.\\n\\nHere's what I mean in one line: [value prop + proof].\\n\\nWorth a 10-min call?\\n\\n[Your name]",
                    "send_day": 3,
                    "purpose": "Follow-up — add social proof, keep it short"
                }},
                {{
                    "subject": "Last one from me",
                    "body": "Hi [name],\\n\\nI'll stop here — clearly not the right time.\\n\\nIf you ever need [result], happy to help. Free resource in the meantime: [link to lead magnet]\\n\\n[Your name]",
                    "send_day": 7,
                    "purpose": "Break-up email — leaves on good terms, provides value"
                }}
            ]
        }}
    ],
    "growth_loop": {{
        "description": "A self-reinforcing loop where each user action brings in new users organically",
        "steps": [
            "User signs up and gets a quick win with your product",
            "They share their result publicly (with your branding visible)",
            "Their network sees the result and asks how they did it",
            "New users sign up — loop repeats"
        ],
        "viral_coefficient_tip": "Add a 'Powered by [Brand]' footer or watermark to all user-generated outputs. Add a one-click share button after each user win."
    }},
    "partnership_opportunities": [
        "Newsletter swap with a complementary {req.industry} newsletter (same audience, no overlap)",
        "Co-webinar with a non-competing tool that serves the same {req.target_audience}",
        "Bundle deal with a complementary product — cross-promote to each other's lists",
        "Affiliate program for existing happy customers — give them 20% recurring commission"
    ],
    "referral_program_ideas": [
        "Give existing users a unique link — for each referral: they get 1 free month, new user gets 20% off",
        "Public leaderboard of top referrers — recognition drives effort",
        "Double-sided incentive: both parties win immediately on signup, not after trial ends"
    ]
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Outreach strategy failed", "raw": response[:300]}
    return data


# ─── Growth Loop Builder ──────────────────────────────────────────────────────

@router.post("/growth-loop")
async def build_growth_loop(req: GrowthLoopRequest):
    """Design a viral growth loop with implementation steps."""
    channels = ", ".join(req.current_channels) if req.current_channels else "none specified"
    prompt = f"""Design a viral growth loop for this business.

Business Model: {req.business_model}
Target Audience: {req.target_audience}
Current Channels: {channels}

A growth loop is where user actions automatically bring more users (like Dropbox referral, Twitter quote tweets).
Design one that works with zero ad spend.

Respond ONLY with valid JSON, no markdown, no thinking tags:
{{
    "loop_name": "Descriptive name for this growth loop",
    "trigger": "The specific event that kicks off the loop (e.g. user achieves a result, user shares, user invites)",
    "steps": [
        "Step 1: User takes [specific action]",
        "Step 2: [Your product] makes [specific output] with branding",
        "Step 3: User shares [output] to [platform]",
        "Step 4: Viewer sees it, gets curious, clicks link",
        "Step 5: New user signs up — loop restarts"
    ],
    "viral_mechanism": "Explanation of why people share this — the psychological trigger that makes sharing feel natural or beneficial",
    "metrics_to_track": [
        "K-factor (viral coefficient) — target > 0.3",
        "Share rate after key win event",
        "Click-through rate on shared content",
        "Conversion rate of referred visitors",
        "Time from signup to first share"
    ],
    "implementation_steps": [
        "Add 'Powered by [Brand]' watermark/footer to all user outputs (2 hours)",
        "Add one-click share button after the key user win moment (4 hours)",
        "Create a public results/showcase page users can link to (1 day)",
        "Set up referral tracking with a unique link per user (1 day)",
        "Test the loop manually with 5 beta users before scaling"
    ],
    "expected_k_factor": "0.3–0.5 (each user brings 0.3–0.5 new users on average)"
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    return data or {"error": "Growth loop generation failed"}
