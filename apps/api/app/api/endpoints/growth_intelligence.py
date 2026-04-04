"""
Growth Intelligence Engine
Powered by: apps/marketingskills/skills/
Skills used: ab-test-setup, cold-email, copywriting, page-cro, content-strategy,
             customer-research, copy-editing, marketing-psychology

All AI calls use local Ollama — zero external cost.
"""

import os
import json
import httpx
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/v1/intelligence", tags=["growth-intelligence"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def ask_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": LLM_MODEL, "prompt": prompt, "stream": False, "think": False},
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception as e:
        return f"Ollama unavailable: {e}"
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


def extract_array(text: str) -> list:
    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return []


# ─── Request Models ───────────────────────────────────────────────────────────

class ExperimentRequest(BaseModel):
    hypothesis: str
    metric: str
    variants: List[str]
    business_type: str
    niche: Optional[str] = ""


class ContentScoreRequest(BaseModel):
    content: str
    content_type: str
    target_audience: str
    goal: str
    business_type: str


class ICPRequest(BaseModel):
    business_type: str
    product_description: str
    target_market: str
    average_deal_size: Optional[str] = ""


class OutboundRequest(BaseModel):
    prospect_name: str
    prospect_company: str
    prospect_role: str
    your_product: str
    pain_point: str
    channel: str


class WeeklyScorecardRequest(BaseModel):
    business_type: str
    niche: str
    metrics: dict


# ─── Dashboard ───────────────────────────────────���────────────────────────────

@router.get("/dashboard")
async def get_dashboard():
    return {
        "modules": [
            {
                "name": "Growth Engine",
                "description": "Design A/B experiments using ab-test-setup skill. Structure hypotheses, define variants, and get statistical measurement plans.",
                "endpoints": ["/intelligence/experiments/create", "/intelligence/experiments/analyze"],
                "skill": "ab-test-setup",
                "status": "active",
            },
            {
                "name": "Content Scorer",
                "description": "Multi-expert content review applying copywriting, page-cro, marketing-psychology, and copy-editing skills simultaneously.",
                "endpoints": ["/intelligence/content/score", "/intelligence/content/optimize"],
                "skill": "copywriting + page-cro + copy-editing",
                "status": "active",
            },
            {
                "name": "Sales Pipeline",
                "description": "ICP definition and prospect scoring using customer-research skill frameworks.",
                "endpoints": ["/intelligence/pipeline/icp-score", "/intelligence/pipeline/prospect-score"],
                "skill": "customer-research",
                "status": "active",
            },
            {
                "name": "Outbound Engine",
                "description": "Personalized outreach and multi-touch sequences using cold-email skill best practices.",
                "endpoints": ["/intelligence/outbound/generate", "/intelligence/outbound/sequence"],
                "skill": "cold-email",
                "status": "active",
            },
            {
                "name": "Weekly Scorecard",
                "description": "Automated growth scorecard with wins, losses, and next-week priorities.",
                "endpoints": ["/intelligence/scorecard/weekly"],
                "skill": "marketing-ideas + analytics-tracking",
                "status": "active",
            },
        ],
        "quick_start": {
            "step1": "POST /intelligence/pipeline/icp-score — define who to target",
            "step2": "POST /intelligence/content/score — score content before publishing",
            "step3": "POST /intelligence/outbound/generate — write personalized outreach",
            "step4": "POST /intelligence/experiments/create — design A/B tests",
            "step5": "POST /intelligence/scorecard/weekly — track progress weekly",
        },
    }


# ─── GROWTH ENGINE ────────────────────────────────────────────────────────────

@router.post("/experiments/create")
async def create_experiment(req: ExperimentRequest):
    """
    Design a structured A/B experiment.
    Applies: ab-test-setup skill — hypothesis framework, statistical rigor,
    single-variable testing, sample size calculation.
    """
    prompt = f"""You are an expert in experimentation and A/B testing (ab-test-setup skill).
Apply the hypothesis framework: "Because [observation], we believe [change] will cause [outcome] for [audience]."

Design a rigorous A/B experiment:

Hypothesis: {req.hypothesis}
Primary Metric: {req.metric}
Variants: {json.dumps(req.variants)}
Business Type: {req.business_type}
Niche: {req.niche or "general"}

Rules: Test ONE thing. Pre-determine sample size. Define success criteria before running.

Respond ONLY with valid JSON:
{{
  "experiment_name": "...",
  "structured_hypothesis": "Because [X], we believe [Y] will cause [Z] for [audience]. We'll know when [metric].",
  "null_hypothesis": "...",
  "primary_metric": "{req.metric}",
  "secondary_metrics": ["metric1", "metric2"],
  "variants": [
    {{"id": "control", "name": "Control", "description": "...", "implementation": "exact steps to set up"}},
    {{"id": "variant_a", "name": "Variant A", "description": "...", "implementation": "exact steps to set up"}}
  ],
  "sample_size_needed": "X visitors per variant",
  "test_duration_days": 14,
  "success_criteria": "Variant A outperforms control by >X% with 95% confidence",
  "how_to_measure": "exact measurement instructions",
  "free_tools": ["Google Optimize", "VWO free tier", "or manual split"],
  "expected_outcome": "...",
  "risk_level": "low",
  "priority_score": 80,
  "estimated_impact": "X% improvement in {req.metric}",
  "what_to_test_next": "if this wins, test..."
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    if not data:
        return {"error": "Experiment design failed", "raw": response[:400]}
    data["created_at"] = datetime.now().isoformat()
    data["status"] = "designed"
    return data


@router.post("/experiments/analyze")
async def analyze_experiment(
    experiment_name: str,
    control_metric: float,
    variant_metric: float,
    sample_size: int,
    metric_name: str,
):
    """Analyze A/B test results and provide a statistical interpretation."""
    uplift = (
        round((variant_metric - control_metric) / control_metric * 100, 1)
        if control_metric > 0
        else 0.0
    )
    prompt = f"""You are an A/B test analyst. Interpret these experiment results.

Experiment: {experiment_name}
Metric: {metric_name}
Control: {control_metric}
Variant: {variant_metric}
Uplift: {uplift}%
Sample size per variant: {sample_size}

Respond ONLY with valid JSON:
{{
  "result": "winner",
  "uplift_percentage": {uplift},
  "statistical_significance": "estimated confidence level",
  "recommendation": "ship",
  "reasoning": "detailed explanation of why this result is or isn't trustworthy",
  "next_experiment": "what to test next based on these results",
  "projected_annual_impact": "estimated annual impact if improvement holds"
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    return data or {"uplift_percentage": uplift, "error": "Analysis failed"}


@router.post("/scorecard/weekly")
async def weekly_scorecard(req: WeeklyScorecardRequest):
    """
    Weekly Growth Scorecard.
    Applies: marketing-ideas + analytics-tracking skills to assess performance
    and recommend the highest-leverage next actions.
    """
    prompt = f"""You are a growth analyst. Create a detailed weekly growth scorecard.

Business: {req.business_type} in {req.niche}
This week's metrics: {json.dumps(req.metrics)}

Respond ONLY with valid JSON:
{{
  "week_ending": "{datetime.now().strftime('%Y-%m-%d')}",
  "overall_score": 72,
  "grade": "B+",
  "metrics_analysis": [
    {{"metric": "name", "value": 0, "trend": "up", "vs_benchmark": "above/below average", "score": 75, "insight": "..."}}
  ],
  "wins": ["specific win 1", "specific win 2"],
  "losses": ["what didn't work", "missed opportunity"],
  "top_priority_next_week": "The single most important thing to focus on — be specific",
  "experiments_to_run": [
    {{"experiment": "...", "expected_impact": "...", "effort": "low"}}
  ],
  "channels_performance": [
    {{"channel": "SEO", "score": 75, "trend": "up", "action": "specific next action"}}
  ],
  "30_day_projection": "Based on current trajectory: specific outcome"
}}"""

    response = await ask_ollama(prompt)
    data = extract_json(response)
    return data or {"error": "Scorecard generation failed"}


# ─── CONTENT OPS ──────────────────────────────────────────────────────────────

@router.post("/content/score")
async def score_content(req: ContentScoreRequest):
    """
    Multi-expert content scoring.
    Applies copywriting, page-cro, copy-editing, and marketing-psychology skills.
    Each expert reviews from their specialty, then an overall verdict is given.
    """
    experts = [
        ("Conversion Copywriter", "clarity, benefit-first messaging, headline strength, CTA power"),
        ("CRO Specialist", "friction points, trust signals, value proposition, conversion elements"),
        ("Marketing Psychologist", "emotional triggers, social proof, loss aversion, desire amplification"),
    ]

    expert_scores = []
    for expert_name, expertise in experts:
        prompt = f"""You are a {expert_name} expert in {expertise}.
Apply marketing best practices: clarity over cleverness, benefits over features, customer language.

Score this {req.content_type} for a {req.business_type} targeting {req.target_audience}.
Goal: {req.goal}

CONTENT:
{req.content[:1500]}

Respond ONLY with valid JSON:
{{
  "expert": "{expert_name}",
  "score": 72,
  "grade": "B",
  "strengths": ["specific strength 1", "specific strength 2"],
  "weaknesses": ["specific weakness 1", "specific weakness 2"],
  "improvements": [
    {{"issue": "specific problem", "fix": "exact rewrite or action", "impact": "high"}}
  ],
  "rewritten_headline": "If there's one thing to rewrite, it's the headline — rewrite it here"
}}"""

        response = await ask_ollama(prompt)
        score_data = extract_json(response)
        if score_data:
            expert_scores.append(score_data)

    overall_prompt = f"""You are a senior content director applying copy-editing and content-strategy skills.
Give an overall verdict on this content.

Type: {req.content_type} | Business: {req.business_type} | Audience: {req.target_audience} | Goal: {req.goal}

Content:
{req.content[:2000]}

Respond ONLY with valid JSON:
{{
  "overall_score": 70,
  "grade": "B",
  "verdict": "revise",
  "top_3_improvements": ["most important fix (be specific)", "second fix", "third fix"],
  "improved_version": "Fully rewritten content with all improvements applied — complete version",
  "projected_performance": "How this content will likely perform vs. average"
}}"""

    overall_response = await ask_ollama(overall_prompt)
    overall_data = extract_json(overall_response)

    avg_score = (
        sum(e.get("score", 70) for e in expert_scores) / len(expert_scores)
        if expert_scores
        else 70
    )

    return {
        "content_type": req.content_type,
        "overall_score": overall_data.get("overall_score", int(avg_score)),
        "grade": overall_data.get("grade", "B"),
        "verdict": overall_data.get("verdict", "revise"),
        "expert_panels": expert_scores,
        "top_3_improvements": overall_data.get("top_3_improvements", []),
        "improved_version": overall_data.get("improved_version", ""),
        "projected_performance": overall_data.get("projected_performance", ""),
    }


@router.post("/content/optimize")
async def optimize_content(
    content: str,
    content_type: str,
    platform: str,
    target_audience: str,
):
    """Quick content optimization for a specific platform."""
    prompt = f"""Optimize this {content_type} for {platform}.
Target audience: {target_audience}

Apply: specificity over vagueness, benefits over features, customer language.

Original:
{content}

Respond ONLY with valid JSON:
{{
  "optimized": "the fully optimized version",
  "changes_made": ["change 1", "change 2", "change 3"],
  "score_before": 58,
  "score_after": 82,
  "platform_tips": ["tip specific to {platform}"]
}}"""

    response = await ask_ollama(prompt)
    return extract_json(response) or {"error": "Optimization failed"}


# ─── SALES PIPELINE ───────────────────────────────────────────────────────────

@router.post("/pipeline/icp-score")
async def score_icp(req: ICPRequest):
    """
    ICP Definition and Scoring System.
    Applies customer-research skill: extract pains, buying triggers,
    digital watering holes, qualification questions.
    """
    prompt = f"""You are a customer research expert. Define the ideal customer profile.
Apply: jobs-to-be-done framework, buying trigger identification, digital watering hole mapping.

Business Type: {req.business_type}
Product: {req.product_description}
Target Market: {req.target_market}
Deal Size: {req.average_deal_size or "not specified"}

Respond ONLY with valid JSON:
{{
  "icp_definition": {{
    "company_size": "...",
    "industry": ["industry1", "industry2"],
    "roles": ["decision maker role 1", "champion role"],
    "pain_points": ["specific pain 1", "specific pain 2", "specific pain 3"],
    "buying_triggers": ["trigger event 1", "trigger event 2"],
    "disqualifiers": ["bad fit signal 1", "bad fit signal 2"]
  }},
  "scoring_criteria": [
    {{"criterion": "Has the primary pain point", "weight": 30, "how_to_identify": "look for..."}},
    {{"criterion": "Right company size", "weight": 20, "how_to_identify": "..."}},
    {{"criterion": "Decision maker role", "weight": 25, "how_to_identify": "..."}},
    {{"criterion": "Budget signals", "weight": 15, "how_to_identify": "..."}},
    {{"criterion": "Timing indicator", "weight": 10, "how_to_identify": "..."}}
  ],
  "where_to_find_them": [
    {{"platform": "LinkedIn", "search_strategy": "exact search string", "estimated_pool": "X prospects"}},
    {{"platform": "Reddit", "search_strategy": "subreddits + keywords to monitor", "estimated_pool": "..."}}
  ],
  "qualification_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
  "red_flags": ["this means bad fit", "another disqualifier"]
}}"""

    response = await ask_ollama(prompt)
    return extract_json(response) or {"error": "ICP scoring failed"}


@router.post("/pipeline/prospect-score")
async def score_prospect(
    company: str,
    role: str,
    signals: List[str],
    business_type: str,
):
    """Score an individual prospect against ICP criteria."""
    prompt = f"""Score this prospect for {business_type}.

Company: {company}
Role: {role}
Signals observed: {json.dumps(signals)}

Apply customer-research framework: jobs-to-be-done, buying triggers, fit scoring.

Respond ONLY with valid JSON:
{{
  "fit_score": 78,
  "fit_grade": "B",
  "verdict": "warm",
  "matching_criteria": ["what aligns with ICP"],
  "missing_criteria": ["what's unknown or mismatched"],
  "recommended_action": "exact next step",
  "outreach_timing": "reach out now / wait for X trigger / skip",
  "personalization_angles": ["angle based on their signals", "second angle"]
}}"""

    response = await ask_ollama(prompt)
    return extract_json(response) or {"error": "Prospect scoring failed"}


# ─── OUTBOUND ENGINE ──────────────────────────────────────────────────────────

@router.post("/outbound/generate")
async def generate_outreach(req: OutboundRequest):
    """
    Personalized outreach message generator.
    Applies cold-email skill: lead with their world, one ask, low friction CTA,
    peer-not-vendor voice, personalization that connects to the problem.
    """
    channel_specs = {
        "email": "professional email, 150-200 words, clear subject line + body, interest-based CTA",
        "linkedin": "LinkedIn DM, 100-150 words, casual professional tone, no attachments",
        "twitter": "Twitter/X DM, under 280 chars, very casual, curiosity-driven",
    }

    prompt = f"""You are a cold email expert. Write a highly personalized {req.channel} outreach.

Prospect: {req.prospect_name} ({req.prospect_role} at {req.prospect_company})
Your product: {req.your_product}
Their pain point: {req.pain_point}
Channel rules: {channel_specs.get(req.channel, "professional")}

Cold email rules (from cold-email skill):
- Lead with THEIR problem, not your product
- Write like a peer, not a vendor — use contractions, read it aloud
- Every sentence earns its place — ruthlessly short
- Personalization must connect to the problem (not just name-drop)
- Interest-based CTA: "Worth a quick chat?" not "Book a 30-min demo"
- "You/your" should dominate over "I/we"

Respond ONLY with valid JSON:
{{
  "subject": "email subject line (email only)",
  "message": "the full outreach message",
  "follow_up_1": "follow up after 3 days of no reply — add value, don't just bump",
  "follow_up_2": "follow up after 7 days — final gentle attempt",
  "personalization_used": "what specific detail made this personal and why it connects",
  "predicted_open_rate": "X%",
  "predicted_reply_rate": "X%",
  "best_send_time": "Day and time recommendation"
}}"""

    response = await ask_ollama(prompt)
    return extract_json(response) or {"error": "Outreach generation failed"}


@router.post("/outbound/sequence")
async def generate_sequence(
    prospect_role: str,
    pain_point: str,
    your_product: str,
    channel: str,
    business_type: str,
):
    """Generate a 5-touch multi-channel outreach sequence."""
    prompt = f"""Create a 5-touch outreach sequence for {prospect_role} prospects.
Apply cold-email skill: each touch adds value, builds on previous, different angles.

Pain point: {pain_point}
Product: {your_product}
Channel: {channel}
Business: {business_type}

Respond ONLY with valid JSON:
{{
  "sequence_name": "...",
  "target_profile": "{prospect_role}",
  "touches": [
    {{"touch": 1, "day": 0, "type": "cold outreach", "subject": "...", "message": "...", "goal": "spark curiosity"}},
    {{"touch": 2, "day": 3, "type": "value add", "subject": "...", "message": "...", "goal": "demonstrate expertise"}},
    {{"touch": 3, "day": 7, "type": "social proof", "subject": "...", "message": "...", "goal": "build credibility"}},
    {{"touch": 4, "day": 12, "type": "different angle", "subject": "...", "message": "...", "goal": "find what resonates"}},
    {{"touch": 5, "day": 30, "type": "breakup + long-term", "subject": "...", "message": "...", "goal": "close or nurture"}}
  ],
  "expected_reply_rate": "X% across full sequence",
  "best_performing_touch": 1,
  "tips": ["tip for running this sequence effectively"]
}}"""

    response = await ask_ollama(prompt)
    return extract_json(response) or {"error": "Sequence generation failed"}
