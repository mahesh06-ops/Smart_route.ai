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
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    except ImportError:
        pass


class Settings:
    # Service Information
    APP_NAME: str = "Smart Route AI"
    APP_VERSION: str = "1.0.0"
    TAGLINE: str = "Find the smartest route, not just the shortest route."

    # Environment file path
    ENV_PATH: Path = ENV_PATH

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # API Keys
    _raw_maptiler = os.getenv("MAPTILER_API_KEY", "").strip()
    MAPTILER_API_KEY: str = "" if _raw_maptiler.startswith("YOUR_") else _raw_maptiler

    _raw_weather = os.getenv("WEATHER_API_KEY", "").strip() or (os.getenv("WEATHER_PROVIDER", "").strip() if len(os.getenv("WEATHER_PROVIDER", "").strip()) > 15 else "")
    WEATHER_API_KEY: str = "" if _raw_weather.startswith("YOUR_") else _raw_weather
    _raw_wp = os.getenv("WEATHER_PROVIDER", "openweathermap").lower().strip()
    WEATHER_PROVIDER: str = "openweathermap" if len(_raw_wp) > 15 else _raw_wp

    _raw_traffic = os.getenv("TRAFFIC_API_KEY", "").strip() or (os.getenv("TRAFFIC_PROVIDER", "").strip() if len(os.getenv("TRAFFIC_PROVIDER", "").strip()) > 15 else "")
    TRAFFIC_API_KEY: str = "" if _raw_traffic.startswith("YOUR_") else _raw_traffic
    _raw_tp = os.getenv("TRAFFIC_PROVIDER", "tomtom").lower().strip()
    TRAFFIC_PROVIDER: str = "tomtom" if len(_raw_tp) > 15 else _raw_tp

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
            "weather_configured": True,  # OpenWeatherMap / Open-Meteo available
            "traffic_configured": True,  # TomTom / Simulated available
            "weather_provider": cls.WEATHER_PROVIDER,
            "traffic_provider": cls.TRAFFIC_PROVIDER,
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
