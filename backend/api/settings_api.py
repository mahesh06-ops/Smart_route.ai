"""
Settings and Configuration API endpoints.
Provides frontend configuration and real-time connectivity testing for external providers.
"""
import time
import httpx
from fastapi import APIRouter
from src.config.settings import settings
from src.utils.logging_config import logger

router = APIRouter(tags=["Settings"])

_api_status_cache = {}
_api_status_cache_time = 0.0
CACHE_TTL = 60.0  # 60 seconds cache


async def check_provider_status() -> dict:
    global _api_status_cache, _api_status_cache_time
    now = time.time()
    if _api_status_cache and (now - _api_status_cache_time) < CACHE_TTL:
        return _api_status_cache

    statuses = {}

    async with httpx.AsyncClient(timeout=4.0) as client:
        # 1. MapTiler Check
        if not settings.MAPTILER_API_KEY or settings.MAPTILER_API_KEY.startswith("YOUR_"):
            maptiler_status = "Not Configured (Key Missing)"
        else:
            try:
                r = await client.get(f"https://api.maptiler.com/maps/streets-v2/style.json?key={settings.MAPTILER_API_KEY}")
                if r.status_code == 200:
                    maptiler_status = "Live (MapTiler Cloud Vector Tiles)"
                elif r.status_code == 403:
                    maptiler_status = "Key rejected (HTTP 403 - Check Allowed Origins)"
                elif r.status_code == 401:
                    maptiler_status = "Key rejected (HTTP 401 Unauthorized)"
                else:
                    maptiler_status = f"Status HTTP {r.status_code}"
            except Exception as e:
                maptiler_status = f"Connection error ({type(e).__name__})"

        # 2. Weather Check
        weather_status = "Fallback in use (Open-Meteo)"
        if settings.WEATHER_PROVIDER == "openweathermap" and settings.WEATHER_API_KEY:
            try:
                r = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": 12.9716, "lon": 77.5946, "appid": settings.WEATHER_API_KEY, "units": "metric"}
                )
                if r.status_code == 200:
                    weather_status = "Live (OpenWeatherMap API)"
                elif r.status_code == 401:
                    weather_status = "Key rejected (HTTP 401) - Fallback in use (Open-Meteo)"
                else:
                    weather_status = f"Fallback in use (HTTP {r.status_code})"
            except Exception:
                weather_status = "Fallback in use (Open-Meteo)"
        else:
            weather_status = "Live (Open-Meteo Public API)"

        # 3. TomTom Routing & Traffic Check
        tomtom_routing_status = "Fallback in use"
        tomtom_traffic_status = "Fallback in use"
        if settings.TRAFFIC_API_KEY and not settings.TRAFFIC_API_KEY.startswith("YOUR_"):
            try:
                r = await client.get(
                    "https://api.tomtom.com/routing/1/calculateRoute/12.9716,77.5946:12.9760,77.6000/json",
                    params={"key": settings.TRAFFIC_API_KEY, "maxAlternatives": 0}
                )
                if r.status_code == 200:
                    tomtom_routing_status = "Live (TomTom)"
                    tomtom_traffic_status = "Live (TomTom)"
                elif r.status_code in (401, 403):
                    tomtom_routing_status = f"Key rejected (HTTP {r.status_code})"
                    tomtom_traffic_status = f"Key rejected (HTTP {r.status_code})"
                else:
                    tomtom_routing_status = f"Fallback in use (HTTP {r.status_code})"
                    tomtom_traffic_status = f"Fallback in use (HTTP {r.status_code})"
            except Exception:
                tomtom_routing_status = "Fallback in use"
                tomtom_traffic_status = "Fallback in use"
        else:
            tomtom_routing_status = "Fallback in use"
            tomtom_traffic_status = "Fallback in use"

    statuses = {
        "maptiler": {
            "name": "MapTiler Vector Basemap",
            "status": maptiler_status,
        },
        "routing": {
            "name": "TomTom Routing Engine",
            "status": tomtom_routing_status,
        },
        "weather": {
            "name": f"Weather Provider ({settings.WEATHER_PROVIDER.title()})",
            "status": weather_status,
        },
        "traffic": {
            "name": f"Traffic Engine ({settings.TRAFFIC_PROVIDER.title()})",
            "status": tomtom_traffic_status,
        },
    }

    _api_status_cache = statuses
    _api_status_cache_time = now
    return statuses


@router.get("/settings")
async def get_settings():
    """Returns safe frontend configuration."""
    return settings.get_public_settings()


@router.get("/settings/map-config")
async def get_map_config():
    """Returns the browser-facing MapTiler basemap API key."""
    maptiler_key = settings.MAPTILER_API_KEY or ""
    if maptiler_key.startswith("YOUR_"):
        maptiler_key = ""

    return {
        "maptiler_api_key": maptiler_key,
    }


@router.get("/settings/api-status")
async def get_api_status():
    """Provides connectivity and setup status with lightweight real calls (cached 60s)."""
    return await check_provider_status()
