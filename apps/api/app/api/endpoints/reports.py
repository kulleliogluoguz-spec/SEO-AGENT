"""Reports endpoint. Falls back to demo store when DB is unavailable."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import Report, User
from app.schemas.schemas import PaginatedResponse, ReportDetailResponse, ReportResponse

router = APIRouter()


def _is_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("connection refused", "asyncpg", "psycopg", "could not connect", "no such table"))


@router.get("", response_model=PaginatedResponse)
async def list_reports(
    workspace_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from sqlalchemy import func as sqlfunc
        q = select(Report).where(Report.workspace_id == workspace_id).order_by(Report.created_at.desc())
        total = (await db.execute(select(sqlfunc.count()).select_from(q.subquery()))).scalar()
        items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return PaginatedResponse(
            items=[ReportResponse.model_validate(i) for i in items],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_reports
        items = get_reports(str(workspace_id))
        total = len(items)
        start = (page - 1) * page_size
        return PaginatedResponse(
            items=items[start: start + page_size],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_report
        record = get_report(str(report_id))
        if not record:
            raise HTTPException(status_code=404, detail="Report not found")
        return record
