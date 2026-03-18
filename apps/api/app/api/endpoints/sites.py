"""
Sites endpoints: onboard, list, get, crawl trigger.
"""
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import Crawl, CrawlStatus, Site, SiteStatus, User, Workspace
from app.schemas.schemas import (
    CrawlResponse,
    PaginatedResponse,
    SiteOnboardRequest,
    SiteResponse,
)

router = APIRouter()


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def onboard_site(
    payload: SiteOnboardRequest,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Site:
    """
    Onboard a new website into a workspace.
    Validates URL, creates Site record, and queues the initial crawl workflow.
    """
    ws = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    parsed = urlparse(payload.url)
    domain = parsed.netloc.lstrip("www.")
    if not domain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse domain from URL")

    existing = (await db.execute(
        select(Site).where(Site.workspace_id == workspace_id, Site.domain == domain)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site with domain '{domain}' already exists in this workspace",
        )

    site = Site(
        workspace_id=workspace_id,
        url=payload.url,
        domain=domain,
        name=payload.name or domain,
        status=SiteStatus.PENDING,
    )
    db.add(site)
    await db.flush()

    crawl = Crawl(site_id=site.id, status=CrawlStatus.QUEUED, max_pages=payload.max_pages)
    db.add(crawl)
    await db.commit()
    await db.refresh(site)

    # Fire-and-forget: trigger Temporal workflow
    try:
        from app.services.site_service import SiteService
        service = SiteService(db)
        await service.trigger_onboarding_workflow(site.id, crawl.id)
    except Exception:
        pass  # Worker will pick it up; non-fatal

    return site


@router.get("", response_model=PaginatedResponse)
async def list_sites(
    workspace_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """List all sites in a workspace, paginated."""
    base_q = select(Site).where(Site.workspace_id == workspace_id)
    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    items = (await db.execute(
        base_q.order_by(Site.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return PaginatedResponse(
        items=[SiteResponse.model_validate(s) for s in items],
        total=total, page=page, page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Site:
    site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.post("/{site_id}/crawl", response_model=CrawlResponse, status_code=status.HTTP_201_CREATED)
async def trigger_crawl(
    site_id: uuid.UUID,
    max_pages: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Crawl:
    """Trigger a new crawl for an existing site."""
    site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    crawl = Crawl(site_id=site_id, status=CrawlStatus.QUEUED, max_pages=max_pages)
    db.add(crawl)
    await db.commit()
    await db.refresh(crawl)
    return crawl


@router.get("/{site_id}/crawls", response_model=list[CrawlResponse])
async def list_site_crawls(
    site_id: uuid.UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Crawl]:
    """List recent crawls for a site."""
    result = await db.execute(
        select(Crawl).where(Crawl.site_id == site_id)
        .order_by(Crawl.created_at.desc()).limit(limit)
    )
    return result.scalars().all()
