"""
Trends API endpoints.

Provides:
  GET  /trends                    — list trends for a workspace
  GET  /trends/{id}               — get trend details
  POST /trends/detect             — trigger trend detection from recent documents
  GET  /trends/{id}/recommendations — get growth recommendations for a trend
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_workspace_access
from app.core.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trends", tags=["Trends"])


class TrendResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    summary: str
    keywords: list[str]
    category: str
    momentum_score: float
    relevance_score: float
    volume_7d: int
    sentiment: float
    source_types: list[str]
    evidence: list[dict]
    status: str
    first_seen_at: datetime
    last_active_at: datetime
    created_at: datetime


class TrendDetectRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace to detect trends for")
    lookback_days: int = Field(14, ge=1, le=90, description="How many days of documents to analyze")
    min_document_count: int = Field(2, ge=1, description="Minimum documents per trend cluster")


@router.get("", response_model=list[TrendResponse])
async def list_trends(
    workspace_id: Annotated[str, Query(..., description="Workspace ID")],
    status: Optional[str] = Query(None, description="Filter by status: active, declining, expired"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relevance score"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[TrendResponse]:
    """List trends for a workspace, ordered by relevance × momentum descending."""
    from sqlalchemy import text

    await require_workspace_access(current_user, workspace_id, db)

    query = """
        SELECT id, workspace_id, title, summary, keywords, category,
               momentum_score, relevance_score, volume_7d, sentiment,
               source_types, evidence, status, first_seen_at, last_active_at, created_at
        FROM trends
        WHERE workspace_id = :workspace_id
          AND relevance_score >= :min_relevance
    """
    params: dict = {"workspace_id": workspace_id, "min_relevance": min_relevance}

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY (relevance_score * GREATEST(momentum_score, 0.1)) DESC LIMIT :limit OFFSET :offset"
    params.update({"limit": limit, "offset": offset})

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [_row_to_trend_response(row) for row in rows]


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: str,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrendResponse:
    """Get a specific trend by ID."""
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT id, workspace_id, title, summary, keywords, category,
                   momentum_score, relevance_score, volume_7d, sentiment,
                   source_types, evidence, status, first_seen_at, last_active_at, created_at
            FROM trends WHERE id = :trend_id
        """),
        {"trend_id": trend_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Trend not found")

    await require_workspace_access(current_user, str(row[1]), db)
    return _row_to_trend_response(row)


@router.post("/detect", status_code=202)
async def detect_trends(
    request: TrendDetectRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Trigger trend detection from recently ingested source documents.

    Runs in the background. New TrendRecord objects will appear in GET /trends
    when complete.
    """
    await require_workspace_access(current_user, request.workspace_id, db)

    background_tasks.add_task(
        _run_trend_detection_background,
        workspace_id=request.workspace_id,
        lookback_days=request.lookback_days,
        min_document_count=request.min_document_count,
    )

    return {
        "status": "accepted",
        "message": "Trend detection started. Results will appear in GET /trends.",
        "workspace_id": request.workspace_id,
    }


def _row_to_trend_response(row) -> TrendResponse:
    return TrendResponse(
        id=str(row[0]),
        workspace_id=str(row[1]),
        title=row[2] or "",
        summary=row[3] or "",
        keywords=list(row[4] or []),
        category=row[5] or "general",
        momentum_score=float(row[6] or 0.0),
        relevance_score=float(row[7] or 0.0),
        volume_7d=int(row[8] or 0),
        sentiment=float(row[9] or 0.0),
        source_types=list(row[10] or []),
        evidence=list(row[11] or []),
        status=row[12] or "active",
        first_seen_at=row[13],
        last_active_at=row[14],
        created_at=row[15],
    )


async def _run_trend_detection_background(
    workspace_id: str,
    lookback_days: int,
    min_document_count: int,
) -> None:
    """Detect trends from recent source documents and persist to DB."""
    from app.agents.trends.trend_detector import TrendDetector
    from app.core.db.database import get_async_session
    from sqlalchemy import text
    from datetime import timezone
    import json
    import uuid

    logger.info(f"Starting trend detection for workspace {workspace_id}")

    try:
        async with get_async_session() as db:
            # Load recent source documents
            result = await db.execute(
                text("""
                    SELECT id, title, raw_text, published_at, source_type, source_url, metadata
                    FROM source_documents
                    WHERE workspace_id = :workspace_id
                      AND published_at >= NOW() - INTERVAL ':days days'
                    ORDER BY published_at DESC
                    LIMIT 1000
                """),
                {"workspace_id": workspace_id, "days": lookback_days},
            )
            rows = result.fetchall()
            documents = [
                {
                    "id": str(r[0]),
                    "title": r[1],
                    "raw_text": r[2],
                    "published_at": r[3],
                    "source_type": r[4],
                    "source_url": r[5],
                    "metadata": r[6] or {},
                }
                for r in rows
            ]

            if not documents:
                logger.info(f"No documents found for workspace {workspace_id}, skipping trend detection")
                return

            # Load brand profile for relevance scoring
            brand_result = await db.execute(
                text("SELECT * FROM brand_profiles WHERE workspace_id = :wid"),
                {"wid": workspace_id},
            )
            brand_row = brand_result.fetchone()
            brand_profile = dict(brand_row._mapping) if brand_row else None

            # Detect trends
            detector = TrendDetector(min_document_count=min_document_count)
            candidates = detector.detect_trends(documents, brand_profile=brand_profile)

            logger.info(f"Detected {len(candidates)} trend candidates for workspace {workspace_id}")

            now = datetime.now(tz=timezone.utc)

            # Persist trend records
            for candidate in candidates[:50]:  # Top 50 trends
                trend_id = str(uuid.uuid4())
                relevance_score = candidate.metadata.get("relevance_score", 0.0)

                await db.execute(
                    text("""
                        INSERT INTO trends (
                            id, workspace_id, title, summary, keywords, category,
                            momentum_score, relevance_score, volume_7d, sentiment,
                            source_types, evidence, status,
                            first_seen_at, last_active_at, created_at, updated_at
                        ) VALUES (
                            :id, :workspace_id, :title, :summary, :keywords, :category,
                            :momentum_score, :relevance_score, :volume_7d, :sentiment,
                            :source_types, :evidence, 'active',
                            :now, :now, :now, :now
                        )
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": trend_id,
                        "workspace_id": workspace_id,
                        "title": candidate.title,
                        "summary": f"Trending topic with {candidate.document_count} recent mentions",
                        "keywords": candidate.keywords,
                        "category": candidate.category,
                        "momentum_score": candidate.momentum_score,
                        "relevance_score": relevance_score,
                        "volume_7d": candidate.volume_7d,
                        "sentiment": candidate.sentiment_avg,
                        "source_types": candidate.sources,
                        "evidence": json.dumps(candidate.evidence),
                        "now": now,
                    },
                )

            await db.commit()
            logger.info(f"Persisted {len(candidates)} trends for workspace {workspace_id}")

    except Exception as e:
        logger.error(f"Trend detection failed for workspace {workspace_id}: {e}", exc_info=True)
