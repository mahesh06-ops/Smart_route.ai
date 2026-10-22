"""
API Package for Smart Route AI.
"""
from backend.api.health import router as health_router
from backend.api.route_api import router as route_router
from backend.api.history_api import router as history_router
from backend.api.settings_api import router as settings_router
from backend.api.weather_api import weather_router

__all__ = ["health_router", "route_router", "history_router", "settings_router", "weather_router"]

