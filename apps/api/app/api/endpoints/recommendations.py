"""
Recommendations endpoints: list, get, update status.
Falls back to demo store when PostgreSQL is unavailable.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import Recommendation, RecommendationStatus, User
from app.schemas.schemas import (
    PaginatedResponse,
    RecommendationResponse,
    RecommendationUpdateRequest,
)

router = APIRouter()


def _is_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("connection refused", "asyncpg", "psycopg", "could not connect", "no such table"))


@router.get("", response_model=PaginatedResponse)
async def list_recommendations(
    site_id: uuid.UUID,
    category: str | None = None,
    status: str | None = None,
    min_priority: float = Query(default=0.0, ge=0.0, le=1.0),
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from sqlalchemy import func as sqlfunc
        query = select(Recommendation).where(
            Recommendation.site_id == site_id,
            Recommendation.priority_score >= min_priority,
        )
        if category:
            query = query.where(Recommendation.category == category)
        if status:
            query = query.where(Recommendation.status == status)
        count_q = select(sqlfunc.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar()
        query = query.order_by(Recommendation.priority_score.desc()).offset((page - 1) * page_size).limit(page_size)
        recs = (await db.execute(query)).scalars().all()
        return PaginatedResponse(
            items=[RecommendationResponse.model_validate(r) for r in recs],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_recommendations
        items = get_recommendations(str(site_id), category)
        total = len(items)
        start = (page - 1) * page_size
        return PaginatedResponse(
            items=items[start: start + page_size],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )


@router.get("/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id))
        rec = result.scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return rec
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        raise HTTPException(status_code=404, detail="Recommendation not found")


@router.patch("/{rec_id}", response_model=RecommendationResponse)
async def update_recommendation(
    rec_id: uuid.UUID,
    payload: RecommendationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id))
        rec = result.scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        if payload.status:
            try:
                rec.status = RecommendationStatus(payload.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
        await db.commit()
        await db.refresh(rec)
        return rec
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        raise HTTPException(status_code=503, detail="Status update requires a running database.")
