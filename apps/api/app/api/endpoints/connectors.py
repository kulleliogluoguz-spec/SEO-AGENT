"""Connectors endpoint — GA4, Search Console, Slack status and config."""
from fastapi import APIRouter, Depends
from app.api.dependencies.auth import get_current_user
from app.models.models import User
router = APIRouter()

@router.get("/status")
async def connectors_status(current_user: User = Depends(get_current_user)):
    """Return mock/real status of all configured connectors."""
    return {
        "connectors": [
            {"name": "ga4", "status": "mock", "description": "Google Analytics 4 (mock mode)"},
            {"name": "search_console", "status": "mock", "description": "Google Search Console (mock mode)"},
            {"name": "slack", "status": "mock", "description": "Slack notifications (mock mode)"},
            {"name": "cms", "status": "not_configured", "description": "CMS publishing (not configured)"},
        ]
    }
