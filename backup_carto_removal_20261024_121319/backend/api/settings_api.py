
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


@router.get("/settings/map-config")
async def get_map_config():
    """Returns browser-facing basemap API keys for MapTiler and CARTO."""
    maptiler_key = settings.MAPTILER_API_KEY or ""
    carto_key = settings.CARTO_API_KEY or ""

    if maptiler_key.startswith("YOUR_"):
        maptiler_key = ""

    if carto_key.startswith("YOUR_"):
        carto_key = ""

    return {
        "maptiler_api_key": maptiler_key,
        "carto_api_key": carto_key,
    }


@router.get("/settings/api-status")
async def get_api_status():
    """Provides connectivity and setup status for external providers."""
    return {
        "maptiler": {
            "name": "MapTiler Vector Basemap",
            "status": (
                "Configured ✓"
                if settings.MAPTILER_API_KEY
                and not settings.MAPTILER_API_KEY.startswith("YOUR_")
                else "Pending Key"
            ),
        },
        "carto": {
            "name": "CARTO Basemap Layer",
            "status": (
                "Configured ✓"
                if settings.CARTO_API_KEY
                and not settings.CARTO_API_KEY.startswith("YOUR_")
                else "Pending Key"
            ),
            "attribution": settings.CARTO_ATTRIBUTION,
            "style_options": [
                "Dark Matter",
                "Positron Light",
                "Voyager",
            ],
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
        },
    }
