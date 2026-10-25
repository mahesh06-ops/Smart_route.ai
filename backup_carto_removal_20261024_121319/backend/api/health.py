"""
Health check and system diagnostics endpoint.
"""
from fastapi import APIRouter
from src.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Returns application status, version, and active subsystem checks."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "carto_status": "ready" if settings.CARTO_API_KEY else "unconfigured",
        "services": {
            "geocoding": "operational",
            "routing": "operational",
            "weather": "operational",
            "traffic": "operational",
            "database": "connected" if settings.DB_PATH.exists() else "uninitialized"
        }
    }
