"""Approvals endpoint. Falls back to demo store when DB is unavailable."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import Approval, ApprovalStatus, User
from app.schemas.schemas import ApprovalActionRequest, ApprovalResponse, PaginatedResponse

router = APIRouter()


def _is_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("connection refused", "asyncpg", "psycopg", "could not connect", "no such table"))


@router.get("", response_model=PaginatedResponse)
async def list_approvals(
    workspace_id: uuid.UUID,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from sqlalchemy import func as sqlfunc
        q = select(Approval).where(Approval.workspace_id == workspace_id)
        if status:
            q = q.where(Approval.status == status)
        total = (await db.execute(select(sqlfunc.count()).select_from(q.subquery()))).scalar()
        items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return PaginatedResponse(
            items=[ApprovalResponse.model_validate(i) for i in items],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import get_approvals
        items = get_approvals(str(workspace_id), status)
        total = len(items)
        start = (page - 1) * page_size
        return PaginatedResponse(
            items=items[start: start + page_size],
            total=total, page=page, page_size=page_size,
            pages=max(1, -(-total // page_size)),
        )


@router.post("/{approval_id}/action", response_model=ApprovalResponse)
async def action_approval(
    approval_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Approval already actioned")
        approval.status = ApprovalStatus.APPROVED if payload.action == "approve" else ApprovalStatus.REJECTED
        approval.reviewed_by_id = current_user.id
        approval.review_note = payload.note
        approval.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(approval)
        return approval
    except HTTPException:
        raise
    except Exception as exc:
        if not _is_db_error(exc):
            raise
        from app.core.store.demo_store import action_approval as demo_action
        record = demo_action(str(approval_id), payload.action)
        if not record:
            raise HTTPException(status_code=404, detail="Approval not found")
        return record
