"""Workspaces endpoint."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.models.models import User, Workspace, Organization, Membership, MemberRole
from app.schemas.schemas import WorkspaceCreateRequest, WorkspaceResponse
router = APIRouter()

@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    org_id: uuid.UUID,
    payload: WorkspaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = Workspace(organization_id=org_id, **payload.model_dump())
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws
