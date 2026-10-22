"""
Configuration Management for Smart Route AI.
Safely loads environment variables, provides defaults, and prevents secret leakage.
"""
import os
from pathlib import Path
from typing import Dict, Any

# Locate root directory containing .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH)
    except ImportError:
        pass


class Settings:
    # Service Information
    APP_NAME: str = "Smart Route AI"
    APP_VERSION: str = "1.0.0"
    TAGLINE: str = "Find the smartest route, not just the shortest route."

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # API Keys
    CARTO_API_KEY: str = os.getenv("CARTO_API_KEY", "")
    MAP_API_KEY: str = os.getenv("MAP_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    TRAFFIC_API_KEY: str = os.getenv("TRAFFIC_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_route.db")
    DB_PATH: Path = BASE_DIR / "smart_route.db"

    # Default Vehicle and Fuel Parameters
    DEFAULT_FUEL_PRICE: float = float(os.getenv("DEFAULT_FUEL_PRICE", "102.5"))
    VEHICLE_MILEAGE: Dict[str, float] = {
        "car": 15.0,        # km / Liter
        "bike": 45.0,       # km / Liter
        "suv": 11.0,        # km / Liter
        "custom": 14.0      # default custom km / Liter
    }

    # CARTO Basemap Styles
    CARTO_TILES = {
        "dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "light": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "voyager": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
    }
    CARTO_ATTRIBUTION: str = (
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> '
        'contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    )

    @classmethod
    def get_public_settings(cls) -> Dict[str, Any]:
        """
        Returns safe settings for frontend consumption.
        Never reveals secret API keys.
        """
        return {
            "app_name": cls.APP_NAME,
            "version": cls.APP_VERSION,
            "tagline": cls.TAGLINE,
            "carto_configured": bool(cls.CARTO_API_KEY and not cls.CARTO_API_KEY.startswith("YOUR_")),
            "carto_attribution": cls.CARTO_ATTRIBUTION,
            "carto_tiles": cls.CARTO_TILES,
            "routing_configured": True,  # OSRM + Fallback available
            "weather_configured": True,  # Open-Meteo + Fallback available
            "traffic_configured": True,  # Simulated + Live fallback available
            "default_fuel_price": cls.DEFAULT_FUEL_PRICE,
            "vehicle_mileage": cls.VEHICLE_MILEAGE,
        }

    @classmethod
    def get_masked_key(cls, key_val: str) -> str:
        """Safely mask API keys for logs and diagnostic views."""
        if not key_val or key_val.startswith("YOUR_"):
            return "Not Configured"
        if len(key_val) <= 8:
            return "********"
        return f"{key_val[:4]}...{key_val[-4:]}"


settings = Settings()
