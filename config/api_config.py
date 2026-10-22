"""
API Configuration Management for Smart Visa Route.
Safely manages external live API configurations, official immigration endpoints,
API keys via environment variables, and caching policies without leaking secrets.
"""
import os
from pathlib import Path
from typing import Dict, Any

# Root directory path
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH)
    except ImportError:
        pass


class VisaApiConfig:
    # API Keys (loaded strictly from environment variables)
    VISA_API_KEY: str = os.getenv("VISA_API_KEY", "")
    PASSPORT_INDEX_API_KEY: str = os.getenv("PASSPORT_INDEX_API_KEY", "")
    REST_COUNTRIES_URL: str = os.getenv("REST_COUNTRIES_URL", "https://restcountries.com/v3.1")
    
    # Cache settings
    CACHE_DIR: Path = BASE_DIR / "cache"
    CACHE_FILE: Path = BASE_DIR / "cache" / "visa_cache.json"
    CACHE_TTL_HOURS: int = int(os.getenv("VISA_CACHE_TTL_HOURS", "24"))
    
    # HTTP client parameters
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("VISA_REQUEST_TIMEOUT", "8.0"))
    MAX_RETRIES: int = 2
    
    # Operational mode
    ALLOW_DEMO_FALLBACK: bool = True
    
    @classmethod
    def get_public_config(cls) -> Dict[str, Any]:
        """Returns safe, unmasked configuration for frontend/client status checks."""
        return {
            "live_api_configured": bool(cls.VISA_API_KEY and not cls.VISA_API_KEY.startswith("YOUR_")),
            "cache_ttl_hours": cls.CACHE_TTL_HOURS,
            "timeout_seconds": cls.REQUEST_TIMEOUT_SECONDS,
            "cache_file_present": cls.CACHE_FILE.exists()
        }


api_config = VisaApiConfig()
