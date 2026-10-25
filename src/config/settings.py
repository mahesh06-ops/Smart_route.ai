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
    # MapTiler browser-facing basemap key; restrict it to trusted origins.
    MAPTILER_API_KEY: str = (
    os.getenv("MAPTILER_API_KEY", "").strip()
    or os.getenv("VITE_MAPTILER_API_KEY", "").strip()
    or os.getenv("MAP_API_KEY", "").strip()
)
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
            "maptiler_configured": bool(
                cls.MAPTILER_API_KEY
                and not cls.MAPTILER_API_KEY.startswith("YOUR_")
            ),
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

