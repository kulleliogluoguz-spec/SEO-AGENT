"""
Sites endpoints: onboard, list, get, crawl trigger.
Falls back to file-based demo store when PostgreSQL is unavailable.
"""

import uuid
from datetime import UTC
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

_DB_ERR = (Exception,)  # catch-all; narrow if needed


def _is_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        k in msg
        for k in ("connection refused", "asyncpg", "psycopg", "could not connect", "no such table")
    )


def _paginate(items: list, page: int, page_size: int) -> PaginatedResponse:
    total = len(items)
    start = (page - 1) * page_size
    return PaginatedResponse(
        items=items[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def onboard_site(
    payload: SiteOnboardRequest,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Onboard a new website. Falls back to demo store when DB is unavailable."""
    try:
        ws = (
            await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ).scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        parsed = urlparse(payload.url)
        domain = parsed.netloc.removeprefix("www.")
        if not domain:
            raise HTTPException(status_code=400, detail="Could not parse domain from URL")

        existing = (
            await db.execute(
                select(Site).where(Site.workspace_id == workspace_id, Site.domain == domain)
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Site '{domain}' already exists in this workspace"
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
        try:
            from app.services.site_service import SiteService

            await SiteService(db).trigger_onboarding_workflow(site.id, crawl.id)
        except Exception:
            pass
        return SiteResponse.model_validate(site)

    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        # ── Demo fallback ────────────────────────────────────────────────────
        from app.core.store.demo_store import create_site

        record = create_site(str(workspace_id), payload.url, payload.name, payload.max_pages)
        return record


@router.get("", response_model=PaginatedResponse)
async def list_sites(
    workspace_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """List sites. Falls back to demo store when DB is unavailable."""
    try:
        base_q = select(Site).where(Site.workspace_id == workspace_id)
        total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
        items = (
            (
                await db.execute(
                    base_q.order_by(Site.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return PaginatedResponse(
            items=[SiteResponse.model_validate(s) for s in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_sites

        items = get_sites(str(workspace_id))
        return _paginate(items, page, page_size)


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return SiteResponse.model_validate(site)
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_site

        record = get_site(str(site_id))
        if not record:
            raise HTTPException(status_code=404, detail="Site not found")
        return record


@router.post("/{site_id}/crawl", response_model=CrawlResponse, status_code=status.HTTP_201_CREATED)
async def trigger_crawl(
    site_id: uuid.UUID,
    max_pages: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        crawl = Crawl(site_id=site_id, status=CrawlStatus.QUEUED, max_pages=max_pages)
        db.add(crawl)
        await db.commit()
        await db.refresh(crawl)
        return CrawlResponse.model_validate(crawl)
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        import uuid as _uuid
        from datetime import datetime

        return {
            "id": str(_uuid.uuid4()),
            "site_id": str(site_id),
            "status": "queued",
            "max_pages": max_pages,
            "pages_crawled": 0,
            "pages_failed": 0,
            "error_message": None,
            "started_at": None,
            "completed_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        }


@router.get("/{site_id}/crawls", response_model=list[CrawlResponse])
async def list_site_crawls(
    site_id: uuid.UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    try:
        result = await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site_id)
            .order_by(Crawl.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        return []
