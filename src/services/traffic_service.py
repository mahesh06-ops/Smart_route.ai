"""
Traffic Service for Smart Route AI.
Integrates live traffic data via TomTom Routing and Flow APIs with
resilient fallback to the analytical traffic simulation engine.
Transparently labels data source ("Live TomTom Traffic API" vs "Traffic data simulated / analytical model").
"""
import time
import math
from typing import Dict, Any, List, Optional
import httpx

from src.config.settings import settings
from src.intelligence.traffic_engine import traffic_engine
from src.utils.logging_config import logger


class TrafficService:
    TOMTOM_ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute"
    TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

    # In-memory TTL cache: key -> (timestamp, result_dict)
    _cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
    CACHE_TTL_SECONDS = 300.0  # 5 minutes

    @classmethod
    def _get_cached(cls, key: str) -> Optional[Dict[str, Any]]:
        if key in cls._cache:
            ts, val = cls._cache[key]
            if time.time() - ts < cls.CACHE_TTL_SECONDS:
                return dict(val)
            del cls._cache[key]
        return None

    @classmethod
    def _set_cached(cls, key: str, val: Dict[str, Any]):
        # Keep cache size bounded
        if len(cls._cache) > 200:
            cls._cache.clear()
        cls._cache[key] = (time.time(), dict(val))

    @classmethod
    async def _fetch_tomtom_traffic(
        cls,
        base_duration_minutes: float,
        coordinates: Optional[List[List[float]]] = None,
        route_index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Queries TomTom calculateRoute with traffic for real delay and congestion."""
        key = settings.TRAFFIC_API_KEY
        if not key or key.startswith("YOUR_"):
            return None

        if not coordinates or len(coordinates) < 2:
            return None

        # Build coordinate string for TomTom: lat,lon:lat,lon
        start_pt = coordinates[0]
        end_pt = coordinates[-1]
        
        # If route has enough points, use a midpoint waypoint to represent the specific corridor
        mid_pt = None
        if len(coordinates) >= 4 and route_index > 0:
            mid_idx = len(coordinates) // 2
            mid_pt = coordinates[mid_idx]

        if mid_pt:
            route_str = f"{round(start_pt[0], 4)},{round(start_pt[1], 4)}:{round(mid_pt[0], 4)},{round(mid_pt[1], 4)}:{round(end_pt[0], 4)},{round(end_pt[1], 4)}"
        else:
            route_str = f"{round(start_pt[0], 4)},{round(start_pt[1], 4)}:{round(end_pt[0], 4)},{round(end_pt[1], 4)}"

        cache_key = f"tomtom_{route_str}"
        cached = cls._get_cached(cache_key)
        if cached:
            # Scale total duration according to the current base_duration_minutes
            res = dict(cached)
            delay_mins = res["delay_minutes"]
            res["duration_with_traffic"] = round(base_duration_minutes + delay_mins, 1)
            return res

        url = f"{cls.TOMTOM_ROUTING_URL}/{route_str}/json"
        params = {
            "key": key,
            "traffic": "true",
            "travelMode": "car",
            "computeTravelTimeFor": "all"
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    routes = data.get("routes", [])
                    if not routes:
                        return None
                    
                    summary = routes[0].get("summary", {})
                    travel_time_sec = float(summary.get("travelTimeInSeconds", base_duration_minutes * 60))
                    traffic_delay_sec = float(summary.get("trafficDelayInSeconds", 0.0))
                    
                    delay_minutes = round(traffic_delay_sec / 60.0, 1)
                    duration_with_traffic = round(base_duration_minutes + delay_minutes, 1)

                    free_flow_sec = max(1.0, travel_time_sec - traffic_delay_sec)
                    delay_factor = round(travel_time_sec / free_flow_sec, 2)

                    # Compute score and category
                    if delay_factor < 1.08 and delay_minutes < 5:
                        level = "LOW"
                        desc = "Free flowing traffic (TomTom Live)"
                        score = 92
                    elif delay_factor < 1.25 or delay_minutes < 20:
                        level = "MODERATE"
                        desc = "Moderate congestion along corridor (TomTom Live)"
                        score = 72
                    elif delay_factor < 1.50 or delay_minutes < 45:
                        level = "HIGH"
                        desc = "Heavy congestion bottlenecks detected (TomTom Live)"
                        score = 48
                    else:
                        level = "HEAVY"
                        desc = "Severe standstill delays on corridor (TomTom Live)"
                        score = 25

                    result = {
                        "level": level,
                        "score": score,
                        "delay_factor": delay_factor,
                        "delay_minutes": delay_minutes,
                        "duration_with_traffic": duration_with_traffic,
                        "description": desc,
                        "is_live": True,
                        "data_source": "Live TomTom Traffic API",
                    }

                    cls._set_cached(cache_key, result)
                    return result

        except Exception as e:
            logger.warning(f"TomTom live traffic call failed for corridor: {e}")
            return None

    @classmethod
    async def get_route_traffic(
        cls,
        base_duration_minutes: float,
        route_index: int = 0,
        demo_mode: bool = False,
        coordinates: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Retrieves traffic profile for a route.
        Attempts real TomTom traffic evaluation when configured and not in demo mode.
        Falls back to high-fidelity analytical traffic simulation when offline or unkeyed.
        """
        if not demo_mode and settings.TRAFFIC_PROVIDER == "tomtom" and settings.TRAFFIC_API_KEY:
            live_result = await cls._fetch_tomtom_traffic(
                base_duration_minutes=base_duration_minutes,
                coordinates=coordinates,
                route_index=route_index
            )
            if live_result:
                return live_result

        # Analytical simulation fallback
        return traffic_engine.evaluate_traffic(
            base_duration_minutes=base_duration_minutes,
            route_index=route_index,
            is_live=False
        )


traffic_service = TrafficService()
