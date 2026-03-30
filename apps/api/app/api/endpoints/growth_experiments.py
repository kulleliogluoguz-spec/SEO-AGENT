"""
Growth Experiments — X/Twitter Account Growth Test Mode

POST /api/v1/growth/experiments           — create new experiment + generate strategy
GET  /api/v1/growth/experiments           — list user's experiments
GET  /api/v1/growth/experiments/active    — get active experiment
GET  /api/v1/growth/experiments/{id}      — get specific experiment
POST /api/v1/growth/experiments/{id}/generate-posts — generate trend-aware post drafts
POST /api/v1/growth/experiments/{id}/snapshot       — record performance snapshot
POST /api/v1/growth/experiments/{id}/pause          — pause experiment
POST /api/v1/growth/experiments/{id}/resume         — resume experiment
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.core.store.growth_experiment_store import (
    create_experiment,
    get_experiment,
    get_active_experiment,
    get_user_experiments,
    update_experiment,
    record_performance_snapshot,
    set_experiment_stage,
    VALID_GOALS,
    VALID_POSTING_MODES,
    VALID_AD_MODES,
)
from app.core.store.content_queue_store import create_draft
from app.core.store.learning_store import get_promoted_strategies, get_suppressed_strategies
from app.services.trend_intelligence import get_or_refresh_trends

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ExperimentCreateRequest(BaseModel):
    niche: str
    goal: str = "followers"
    posting_mode: str = "review"
    ad_mode: str = "off"
    x_username: Optional[str] = None
    brand_voice: Optional[str] = None
    target_audience: Optional[str] = None
    content_themes: Optional[list[str]] = None
    daily_post_target: int = 3
    followers_at_start: int = 0
    website_url: Optional[str] = None


class GeneratePostsRequest(BaseModel):
    count: int = 5
    force_refresh_trends: bool = False


class SnapshotRequest(BaseModel):
    current_followers: int
    posts_published: int


# ─── Content Strategy Generation ─────────────────────────────────────────────

COLD_START_CONTENT_MIX = {
    "tech": {"educational": 40, "opinion": 25, "thread": 20, "engagement": 15},
    "fashion": {"inspiration": 35, "tips": 25, "community": 25, "product": 15},
    "food": {"recipe": 35, "tips": 25, "behind_scenes": 25, "engagement": 15},
    "fitness": {"tips": 35, "motivation": 25, "educational": 25, "community": 15},
    "travel": {"inspiration": 40, "tips": 30, "story": 20, "engagement": 10},
    "ecommerce": {"educational": 35, "product": 25, "social_proof": 25, "engagement": 15},
    "creator": {"behind_scenes": 35, "tips": 25, "value": 25, "community": 15},
    "b2b": {"educational": 45, "insight": 25, "case_study": 20, "engagement": 10},
    "wellness": {"tips": 35, "inspiration": 25, "educational": 25, "community": 15},
    "general": {"educational": 30, "entertainment": 25, "tips": 25, "engagement": 20},
}

HOOK_STARTERS = [
    "Most people don't know this about {topic}...",
    "I spent 30 days testing {topic}. Here's what I found:",
    "The {topic} framework that changed everything:",
    "Stop making this {topic} mistake:",
    "Unpopular opinion: {topic}",
    "{topic} is harder than everyone admits. Here's why:",
    "5 {topic} lessons I wish I knew sooner:",
    "The honest truth about {topic}:",
    "Why {topic} matters more than you think:",
    "A thread on {topic} that might surprise you 🧵",
]

THREAD_FORMATS = [
    "Hook → 5-7 numbered lessons → CTA",
    "Problem → Agitate → Solution → CTA",
    "Story → Insight → Framework → Apply it → CTA",
    "Before/After → Process → Result → CTA",
    "Common myth → Truth → Why it matters → CTA",
]


def _build_growth_strategy(niche: str, goal: str, posting_mode: str, daily_target: int) -> dict:
    """Generate a cold-start growth strategy for the experiment."""
    mix = COLD_START_CONTENT_MIX.get(niche, COLD_START_CONTENT_MIX["general"])
    posting_cadence = {
        1: "1 post/day — minimum viable presence",
        2: "2 posts/day — morning + evening",
        3: "3 posts/day — morning, noon, evening",
        5: "5 posts/day — high-velocity cold-start mode",
    }.get(daily_target, f"{daily_target} posts/day")

    goal_tactics = {
        "followers": ["Engage in reply chains daily", "Follow 20-30 accounts/day in niche", "Pin best-performing thread"],
        "profile_visits": ["Use strong hooks", "Post threads (not single tweets)", "Tease content series"],
        "website_clicks": ["Include URL in 1 of every 3 posts", "Add link to bio immediately", "Mention site in threads"],
        "signups": ["Use social proof", "Highlight benefits over features", "Create urgency with limited offer"],
        "leads": ["Direct message responders", "Offer free resource in bio link", "Use CTA in every 3rd post"],
        "traffic": ["Share blog excerpts with link", "Repurpose top content as threads", "Quote tweet with commentary"],
    }

    return {
        "phase": "cold_start",
        "posting_cadence": posting_cadence,
        "daily_post_target": daily_target,
        "content_mix": mix,
        "goal_tactics": goal_tactics.get(goal, goal_tactics["followers"]),
        "thread_formats": THREAD_FORMATS[:3],
        "week_1_focus": "Establish identity — post your core beliefs/values, introduce your niche angle",
        "week_2_focus": "Build authority — share educational threads, engage heavily in reply chains",
        "week_3_focus": "Drive goal — optimise toward your primary metric with targeted CTAs",
        "posting_mode": posting_mode,
        "estimated_week_1_reach": f"{daily_target * 7 * 50}–{daily_target * 7 * 200} impressions",
    }


def _apply_learning_to_mix(base_mix: dict, niche: str) -> dict:
    """
    Adjust content type weights based on promoted/suppressed learning patterns.
    - Promoted content types get +30% weight boost (capped at 60%)
    - Suppressed content types get -50% weight reduction
    Returns a new mix dict with adjusted weights (values are relative weights, not %).
    """
    mix = dict(base_mix)
    try:
        promoted = get_promoted_strategies(niche=niche)
        suppressed = get_suppressed_strategies(niche=niche)

        promoted_types = {p["strategy_type"] for p in promoted}
        suppressed_types = {s["strategy_type"] for s in suppressed}

        for content_type in list(mix.keys()):
            if content_type in promoted_types:
                mix[content_type] = min(60, int(mix[content_type] * 1.30))
            elif content_type in suppressed_types:
                mix[content_type] = max(5, int(mix[content_type] * 0.50))

    except Exception:
        pass  # Learning data unavailable — use base mix unchanged

    return mix


def _weighted_content_types(mix: dict, count: int) -> list[str]:
    """
    Generate a list of `count` content types proportionally distributed from mix weights.
    Uses random.choices for weighted sampling with good variety.
    Deterministic seed based on count for reproducibility in tests.
    """
    import random as _random
    types = list(mix.keys())
    weights = [max(mix[t], 1) for t in types]

    if not types:
        return ["educational"] * count

    # Use weighted random sampling
    return _random.choices(types, weights=weights, k=count)


def _generate_post_idea(niche: str, trend_topic: str, content_type: str) -> str:
    """Generate a post draft text for a given trend and content type."""
    hook = random.choice(HOOK_STARTERS).format(topic=trend_topic or niche)

    type_expansions = {
        "educational": f"{hook}\n\nHere are the key points:\n1. Start with the basics\n2. Build on fundamentals\n3. Apply to real scenarios\n4. Measure what matters\n\nRetweet if this helped →",
        "opinion": f"{hook}\n\nHere's my take:\nMost people focus on X, but Y matters more.\n\nThe data supports this — [add your evidence here].\n\nDo you agree? Reply below.",
        "thread": f"{hook}\n\n🧵 A thread:\n\n1/ [Your first point — make it compelling]\n\n2/ [Second point with evidence]\n\n3/ [Third point with example]\n\n4/ [The takeaway]\n\nRT to share with your audience →",
        "tips": f"{hook}\n\n→ Tip 1: [Actionable advice]\n→ Tip 2: [Another tip]\n→ Tip 3: [Quick win]\n→ Tip 4: [Advanced move]\n\nSave this for later.",
        "engagement": f"{hook}\n\nQuick question: what's your experience with {trend_topic or niche}?\n\nA) [Option 1]\nB) [Option 2]\nC) [Option 3]\n\nReply with your answer 👇",
        "inspiration": f"{hook}\n\nRemember: every expert was once a beginner.\n\nThe difference is they kept going when it got hard.\n\nYour {niche} journey starts now.",
    }

    return type_expansions.get(content_type, type_expansions["educational"])


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/growth/experiments")
async def create_growth_experiment(
    body: ExperimentCreateRequest,
    user=Depends(get_current_user),
):
    """
    Create a new growth experiment. Automatically:
    1. Validates goal/mode inputs
    2. Fetches live trends for the niche
    3. Generates a cold-start growth strategy
    4. Creates initial draft posts (5 per default)
    """
    if body.goal not in VALID_GOALS:
        raise HTTPException(status_code=400, detail=f"Invalid goal. Must be one of: {VALID_GOALS}")
    if body.posting_mode not in VALID_POSTING_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid posting_mode. Must be one of: {VALID_POSTING_MODES}")
    if body.ad_mode not in VALID_AD_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid ad_mode. Must be one of: {VALID_AD_MODES}")

    # Build strategy
    strategy = _build_growth_strategy(
        niche=body.niche,
        goal=body.goal,
        posting_mode=body.posting_mode,
        daily_target=body.daily_post_target,
    )

    # Create experiment record
    experiment = create_experiment(
        user_id=str(user.id),
        niche=body.niche,
        goal=body.goal,
        posting_mode=body.posting_mode,
        ad_mode=body.ad_mode,
        x_username=body.x_username,
        brand_voice=body.brand_voice,
        target_audience=body.target_audience,
        content_themes=body.content_themes,
        daily_post_target=body.daily_post_target,
        followers_at_start=body.followers_at_start,
        website_url=body.website_url,
    )

    # Attach strategy
    update_experiment(experiment["id"], str(user.id), {"growth_strategy": strategy})
    experiment["growth_strategy"] = strategy

    # Fetch trends async (non-blocking — best effort)
    trend_signals = []
    try:
        trend_signals = await asyncio.wait_for(
            get_or_refresh_trends(body.niche), timeout=10.0
        )
    except Exception:
        pass

    # Generate initial 5 starter drafts, using learning-adjusted content mix
    base_mix = COLD_START_CONTENT_MIX.get(body.niche, COLD_START_CONTENT_MIX["general"])
    content_mix = _apply_learning_to_mix(base_mix, body.niche)
    content_types = _weighted_content_types(content_mix, 5)
    drafts_created = []

    for i in range(5):
        content_type = content_types[i]
        trend_signal = trend_signals[i] if i < len(trend_signals) else None
        trend_topic = trend_signal.get("keyword") or trend_signal.get("topic") or body.niche if trend_signal else body.niche
        trend_id = trend_signal.get("id") if trend_signal else None
        text = _generate_post_idea(body.niche, trend_topic, content_type)

        draft = create_draft(
            user_id=str(user.id),
            title=f"[{content_type.title()}] {trend_topic[:40]}",
            content_type=content_type,
            topic=trend_topic,
            generated_text=text,
            niche=body.niche,
            trend_keyword=trend_topic,
            channels=["x"],
            objective=f"growth_experiment:{experiment['id']}",
        )
        drafts_created.append({
            "id": draft["id"],
            "title": draft.get("title"),
            "content_type": content_type,
            "trend_topic": trend_topic,
            "trend_id": trend_id,
        })

    update_experiment(experiment["id"], str(user.id), {"posts_drafted": 5})

    return {
        "experiment": experiment,
        "strategy": strategy,
        "trend_signals": trend_signals[:6],
        "drafts_created": drafts_created,
        "next_steps": [
            f"Review {len(drafts_created)} starter posts in your Content Queue",
            "Connect your X account in Connections if not done",
            f"Set posting mode to '{body.posting_mode}' in Autonomy Settings",
            "Start posting — aim for first post within 24h",
        ],
    }


@router.get("/growth/experiments")
async def list_experiments(user=Depends(get_current_user)):
    """List all growth experiments for the current user."""
    experiments = get_user_experiments(str(user.id))
    return {"experiments": experiments, "count": len(experiments)}


@router.get("/growth/experiments/active")
async def get_active(user=Depends(get_current_user)):
    """Return the currently active growth experiment."""
    exp = get_active_experiment(str(user.id))
    if not exp:
        return {"experiment": None, "has_active": False}
    return {"experiment": exp, "has_active": True}


@router.get("/growth/experiments/{experiment_id}")
async def get_one_experiment(experiment_id: str, user=Depends(get_current_user)):
    """Get a specific experiment by ID."""
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.post("/growth/experiments/{experiment_id}/generate-posts")
async def generate_posts(
    experiment_id: str,
    body: GeneratePostsRequest,
    user=Depends(get_current_user),
):
    """
    Generate a fresh batch of trend-aware post drafts for this experiment.
    Uses current live trends for the experiment's niche.
    """
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    count = min(body.count, 20)

    trend_signals = []
    try:
        trend_signals = await asyncio.wait_for(
            get_or_refresh_trends(exp["niche"]), timeout=10.0
        )
    except Exception:
        pass

    # Apply learning-adjusted content mix
    base_mix = COLD_START_CONTENT_MIX.get(exp["niche"], COLD_START_CONTENT_MIX["general"])
    content_mix = _apply_learning_to_mix(base_mix, exp["niche"])
    content_types = _weighted_content_types(content_mix, count)
    drafts_created = []

    for i in range(count):
        content_type = content_types[i]
        trend_signal = trend_signals[i % len(trend_signals)] if trend_signals else None
        trend_topic = trend_signal.get("keyword") or trend_signal.get("topic") or exp["niche"] if trend_signal else exp["niche"]
        trend_id = trend_signal.get("id") if trend_signal else None
        text = _generate_post_idea(exp["niche"], trend_topic, content_type)

        draft = create_draft(
            user_id=str(user.id),
            title=f"[{content_type.title()}] {trend_topic[:40]}",
            content_type=content_type,
            topic=trend_topic,
            generated_text=text,
            niche=exp["niche"],
            trend_keyword=trend_topic,
            channels=["x"],
            objective=f"growth_experiment:{experiment_id}",
        )
        drafts_created.append({
            "id": draft["id"],
            "title": draft.get("title"),
            "content_type": content_type,
            "trend_topic": trend_topic,
            "trend_id": trend_id,
        })

    # Update drafted count
    new_count = exp.get("posts_drafted", 0) + count
    update_experiment(experiment_id, str(user.id), {"posts_drafted": new_count})

    return {
        "drafts_created": drafts_created,
        "count": len(drafts_created),
        "trend_signals_used": len(trend_signals),
        "content_mix_used": content_mix,
        "learning_applied": any(
            content_mix.get(ct, 0) != base_mix.get(ct, 0)
            for ct in base_mix
        ),
        "message": f"Generated {len(drafts_created)} posts. Review them in your Content Queue.",
    }


@router.post("/growth/experiments/{experiment_id}/snapshot")
async def add_snapshot(
    experiment_id: str,
    body: SnapshotRequest,
    user=Depends(get_current_user),
):
    """Record a follower/post performance snapshot for tracking growth over time."""
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    updated = record_performance_snapshot(
        experiment_id=experiment_id,
        user_id=str(user.id),
        current_followers=body.current_followers,
        posts_published=body.posts_published,
    )

    follower_delta = body.current_followers - exp.get("followers_at_start", 0)
    return {
        "experiment": updated,
        "follower_delta": follower_delta,
        "follower_growth_pct": round(
            follower_delta / max(exp.get("followers_at_start", 1), 1) * 100, 1
        ),
    }


@router.post("/growth/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str, user=Depends(get_current_user)):
    """Pause an active experiment."""
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    updated = set_experiment_stage(experiment_id, str(user.id), "paused")
    return {"experiment": updated, "message": "Experiment paused."}


@router.post("/growth/experiments/{experiment_id}/resume")
async def resume_experiment(experiment_id: str, user=Depends(get_current_user)):
    """Resume a paused experiment."""
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    updated = set_experiment_stage(experiment_id, str(user.id), "active")
    return {"experiment": updated, "message": "Experiment resumed."}


# ─── Instagram Growth Experiments ─────────────────────────────────────────────

INSTAGRAM_CONTENT_MIX = {
    "tech": {"carousel": 40, "caption": 30, "reel_concept": 20, "story": 10},
    "fashion": {"reel_concept": 40, "carousel": 30, "caption": 20, "story": 10},
    "food": {"reel_concept": 35, "carousel": 30, "caption": 25, "story": 10},
    "fitness": {"reel_concept": 40, "carousel": 25, "caption": 25, "story": 10},
    "travel": {"reel_concept": 40, "carousel": 30, "caption": 20, "story": 10},
    "ecommerce": {"carousel": 40, "caption": 30, "reel_concept": 20, "story": 10},
    "creator": {"reel_concept": 45, "behind_scenes": 25, "carousel": 20, "story": 10},
    "b2b": {"carousel": 45, "caption": 35, "reel_concept": 15, "story": 5},
    "wellness": {"reel_concept": 35, "carousel": 30, "caption": 25, "story": 10},
    "general": {"carousel": 35, "reel_concept": 30, "caption": 25, "story": 10},
}

INSTAGRAM_GOALS = [
    "followers", "reach", "profile_visits", "website_clicks", "saves", "engagement"
]


def _build_instagram_strategy(niche: str, goal: str, posting_mode: str, daily_target: int) -> dict:
    mix = INSTAGRAM_CONTENT_MIX.get(niche, INSTAGRAM_CONTENT_MIX["general"])
    cadence = {
        1: "1 post/day — story + feed post rotation",
        2: "2 posts/day — morning feed + evening story",
        3: "3 posts/day — carousel, reel, story daily",
    }.get(daily_target, f"{daily_target} posts/day — high-velocity mode")

    goal_tactics = {
        "followers": ["Post Reels daily — Reels reach non-followers", "Use 5-8 niche-relevant hashtags", "Reply to comments within 1 hour"],
        "reach": ["Prioritize Reels and carousels over single images", "Post at peak times (8-9am, 12-1pm, 7-9pm)", "Use trending audio on Reels"],
        "profile_visits": ["Strong hook in first 3 seconds of Reels", "CTA: 'Visit my profile for more'", "Consistent visual style"],
        "website_clicks": ["Add link to bio + Story CTA 'link in bio'", "Story swipe-up if 10k+ followers", "Carousel last slide = CTA to website"],
        "saves": ["Carousels with educational content", "Lists and frameworks people want to refer back to", "How-to content with numbered steps"],
        "engagement": ["Ask questions in captions", "Polls and questions in Stories", "Collab posts with niche accounts"],
    }

    return {
        "phase": "cold_start",
        "channel": "instagram",
        "posting_cadence": cadence,
        "daily_post_target": daily_target,
        "content_mix": mix,
        "goal_tactics": goal_tactics.get(goal, goal_tactics["followers"]),
        "week_1_focus": "Establish aesthetic — post 9 feed posts to fill grid, use consistent visual theme",
        "week_2_focus": "Push Reels — algorithm favors Reels for new accounts; aim for 3-5 Reels this week",
        "week_3_focus": "Drive goal metric — optimise captions and CTAs toward your primary objective",
        "posting_mode": posting_mode,
        "estimated_week_1_reach": f"{daily_target * 7 * 200}–{daily_target * 7 * 800} accounts reached",
        "note": "Instagram requires image or video for all posts. Caption-only posts are not supported — pair each caption with a visual.",
    }


def _generate_instagram_post_idea(niche: str, trend_topic: str, content_type: str) -> str:
    topic = trend_topic or niche
    ideas = {
        "carousel": f"📱 CAROUSEL CONCEPT: '{topic}'\n\nSlide 1 (Hook): [Bold statement or surprising fact about {topic}]\nSlide 2: [Problem — what people struggle with]\nSlide 3: [Solution point 1]\nSlide 4: [Solution point 2]\nSlide 5: [Solution point 3]\nSlide 6: [Quick summary]\nSlide 7: [CTA — Save this + follow for more]\n\nCaption: Everything you need to know about {topic} in one carousel. Save it for later 📌\n\n##{niche} #{topic.replace(' ', '')} #tips #howto",
        "reel_concept": f"🎬 REEL CONCEPT: '{topic}'\n\nHook (0-3s): [Start mid-action or with a bold claim]\nBody (3-20s): [Quick 3-step breakdown of {topic}]\nClose (20-30s): [Result or transformation]\nText overlay: '3 things about {topic} you need to know'\nAudio: [Use trending audio from Reels tab]\nCaption: This changed how I think about {topic} 👇\n\n##{niche} #reels #{topic.replace(' ', '')}",
        "caption": f"Most people get {topic} completely wrong.\n\nHere's what actually works:\n\n① [First insight — specific and actionable]\n② [Second insight — counter-intuitive]\n③ [Third insight — the one that makes the difference]\n\nThe secret? Consistency beats perfection every time.\n\nWhat's your biggest challenge with {topic}? Drop it in the comments 👇\n\n##{niche} #{topic.replace(' ', '')} #tips #growthmindset",
        "story": f"📸 STORY SEQUENCE: '{topic}'\n\nStory 1: Poll — 'Do you struggle with {topic}? Yes/No'\nStory 2: 'Most people say yes — here's why'\nStory 3: [Tip 1 with graphic]\nStory 4: [Tip 2 with graphic]\nStory 5: CTA — 'Save my latest post for the full breakdown'\n\nAdd: Question sticker 'What's your biggest {topic} question?'",
        "behind_scenes": f"Behind the scenes of how we approach {topic} 👀\n\nA lot of people ask us how we [relevant action]...\n\nThe honest answer: [authentic insight]\n\nWe used to think {topic} was about [common misconception]. Turns out it's really about [truth].\n\nWhat does your {niche} process look like? Tell me below 👇",
    }
    return ideas.get(content_type, ideas["caption"])


class InstagramExperimentCreateRequest(BaseModel):
    niche: str
    goal: str = "followers"
    posting_mode: str = "review"
    ig_handle: Optional[str] = None
    brand_voice: Optional[str] = None
    target_audience: Optional[str] = None
    daily_post_target: int = 2
    followers_at_start: int = 0
    website_url: Optional[str] = None
    visual_style: Optional[str] = None


@router.post("/growth/experiments/instagram")
async def create_instagram_experiment(
    body: InstagramExperimentCreateRequest,
    user=Depends(get_current_user),
):
    """
    Create an Instagram growth experiment. Generates:
    - Instagram-native content strategy (carousel, reel, caption mix)
    - Trend-aware starter post concepts
    - Cold-start posting cadence
    """
    if body.goal not in INSTAGRAM_GOALS:
        body.goal = "followers"

    strategy = _build_instagram_strategy(
        niche=body.niche,
        goal=body.goal,
        posting_mode=body.posting_mode,
        daily_target=body.daily_post_target,
    )

    experiment = create_experiment(
        user_id=str(user.id),
        niche=body.niche,
        goal=body.goal,
        posting_mode=body.posting_mode,
        ad_mode="off",
        x_username=None,
        brand_voice=body.brand_voice,
        target_audience=body.target_audience,
        content_themes=None,
        daily_post_target=body.daily_post_target,
        followers_at_start=body.followers_at_start,
        website_url=body.website_url,
    )
    update_experiment(experiment["id"], str(user.id), {
        "growth_strategy": strategy,
        "channel": "instagram",
        "ig_handle": body.ig_handle,
    })
    experiment["growth_strategy"] = strategy
    experiment["channel"] = "instagram"

    trend_signals = []
    try:
        trend_signals = await asyncio.wait_for(
            get_or_refresh_trends(body.niche), timeout=10.0
        )
    except Exception:
        pass

    content_mix = INSTAGRAM_CONTENT_MIX.get(body.niche, INSTAGRAM_CONTENT_MIX["general"])
    content_types = list(content_mix.keys())
    drafts_created = []

    for i in range(5):
        content_type = content_types[i % len(content_types)]
        trend_topic = (trend_signals[i].get("keyword") or trend_signals[i].get("topic") or body.niche) if i < len(trend_signals) else body.niche
        text = _generate_instagram_post_idea(body.niche, trend_topic, content_type)

        draft = create_draft(
            user_id=str(user.id),
            title=f"[IG {content_type.replace('_', ' ').title()}] {trend_topic[:35]}",
            content_type=content_type,
            topic=trend_topic,
            generated_text=text,
            channels=["instagram"],
            objective=f"ig_experiment:{experiment['id']}",
        )
        drafts_created.append({
            "id": draft["id"],
            "title": draft.get("title"),
            "content_type": content_type,
            "trend_topic": trend_topic,
        })

    update_experiment(experiment["id"], str(user.id), {"posts_drafted": 5})

    return {
        "experiment": experiment,
        "strategy": strategy,
        "trend_signals": trend_signals[:6],
        "drafts_created": drafts_created,
        "next_steps": [
            f"Review {len(drafts_created)} Instagram content concepts in your Content Queue",
            "Connect your Instagram Business/Creator account in Connections",
            "Pair each caption concept with an image or video before publishing",
            f"Set posting cadence to {body.daily_post_target} post(s)/day in Autonomy Settings",
            "Post your first Reel within 48 hours — Reels get 3-5x more reach for new accounts",
        ],
    }


@router.get("/growth/experiments/instagram/active")
async def get_active_instagram(user=Depends(get_current_user)):
    """Return the currently active Instagram growth experiment."""
    experiments = get_user_experiments(str(user.id))
    active = next(
        (e for e in experiments if e.get("channel") == "instagram" and e.get("stage") == "active"),
        None,
    )
    if not active:
        return {"experiment": None, "has_active": False}
    return {"experiment": active, "has_active": True}


@router.post("/growth/experiments/{experiment_id}/generate-posts/instagram")
async def generate_instagram_posts(
    experiment_id: str,
    body: GeneratePostsRequest,
    user=Depends(get_current_user),
):
    """Generate Instagram-native content ideas for a growth experiment."""
    exp = get_experiment(experiment_id, str(user.id))
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    count = min(body.count, 10)
    trend_signals = []
    try:
        trend_signals = await asyncio.wait_for(
            get_or_refresh_trends(exp["niche"]), timeout=10.0
        )
    except Exception:
        pass

    content_mix = INSTAGRAM_CONTENT_MIX.get(exp["niche"], INSTAGRAM_CONTENT_MIX["general"])
    content_types = list(content_mix.keys())
    drafts_created = []

    for i in range(count):
        content_type = content_types[i % len(content_types)]
        trend_topic = (trend_signals[i % len(trend_signals)].get("keyword") or trend_signals[i % len(trend_signals)].get("topic") or exp["niche"]) if trend_signals else exp["niche"]
        text = _generate_instagram_post_idea(exp["niche"], trend_topic, content_type)

        draft = create_draft(
            user_id=str(user.id),
            title=f"[IG {content_type.replace('_', ' ').title()}] {trend_topic[:35]}",
            content_type=content_type,
            topic=trend_topic,
            generated_text=text,
            channels=["instagram"],
            objective=f"ig_experiment:{experiment_id}",
        )
        drafts_created.append({
            "id": draft["id"],
            "title": draft.get("title"),
            "content_type": content_type,
            "trend_topic": trend_topic,
        })

    new_count = exp.get("posts_drafted", 0) + count
    update_experiment(experiment_id, str(user.id), {"posts_drafted": new_count})

    return {
        "drafts_created": drafts_created,
        "count": len(drafts_created),
        "message": f"Generated {len(drafts_created)} Instagram content concepts. Pair each with a visual before publishing.",
    }
