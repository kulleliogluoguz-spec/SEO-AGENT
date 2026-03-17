"""
Content endpoints: briefs, generation, review, approval.
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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

router = APIRouter()


@router.post("/briefs", response_model=ContentAssetResponse, status_code=201)
async def create_brief(
    payload: ContentBriefRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a content brief. Triggers brief generation via agent."""
    service = ContentService(db)
    asset = await service.create_brief(
        site_id=payload.site_id,
        content_type=payload.content_type,
        topic=payload.topic,
        target_keyword=payload.target_keyword,
        tone=payload.tone,
        word_count_target=payload.word_count_target,
        notes=payload.notes,
        created_by=current_user,
    )
    return asset


@router.post("/generate", response_model=ContentAssetResponse, status_code=201)
async def generate_content(
    payload: ContentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate content from a brief.
    Requires the brief to be in DRAFT status.
    Output goes to REVIEW status for human approval.
    """
    service = ContentService(db)
    asset = await service.generate_from_brief(
        brief_id=payload.brief_id,
        model=payload.model,
    )
    return asset


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


@router.get("/{asset_id}", response_model=ContentAssetResponse)
async def get_content_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ContentAsset).where(ContentAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Content asset not found")
    return asset


@router.post("/{asset_id}/approve", response_model=ContentAssetResponse)
async def approve_content(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
