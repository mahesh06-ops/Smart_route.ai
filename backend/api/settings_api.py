"""
Settings and Configuration API endpoints.
"""
from fastapi import APIRouter
from src.config.settings import settings

router = APIRouter(tags=["Settings"])


@router.get("/settings")
async def get_settings():
    """Returns safe frontend configuration."""
    return settings.get_public_settings()


@router.get("/settings/api-status")
async def get_api_status():
    """Provides connectivity and setup status for external providers."""
    return {
        "carto": {
            "name": "CARTO Basemap Layer",
            "status": "Configured ✓" if settings.CARTO_API_KEY and not settings.CARTO_API_KEY.startswith("YOUR_") else "Pending Key",
            "attribution": settings.CARTO_ATTRIBUTION,
            "style_options": ["Dark Matter (Default)", "Positron Light", "Voyager"]
        },
        "routing": {
            "name": "OSRM Routing Engine + Corridor Model",
            "status": "Configured ✓ (Live OSRM with Resilient Fallback)",
        },
        "weather": {
            "name": "Open-Meteo Meteorological Service",
            "status": "Configured ✓ (Live API with Simulation Fallback)",
        },
        "traffic": {
            "name": "Analytical Traffic Congestion Engine",
            "status": "Configured ✓ (Multi-factor Congestion Analysis)",
        }
    }
