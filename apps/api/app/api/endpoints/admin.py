"""
Admin endpoints: system health, feature flags, agent registry summary.
Superuser-only.
"""
import platform
import sys

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_superuser
from app.core.config.feature_flags import get_flags
from app.core.config.settings import get_settings
from app.core.db.database import check_db_connection
from app.models.models import User

router = APIRouter()
settings = get_settings()


@router.get("/system", summary="System health and version info")
async def system_info(current_user: User = Depends(require_superuser)) -> dict:
    """Superuser: full system health and configuration summary."""
    db_ok = await check_db_connection()
    flags = get_flags()

    return {
        "version": "0.1.0",
        "environment": settings.environment,
        "python_version": sys.version,
        "platform": platform.platform(),
        "database": "ok" if db_ok else "error",
        "autonomy_level": settings.autonomy_default_level,
        "autonomy_max": settings.autonomy_max_allowed_level,
        "demo_mode": settings.demo_mode,
        "llm_configured": bool(settings.anthropic_api_key),
        "temporal_host": settings.temporal_host,
        "feature_flags": flags.describe(),
        "agent_count": 138,
        "agent_layers": 13,
    }


@router.get("/flags", summary="Feature flag status")
async def feature_flags(current_user: User = Depends(require_superuser)) -> dict:
    """Superuser: list all feature flags and their current state."""
    return get_flags().describe()


@router.get("/agents", summary="Agent registry summary")
async def agent_registry(current_user: User = Depends(require_superuser)) -> dict:
    """Superuser: summary of all registered agents by layer."""
    from app.agents.registry import REGISTRY_BY_LAYER, AGENT_REGISTRY
    return {
        "total": len(AGENT_REGISTRY),
        "by_layer": {
            str(layer): {
                "count": len(agents),
                "names": [a.name for a in agents],
            }
            for layer, agents in sorted(REGISTRY_BY_LAYER.items())
        },
    }
