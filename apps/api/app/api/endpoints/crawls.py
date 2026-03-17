"""Crawls endpoint."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import Crawl, CrawlPage, User
from app.schemas.schemas import CrawlPageResponse, CrawlResponse, PaginatedResponse
router = APIRouter()

@router.get("/{crawl_id}", response_model=CrawlResponse)
async def get_crawl(crawl_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Crawl).where(Crawl.id == crawl_id))
    crawl = result.scalar_one_or_none()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl not found")
    return crawl

@router.get("/{crawl_id}/pages", response_model=PaginatedResponse)
async def list_crawl_pages(crawl_id: uuid.UUID, page: int = 1, page_size: int = 50,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func as sqlfunc
    q = select(CrawlPage).where(CrawlPage.crawl_id == crawl_id)
    total = (await db.execute(select(sqlfunc.count()).select_from(q.subquery()))).scalar()
    items = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(items=[CrawlPageResponse.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size, pages=max(1,-(-total//page_size)))
