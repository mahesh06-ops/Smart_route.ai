"""
Geocoding Service for Smart Route AI.
Resolves human-readable place names (e.g. Ballari, Bengaluru, Hyderabad, Mumbai)
to latitude and longitude coordinates.
Features:
- Instant high-precision cache for major Indian and world hubs
- Live Nominatim / OpenStreetMap geocoding fallback
- Robust error handling for unknown, ambiguous, or failed queries
"""
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import httpx
from src.utils.logging_config import logger
from src.utils.validation import sanitize_string, validate_coordinates

# Pre-cached coordinates for guaranteed fast and reliable demo lookup
CITY_CACHE: Dict[str, Tuple[float, float, str]] = {
    "ballari": (15.1394, 76.9214, "Ballari, Karnataka, India"),
    "bellary": (15.1394, 76.9214, "Ballari, Karnataka, India"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad, Telangana, India"),
    "chennai": (13.0827, 80.2707, "Chennai, Tamil Nadu, India"),
    "mumbai": (19.0760, 72.8777, "Mumbai, Maharashtra, India"),
    "pune": (18.5204, 73.8567, "Pune, Maharashtra, India"),
    "delhi": (28.6139, 77.2090, "New Delhi, Delhi, India"),
    "new delhi": (28.6139, 77.2090, "New Delhi, Delhi, India"),
    "kolkata": (22.5726, 88.3639, "Kolkata, West Bengal, India"),
    "mysuru": (12.2958, 76.6394, "Mysuru, Karnataka, India"),
    "mysore": (12.2958, 76.6394, "Mysuru, Karnataka, India"),
    "hubballi": (15.3647, 75.1240, "Hubballi, Karnataka, India"),
    "hubli": (15.3647, 75.1240, "Hubballi, Karnataka, India"),
    "mangalore": (12.9141, 74.8560, "Mangaluru, Karnataka, India"),
    "mangaluru": (12.9141, 74.8560, "Mangaluru, Karnataka, India"),
    "goa": (15.2993, 74.1240, "Panaji, Goa, India"),
    "panaji": (15.4909, 73.8278, "Panaji, Goa, India"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad, Gujarat, India"),
    "jaipur": (26.9124, 75.7873, "Jaipur, Rajasthan, India"),
    "coimbatore": (11.0168, 76.9558, "Coimbatore, Tamil Nadu, India"),
    "kochi": (9.9312, 76.2673, "Kochi, Kerala, India"),
    "vijayawada": (16.5062, 80.6480, "Vijayawada, Andhra Pradesh, India"),
    "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam, Andhra Pradesh, India"),
    "tirupati": (13.6288, 79.4192, "Tirupati, Andhra Pradesh, India"),
    "davangere": (14.4644, 75.9218, "Davanagere, Karnataka, India"),
    "shivamogga": (13.9299, 75.5681, "Shivamogga, Karnataka, India"),
    "shimoga": (13.9299, 75.5681, "Shivamogga, Karnataka, India"),
    "hampi": (15.3350, 76.4600, "Hampi, Karnataka, India"),
    "anantapur": (14.6819, 77.6006, "Anantapur, Andhra Pradesh, India"),
    "kurnool": (15.8281, 78.0373, "Kurnool, Andhra Pradesh, India"),
    # International hubs
    "london": (51.5074, -0.1278, "London, United Kingdom"),
    "paris": (48.8566, 2.3522, "Paris, France"),
    "tokyo": (35.6762, 139.6503, "Tokyo, Japan"),
    "new york": (40.7128, -74.0060, "New York, NY, USA"),
    "san francisco": (37.7749, -122.4194, "San Francisco, CA, USA"),
    "singapore": (1.3521, 103.8198, "Singapore"),
    "dubai": (25.2048, 55.2708, "Dubai, United Arab Emirates"),
}


class GeocodingService:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "SmartRouteAI/1.0 (academic-navigation-system)"

    @classmethod
    async def geocode(cls, query: str) -> Dict[str, Any]:
        """
        Geocodes a place name to coordinates {lat, lon, display_name, source}.
        """
        cleaned = sanitize_string(query)
        if not cleaned:
            return {"success": False, "error": "Location query cannot be empty."}

        # 1. Check instant curated cache
        lookup_key = cleaned.lower()
        if lookup_key in CITY_CACHE:
            lat, lon, display_name = CITY_CACHE[lookup_key]
            return {
                "success": True,
                "lat": lat,
                "lon": lon,
                "display_name": display_name,
                "query": cleaned,
                "source": "curated_cache",
            }

        # Check partial match in cache
        for k, (lat, lon, d_name) in CITY_CACHE.items():
            if k in lookup_key or lookup_key in k:
                return {
                    "success": True,
                    "lat": lat,
                    "lon": lon,
                    "display_name": d_name,
                    "query": cleaned,
                    "source": "curated_cache_partial",
                }

        # 2. Query live Nominatim API
        try:
            params = {
                "q": cleaned,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            headers = {"User-Agent": cls.USER_AGENT}
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(cls.NOMINATIM_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0:
                        first = data[0]
                        lat = float(first["lat"])
                        lon = float(first["lon"])
                        if validate_coordinates(lat, lon):
                            return {
                                "success": True,
                                "lat": lat,
                                "lon": lon,
                                "display_name": first.get("display_name", cleaned),
                                "query": cleaned,
                                "source": "nominatim_live",
                            }
        except Exception as e:
            logger.warning(f"Live geocoding network attempt for '{cleaned}' failed: {e}")

        # 3. Friendly failure message
        return {
            "success": False,
            "error": f"Location '{cleaned}' not found. Please try entering a known city name (e.g. Ballari, Bengaluru, Hyderabad, Mumbai).",
            "query": cleaned,
        }


geocoding_service = GeocodingService()
