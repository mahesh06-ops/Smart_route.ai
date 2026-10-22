"""
Traffic Service for Smart Route AI.
Integrates live traffic feeds when configured or evaluates routes using
the analytical traffic congestion simulation model.
Transparently labels whether traffic is live or simulated.
"""
from typing import Dict, Any, List
from src.intelligence.traffic_engine import traffic_engine
from src.config.settings import settings


class TrafficService:
    @classmethod
    def get_route_traffic(
        cls,
        base_duration_minutes: float,
        route_index: int = 0,
        demo_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves traffic profile for a route.
        """
        # If external traffic API key configured and not in demo mode:
        is_live = bool(settings.TRAFFIC_API_KEY and not demo_mode and not settings.TRAFFIC_API_KEY.startswith("YOUR_"))

        # We evaluate traffic via traffic intelligence engine
        return traffic_engine.evaluate_traffic(
            base_duration_minutes=base_duration_minutes,
            route_index=route_index,
            is_live=is_live
        )


traffic_service = TrafficService()
