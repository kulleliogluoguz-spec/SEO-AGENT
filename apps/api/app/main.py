"""
AI CMO OS — FastAPI Application Entry Point.
"""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.endpoints.ai_admin import router as ai_router

from app.api.endpoints import (
    admin,
    approvals,
    auth,
    connectors,
    content,
    crawls,
    recommendations,
    reports,
    sites,
    workspaces,
    
)
from app.api.endpoints.marketing.routes import router as marketing_router
from app.api.endpoints.geo import router as geo_router
from app.api.endpoints.trends import router as trends_router
from app.api.endpoints.brand import router as brand_router
from app.api.endpoints.ads_connectors import router as ads_connectors_router
from app.api.endpoints.learning import router as learning_router
from app.api.endpoints.campaigns import router as campaigns_router
from app.api.endpoints.optimization import router as optimization_router
from app.api.endpoints.autonomy import router as autonomy_router
from app.api.endpoints.content_queue import router as content_queue_router
from app.api.endpoints.publishing import router as publishing_router
from app.api.endpoints.growth_experiments import router as growth_experiments_router
from app.api.endpoints.metrics import router as metrics_router
from app.api.endpoints.oauth_social import router as oauth_social_router
from app.api.endpoints.ads_launch import router as ads_launch_router
from app.api.endpoints.growth_dashboard import router as growth_dashboard_router
from app.core.config.settings import get_settings
from app.core.db.database import check_db_connection

logger = structlog.get_logger(__name__)
settings = get_settings()


async def _publish_sweep_loop() -> None:
    """
    Background job: publish scheduled posts that are past their scheduled_at time.
    Runs every 5 minutes. Routes each post to the correct channel publisher.
    Falls back to informative failure if channel has no credentials configured.
    """
    from app.core.store.content_queue_store import get_due_scheduled_posts, mark_post_published, mark_post_failed
    from app.core.store.autonomy_store import check_publish_allowed
    from app.services.publishers import get_publisher

    await asyncio.sleep(30)  # wait for startup
    while True:
        try:
            due = get_due_scheduled_posts()
            if due:
                logger.info("publish_sweep.found", count=len(due))
            for post in due:
                channel = post.get("channel", "")
                user_id = post.get("user_id", "")
                text = post.get("caption_override") or post.get("generated_text", "")

                # Full policy gate: kill switch + auto-publish flag + quiet hours + daily limit
                allowed, reason = check_publish_allowed(user_id, channel)
                if not allowed:
                    mark_post_failed(post["id"], reason)
                    logger.info("publish_sweep.blocked_by_policy", post_id=post["id"], channel=channel, reason=reason)
                    continue

                try:
                    publisher = get_publisher(channel, user_id)
                    result = await publisher.publish_text_post(text)
                    if result.success:
                        mark_post_published(post["id"], result.post_id or "")
                        logger.info("publish_sweep.published", post_id=post["id"], channel=channel, platform_id=result.post_id)
                    else:
                        mark_post_failed(post["id"], result.error or "Unknown publisher error")
                        logger.warning("publish_sweep.failed", post_id=post["id"], channel=channel, error=result.error)
                except ValueError:
                    mark_post_failed(
                        post["id"],
                        f"No publisher available for channel '{channel}'. "
                        "Connect the channel in Connections to enable auto-publish."
                    )
                    logger.info("publish_sweep.no_publisher", post_id=post["id"], channel=channel)
                except Exception as e:
                    mark_post_failed(post["id"], f"Publisher error: {e}")
                    logger.error("publish_sweep.publisher_error", post_id=post["id"], channel=channel, error=str(e))
        except Exception as e:
            logger.error("publish_sweep.error", error=str(e))
        await asyncio.sleep(300)  # every 5 minutes


async def _metrics_ingestion_loop() -> None:
    """
    Background job: auto-collect post metrics + follower counts.
    - Post metrics: every 60 minutes (all published posts in last 7 days)
    - Follower counts: every 6 hours (X and Instagram)
    Errors are swallowed — metrics are best-effort.
    """
    from app.services.growth.metrics_ingestion import (
        run_post_metrics_ingestion,
        run_follower_count_ingestion,
    )
    # Stagger startup so server is fully ready
    await asyncio.sleep(120)
    loop_count = 0
    while True:
        try:
            await run_post_metrics_ingestion()
        except Exception as e:
            logger.error("metrics_ingestion.post_metrics_error", error=str(e))
        # Fetch follower counts every 6 hours (every 6th hourly loop)
        if loop_count % 6 == 0:
            try:
                await run_follower_count_ingestion()
            except Exception as e:
                logger.error("metrics_ingestion.follower_count_error", error=str(e))
        loop_count += 1
        await asyncio.sleep(3600)  # every hour


async def _ads_optimization_loop() -> None:
    """
    Background job: daily ads performance check + recommendations.
    Analyzes all active ad campaigns and creates optimization recommendations.
    """
    from app.services.growth.ads_optimizer import run_ads_optimization
    # Start 3 hours after server starts (let ads accumulate data first)
    await asyncio.sleep(3 * 3600)
    while True:
        try:
            await run_ads_optimization()
        except Exception as e:
            logger.error("ads_optimization.error", error=str(e))
        await asyncio.sleep(24 * 3600)  # every 24 hours


async def _trend_refresh_loop() -> None:
    """
    Background job: refresh trending signals for all active niches every 6 hours.
    Runs inside the FastAPI lifespan, does not block startup.
    Errors are logged and swallowed — trend data is best-effort.
    """
    from app.services.trend_intelligence import refresh_all_active_niches

    # Stagger startup by 90s so the server is fully ready first
    await asyncio.sleep(90)
    while True:
        try:
            results = await refresh_all_active_niches()
            logger.info("trend_refresh.complete", results=results)
        except Exception as e:
            logger.error("trend_refresh.error", error=str(e))
        await asyncio.sleep(6 * 3600)  # every 6 hours


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle hooks."""
    logger.info("aicmo.startup", environment=settings.environment, version="0.1.0")

    # Start background jobs
    trend_task = asyncio.create_task(_trend_refresh_loop())
    publish_task = asyncio.create_task(_publish_sweep_loop())
    metrics_task = asyncio.create_task(_metrics_ingestion_loop())
    ads_opt_task = asyncio.create_task(_ads_optimization_loop())

    yield

    # Graceful shutdown
    for task in (trend_task, publish_task, metrics_task, ads_opt_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    logger.info("aicmo.shutdown")


app = FastAPI(
    title="AI CMO OS API",
    description=(
        "AI Growth Operating System — policy-aware, approval-gated, "
        "evidence-backed growth intelligence platform. "
        "Default autonomy: Level 1 (draft-only). Publishing requires human approval."
    ),
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_logging(request: Request, call_next):
    """Attach request ID and log every request with timing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()

    response = await call_next(request)

    duration_ms = round((time.monotonic() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)

    # Skip logging health checks to reduce noise
    if request.url.path not in ("/health", "/"):
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
    return response


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Convert Pydantic validation errors to consistent error format."""
    details = [
        {
            "code": "validation_error",
            "field": ".".join(str(loc) for loc in err["loc"]) if err.get("loc") else None,
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Request validation failed", "details": details},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Bad request", "details": [{"code": "invalid_value", "message": str(exc)}]},
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": "Permission denied", "details": [{"code": "forbidden", "message": str(exc)}]},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: return structured JSON (not plain text) so CORS headers are always included."""
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ─── Routers ─────────────────────────────────────────────────────────────────

API_V1 = "/api/v1"

app.include_router(auth.router, prefix=f"{API_V1}/auth", tags=["auth"])
app.include_router(workspaces.router, prefix=f"{API_V1}/workspaces", tags=["workspaces"])
app.include_router(sites.router, prefix=f"{API_V1}/sites", tags=["sites"])
app.include_router(crawls.router, prefix=f"{API_V1}/crawls", tags=["crawls"])
app.include_router(recommendations.router, prefix=f"{API_V1}/recommendations", tags=["recommendations"])
app.include_router(content.router, prefix=f"{API_V1}/content", tags=["content"])
app.include_router(approvals.router, prefix=f"{API_V1}/approvals", tags=["approvals"])
app.include_router(reports.router, prefix=f"{API_V1}/reports", tags=["reports"])
app.include_router(connectors.router, prefix=f"{API_V1}/connectors", tags=["connectors"])
app.include_router(admin.router, prefix=f"{API_V1}/admin", tags=["admin"])
app.include_router(marketing_router, prefix=API_V1, tags=["marketing"])
app.include_router(ai_router, prefix="/api/v1")
app.include_router(geo_router, prefix=f"{API_V1}", tags=["GEO"])
app.include_router(trends_router, prefix=f"{API_V1}", tags=["Trends"])
app.include_router(brand_router, prefix=f"{API_V1}/brand", tags=["brand"])
app.include_router(ads_connectors_router, prefix=f"{API_V1}/ads-connectors", tags=["ads-connectors"])
app.include_router(learning_router, prefix=f"{API_V1}/learning", tags=["learning"])
app.include_router(campaigns_router, prefix=f"{API_V1}/campaigns", tags=["campaigns"])
app.include_router(optimization_router, prefix=f"{API_V1}/optimization", tags=["optimization"])
app.include_router(autonomy_router, prefix=f"{API_V1}", tags=["autonomy"])
app.include_router(content_queue_router, prefix=f"{API_V1}", tags=["content-queue"])
app.include_router(publishing_router, prefix=f"{API_V1}", tags=["publishing"])
app.include_router(growth_experiments_router, prefix=f"{API_V1}", tags=["growth-experiments"])
app.include_router(metrics_router, prefix=f"{API_V1}", tags=["metrics"])
app.include_router(oauth_social_router, prefix=f"{API_V1}", tags=["oauth-social"])
app.include_router(ads_launch_router, prefix=f"{API_V1}", tags=["ads-launch"])
app.include_router(growth_dashboard_router, prefix=f"{API_V1}", tags=["growth-dashboard"])


# ─── System Endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], summary="Liveness probe")
async def health():
    """Basic health check for load balancer / container probe."""
    return {"status": "ok", "version": "0.1.0", "environment": settings.environment}


@app.get("/health/ready", tags=["system"], summary="Readiness probe")
async def readiness():
    """Readiness check: verifies database, Ollama, and Qdrant connectivity."""
    import httpx
    db_ok = await check_db_connection()

    # Check Ollama
    ollama_ok = False
    try:
        ollama_url = settings.ollama_base_url if hasattr(settings, "ollama_base_url") else "http://localhost:11434"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{ollama_url}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    # Check Qdrant
    qdrant_ok = False
    try:
        qdrant_url = settings.qdrant_url if hasattr(settings, "qdrant_url") else "http://localhost:6333"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{qdrant_url}/readyz")
            qdrant_ok = r.status_code == 200
    except Exception:
        qdrant_ok = False

    all_ok = db_ok  # DB is the only hard requirement; AI services are optional at startup
    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": {
                "database": "ok" if db_ok else "error",
                "ollama": "ok" if ollama_ok else "unavailable",
                "qdrant": "ok" if qdrant_ok else "unavailable",
            },
        },
    )


@app.get("/", tags=["system"], include_in_schema=False)
async def root():
    return {"name": "AI CMO OS API", "version": "0.1.0", "docs": "/docs"}
