"""
GEO (Generative Engine Optimization) API endpoints.

Provides:
  POST /geo/audit         — trigger a new GEO audit for a site
  GET  /geo/audits        — list GEO audits for a workspace
  GET  /geo/audits/{id}   — get GEO audit details
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_workspace_access
from app.core.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geo", tags=["GEO"])


class GEOAuditRequest(BaseModel):
    site_id: str = Field(..., description="Site ID to audit")
    workspace_id: str = Field(..., description="Workspace ID")
    site_url: Optional[str] = Field(None, description="Override site URL (defaults to site's URL)")


class GEOAuditResponse(BaseModel):
    id: str
    workspace_id: str
    site_id: str
    status: str
    overall_score: Optional[float] = None
    citability_score: Optional[float] = None
    ai_crawler_score: Optional[float] = None
    schema_score: Optional[float] = None
    entity_score: Optional[float] = None
    content_clarity_score: Optional[float] = None
    llms_txt_present: Optional[bool] = None
    llms_txt_quality: Optional[float] = None
    robots_txt_allows_ai: Optional[bool] = None
    structured_data_types: list[str] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    created_at: datetime


@router.post("/audit", response_model=GEOAuditResponse, status_code=202)
async def trigger_geo_audit(
    request: GEOAuditRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GEOAuditResponse:
    """
    Trigger a new GEO (Generative Engine Optimization) audit for a site.

    The audit runs in the background and checks:
    - llms.txt presence and quality
    - robots.txt AI crawler access
    - JSON-LD structured data
    - Content citability and clarity
    - Entity consistency
    - Canonical signals

    Returns 202 Accepted with the audit record ID.
    Poll GET /geo/audits/{id} to check status.
    """
    # Verify workspace access
    await require_workspace_access(current_user, request.workspace_id, db)

    # Resolve site URL
    site_url = request.site_url
    if not site_url:
        # Look up site URL from database
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT url FROM sites WHERE id = :site_id AND workspace_id = :workspace_id"),
            {"site_id": request.site_id, "workspace_id": request.workspace_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Site not found")
        site_url = row[0]

    # Create audit record in DB
    audit_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)

    await db.execute(
        __import__("sqlalchemy", fromlist=["text"]).text("""
            INSERT INTO geo_audits (id, workspace_id, site_id, status, created_at, updated_at)
            VALUES (:id, :workspace_id, :site_id, 'pending', :now, :now)
        """),
        {
            "id": audit_id,
            "workspace_id": request.workspace_id,
            "site_id": request.site_id,
            "now": now,
        },
    )
    await db.commit()

    # Run audit in background
    background_tasks.add_task(
        _run_geo_audit_background,
        audit_id=audit_id,
        site_url=site_url,
        workspace_id=request.workspace_id,
        site_id=request.site_id,
    )

    return GEOAuditResponse(
        id=audit_id,
        workspace_id=request.workspace_id,
        site_id=request.site_id,
        status="pending",
        structured_data_types=[],
        issues=[],
        recommendations=[],
        created_at=now,
    )


@router.get("/audits", response_model=list[GEOAuditResponse])
async def list_geo_audits(
    workspace_id: Annotated[str, Query(..., description="Workspace ID")],
    site_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[GEOAuditResponse]:
    """List GEO audits for a workspace, ordered by most recent first."""
    from sqlalchemy import text

    await require_workspace_access(current_user, workspace_id, db)

    query = """
        SELECT id, workspace_id, site_id, status, overall_score,
               citability_score, ai_crawler_score, schema_score,
               entity_score, content_clarity_score, llms_txt_present,
               llms_txt_quality, robots_txt_allows_ai, structured_data_types,
               issues, recommendations, completed_at, created_at
        FROM geo_audits
        WHERE workspace_id = :workspace_id
    """
    params: dict = {"workspace_id": workspace_id}

    if site_id:
        query += " AND site_id = :site_id"
        params["site_id"] = site_id

    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [_row_to_geo_audit_response(row) for row in rows]


@router.get("/audits/{audit_id}", response_model=GEOAuditResponse)
async def get_geo_audit(
    audit_id: str,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GEOAuditResponse:
    """Get a specific GEO audit by ID."""
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT id, workspace_id, site_id, status, overall_score,
                   citability_score, ai_crawler_score, schema_score,
                   entity_score, content_clarity_score, llms_txt_present,
                   llms_txt_quality, robots_txt_allows_ai, structured_data_types,
                   issues, recommendations, completed_at, created_at
            FROM geo_audits
            WHERE id = :audit_id
        """),
        {"audit_id": audit_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="GEO audit not found")

    await require_workspace_access(current_user, str(row[1]), db)
    return _row_to_geo_audit_response(row)


def _row_to_geo_audit_response(row) -> GEOAuditResponse:
    return GEOAuditResponse(
        id=str(row[0]),
        workspace_id=str(row[1]),
        site_id=str(row[2]),
        status=row[3] or "pending",
        overall_score=row[4],
        citability_score=row[5],
        ai_crawler_score=row[6],
        schema_score=row[7],
        entity_score=row[8],
        content_clarity_score=row[9],
        llms_txt_present=row[10],
        llms_txt_quality=row[11],
        robots_txt_allows_ai=row[12],
        structured_data_types=list(row[13] or []),
        issues=list(row[14] or []),
        recommendations=list(row[15] or []),
        completed_at=row[16],
        created_at=row[17],
    )


async def _run_geo_audit_background(
    audit_id: str,
    site_url: str,
    workspace_id: str,
    site_id: str,
) -> None:
    """Run GEO audit asynchronously and persist results."""
    from app.agents.geo.geo_auditor import GEOAuditor
    from app.core.db.database import get_async_session
    from sqlalchemy import text
    import json

    try:
        auditor = GEOAuditor()
        result = await auditor.audit(site_url)

        async with get_async_session() as db:
            await db.execute(
                text("""
                    UPDATE geo_audits SET
                        status = 'complete',
                        overall_score = :overall_score,
                        citability_score = :citability_score,
                        ai_crawler_score = :ai_crawler_score,
                        schema_score = :schema_score,
                        entity_score = :entity_score,
                        content_clarity_score = :content_clarity_score,
                        llms_txt_present = :llms_txt_present,
                        llms_txt_quality = :llms_txt_quality,
                        robots_txt_allows_ai = :robots_txt_allows_ai,
                        structured_data_types = :structured_data_types,
                        issues = :issues,
                        recommendations = :recommendations,
                        audit_duration_seconds = :duration,
                        completed_at = :now,
                        updated_at = :now
                    WHERE id = :audit_id
                """),
                {
                    "audit_id": audit_id,
                    "overall_score": result.overall_score,
                    "citability_score": result.citability_score,
                    "ai_crawler_score": result.ai_crawler_score,
                    "schema_score": result.schema_score,
                    "entity_score": result.entity_score,
                    "content_clarity_score": result.content_clarity_score,
                    "llms_txt_present": result.llms_txt_present,
                    "llms_txt_quality": result.llms_txt_quality,
                    "robots_txt_allows_ai": result.robots_txt_allows_ai,
                    "structured_data_types": result.structured_data_types,
                    "issues": json.dumps(result.issues),
                    "recommendations": json.dumps(result.recommendations),
                    "duration": int(result.duration_seconds),
                    "now": datetime.now(tz=timezone.utc),
                },
            )
            await db.commit()
            logger.info(f"GEO audit {audit_id} completed: score={result.overall_score}")

    except Exception as e:
        logger.error(f"GEO audit {audit_id} failed: {e}")
        from app.core.db.database import get_async_session
        from sqlalchemy import text

        async with get_async_session() as db:
            await db.execute(
                text("""
                    UPDATE geo_audits
                    SET status = 'failed', updated_at = :now
                    WHERE id = :audit_id
                """),
                {"audit_id": audit_id, "now": datetime.now(tz=timezone.utc)},
            )
            await db.commit()
