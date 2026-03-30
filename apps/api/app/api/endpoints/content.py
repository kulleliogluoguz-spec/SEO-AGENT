"""
Content endpoints: briefs, generation, review, approval.
Falls back to file-based demo store when PostgreSQL is unavailable.
"""
import logging
import os
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import ContentAsset, ContentStatus, User
from app.schemas.schemas import (
    ContentAssetResponse,
    ContentBriefRequest,
    ContentGenerateRequest,
    PaginatedResponse,
)
from app.services.content_service import ContentService

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Creative generation via Ollama ────────────────────────────────────────────

class CreativeGenerateRequest(BaseModel):
    content_type: str        # reel_script | carousel | caption | story | blog | landing_page | ad_copy
    objective: str           # engagement | awareness | traffic | conversion
    topic: str
    audience: Optional[str] = None
    tone: str = "conversational"
    keywords: Optional[str] = None
    brand_name: Optional[str] = None
    niche: Optional[str] = None
    notes: Optional[str] = None
    variations: int = 3      # Number of variations to generate


CONTENT_PROMPTS = {
    "reel_script": """Write {variations} short-form video scripts (Reels/TikTok) for the following brief.
Each script should be 30–60 seconds when spoken aloud (roughly 75–150 words).
Format each as:
HOOK (first 3 seconds): [hook line]
CONTENT: [main content, numbered steps or key points]
CTA: [call to action]""",

    "carousel": """Write {variations} Instagram carousel post scripts for the following brief.
Each carousel should have 5–8 slides.
Format each as:
SLIDE 1 (Cover): [attention-grabbing title]
SLIDE 2: [key point or step 1]
SLIDE 3: [key point or step 2]
SLIDE 4: [key point or step 3]
SLIDE 5: [key point or step 4]
SLIDE 6: [social proof or stat]
SLIDE 7 (CTA): [call to action]""",

    "caption": """Write {variations} Instagram caption variations for the following brief.
Each caption should be 100–200 words, engaging, and end with a CTA and 5–8 relevant hashtags.
Format each as:
CAPTION: [caption text]
HASHTAGS: [hashtags]""",

    "story": """Write {variations} Instagram Story sequences (3–5 slides each) for the following brief.
Keep each story slide text under 30 words. Make them visually-oriented.
Format each as:
SLIDE 1: [text]
SLIDE 2: [text]
SLIDE 3: [text]
CTA SLIDE: [call to action]""",

    "ad_copy": """Write {variations} ad copy variations for the following brief.
Each variation should include:
HEADLINE: [5–8 words, attention-grabbing]
BODY: [2–3 sentences, benefit-focused]
CTA: [2–4 words]""",

    "blog": """Write an outline for {variations} blog article(s) for the following brief.
Each outline should include:
TITLE: [SEO-optimized title]
META DESCRIPTION: [150 characters]
INTRODUCTION: [2-3 sentences]
H2 SECTIONS: [list 4–6 section headings]
CONCLUSION: [approach]""",

    "landing_page": """Write {variations} landing page copy variations for the following brief.
Format each as:
HEADLINE: [primary headline, 6–10 words]
SUBHEADLINE: [supporting statement, 15–25 words]
VALUE PROPS: [3 bullet points with benefit + feature]
SOCIAL PROOF: [type of proof to show]
CTA: [button text + surrounding copy]""",
}


@router.post("/generate-creative")
async def generate_creative(
    payload: CreativeGenerateRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Generate creative content using Ollama (local AI).

    Calls qwen3:8b (or configured model) to generate real copy variations.
    No external API — runs on your local machine.
    Falls back to structured templates when Ollama is unavailable.
    """
    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")

    content_type = payload.content_type
    prompt_template = CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS["caption"])

    context_lines = [
        f"Brand: {payload.brand_name or 'Unknown Brand'}",
        f"Niche: {payload.niche or 'general'}",
        f"Objective: {payload.objective}",
        f"Topic: {payload.topic}",
        f"Target audience: {payload.audience or 'general audience'}",
        f"Tone: {payload.tone}",
    ]
    if payload.keywords:
        context_lines.append(f"Keywords to include: {payload.keywords}")
    if payload.notes:
        context_lines.append(f"Additional notes: {payload.notes}")

    context_block = "\n".join(context_lines)
    prompt_instruction = prompt_template.format(variations=payload.variations)

    full_prompt = f"""{prompt_instruction}

BRIEF:
{context_block}

Be specific, concrete, and actionable. Write for {payload.tone} tone.
Do not use placeholders — write actual copy."""

    # Try Ollama
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.post(
                f"{ollama_base}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9,
                        "num_predict": 1200,
                    },
                },
            )

            if response.status_code == 200:
                data = response.json()
                generated_text = data.get("response", "")

                return {
                    "content_type": content_type,
                    "objective": payload.objective,
                    "topic": payload.topic,
                    "generated": generated_text,
                    "model": model,
                    "source": "ollama",
                    "variations_requested": payload.variations,
                    "provenance": "generated",
                    "note": f"Generated locally using {model} via Ollama.",
                }

            logger.warning("[content] Ollama returned %s — falling back to template", response.status_code)

    except httpx.RequestError as e:
        logger.warning("[content] Ollama unavailable (%s) — returning template structure", e)

    # Fallback: return structured brief template when Ollama is unavailable
    return {
        "content_type": content_type,
        "objective": payload.objective,
        "topic": payload.topic,
        "generated": _template_fallback(payload),
        "model": "template",
        "source": "template_fallback",
        "variations_requested": payload.variations,
        "provenance": "estimated",
        "note": (
            "Ollama is not running. Start Ollama with `ollama serve` and pull a model: "
            f"`ollama pull {model}` for AI-generated copy."
        ),
    }


def _template_fallback(p: CreativeGenerateRequest) -> str:
    """Return a structured brief template when Ollama is unavailable."""
    lines = [
        f"Content Type: {p.content_type}",
        f"Topic: {p.topic}",
        f"Objective: {p.objective}",
        f"Audience: {p.audience or 'your target audience'}",
        f"Tone: {p.tone}",
        "",
        "To generate real AI copy:",
        "1. Install Ollama: https://ollama.com",
        "2. Run: ollama serve",
        f"3. Pull model: ollama pull {os.environ.get('OLLAMA_MODEL', 'qwen3:8b')}",
        "4. Retry this request",
        "",
        "--- SAMPLE STRUCTURE ---",
    ]

    if p.content_type == "reel_script":
        lines += [
            f"HOOK: [Attention-grabbing opener about {p.topic}]",
            f"CONTENT: [3-5 key points about {p.topic} for {p.audience or 'your audience'}]",
            f"CTA: [Action you want viewers to take]",
        ]
    elif p.content_type == "caption":
        lines += [
            f"CAPTION: [Opening hook about {p.topic}...][Main value][Engagement question]",
            f"HASHTAGS: #{p.niche or 'brand'} #{p.topic.replace(' ', '').lower()} #[relevant tags]",
        ]
    elif p.content_type == "ad_copy":
        lines += [
            f"HEADLINE: [Benefit-driven headline for {p.topic}]",
            f"BODY: [Problem → Solution → CTA for {p.audience or 'your audience'}]",
            "CTA: [Action button text]",
        ]
    else:
        lines.append(f"[Brief structure for {p.content_type} about {p.topic}]")

    return "\n".join(lines)


def _is_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("connection refused", "asyncpg", "psycopg", "could not connect", "no such table"))


def _paginate(items: list, page: int, page_size: int) -> PaginatedResponse:
    total = len(items)
    start = (page - 1) * page_size
    return PaginatedResponse(
        items=items[start: start + page_size],
        total=total, page=page, page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("/briefs", response_model=ContentAssetResponse, status_code=201)
async def create_brief(
    payload: ContentBriefRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a content brief. Falls back to demo store when DB is unavailable."""
    try:
        service = ContentService(db)
        return await service.create_brief(
            site_id=payload.site_id,
            content_type=payload.content_type,
            topic=payload.topic,
            target_keyword=payload.target_keyword,
            tone=payload.tone,
            word_count_target=payload.word_count_target,
            notes=payload.notes,
            created_by=current_user,
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import create_content_asset, DEMO_WS
        record = create_content_asset(DEMO_WS, {
            "title": payload.topic,
            "asset_type": payload.content_type or "blog",
            "status": "draft",
            "content": None,
            "brief": {
                "topic": payload.topic,
                "content_type": payload.content_type,
                "target_keyword": payload.target_keyword,
                "tone": payload.tone,
                "word_count_target": payload.word_count_target,
                "notes": payload.notes,
            },
            "compliance_flags": [],
            "risk_score": 0.0,
        })
        return record


@router.post("/generate", response_model=ContentAssetResponse, status_code=201)
async def generate_content(
    payload: ContentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = ContentService(db)
        return await service.generate_from_brief(brief_id=payload.brief_id, model=payload.model)
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        raise HTTPException(status_code=503, detail="Content generation requires a running database.")


@router.get("", response_model=PaginatedResponse)
async def list_content(
    workspace_id: uuid.UUID,
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from sqlalchemy import func as sqlfunc
        query = select(ContentAsset).where(ContentAsset.workspace_id == workspace_id)
        if asset_type:
            query = query.where(ContentAsset.asset_type == asset_type)
        if status:
            query = query.where(ContentAsset.status == status)
        count_q = select(sqlfunc.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar()
        items = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return PaginatedResponse(
            items=[ContentAssetResponse.model_validate(i) for i in items],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_content_assets
        items = get_content_assets(str(workspace_id), asset_type, status)
        return _paginate(items, page, page_size)


@router.get("/{asset_id}", response_model=ContentAssetResponse)
async def get_content_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(ContentAsset).where(ContentAsset.id == asset_id))
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Content asset not found")
        return asset
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        raise HTTPException(status_code=404, detail="Content asset not found")


@router.post("/{asset_id}/approve", response_model=ContentAssetResponse)
async def approve_content(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(ContentAsset).where(ContentAsset.id == asset_id))
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Content asset not found")
        if asset.status not in (ContentStatus.REVIEW, ContentStatus.DRAFT):
            raise HTTPException(status_code=400, detail=f"Cannot approve asset in {asset.status} status")
        from datetime import datetime, timezone
        asset.status = ContentStatus.APPROVED
        asset.approved_by_id = current_user.id
        asset.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(asset)
        return asset
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        raise HTTPException(status_code=503, detail="Approval requires a running database.")
