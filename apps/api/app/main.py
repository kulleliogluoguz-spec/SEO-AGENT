"""
AI CMO OS — FastAPI Application Entry Point.
"""
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.core.config.settings import get_settings
from app.core.db.database import check_db_connection

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle hooks."""
    logger.info("aicmo.startup", environment=settings.environment, version="0.1.0")
    yield
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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
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


# ─── System Endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], summary="Liveness probe")
async def health():
    """Basic health check for load balancer / container probe."""
    return {"status": "ok", "version": "0.1.0", "environment": settings.environment}


@app.get("/health/ready", tags=["system"], summary="Readiness probe")
async def readiness():
    """Readiness check: verifies database connectivity."""
    db_ok = await check_db_connection()
    http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if db_ok else "not_ready",
            "checks": {"database": "ok" if db_ok else "error"},
        },
    )


@app.get("/", tags=["system"], include_in_schema=False)
async def root():
    return {"name": "AI CMO OS API", "version": "0.1.0", "docs": "/docs"}
