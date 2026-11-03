"""
Health check and system diagnostics endpoint.
"""
from fastapi import APIRouter
from src.config.settings import settings
from backend.api.settings_api import check_provider_status

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Returns application status, version, and active subsystem checks."""
    provider_status = await check_provider_status()

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "services": {
            "geocoding": "operational",
            "routing": provider_status.get("routing", {}).get("status", "operational"),
            "weather": provider_status.get("weather", {}).get("status", "operational"),
            "traffic": provider_status.get("traffic", {}).get("status", "operational"),
            "maptiler": provider_status.get("maptiler", {}).get("status", "operational"),
            "database": "connected" if settings.DB_PATH.exists() else "uninitialized"
        }
    }
