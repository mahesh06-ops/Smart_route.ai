"""
Traffic Intelligence Engine.
Evaluates traffic congestion, delay multipliers, and normalizes into a 0 - 100 traffic score.
Categories: LOW, MODERATE, HIGH, HEAVY.
Clearly indicates data source (Live vs Simulated).
"""
import random
from typing import Dict, Any, Optional


class TrafficEngine:
    SEVERITY_MAPPING = {
        "LOW": {"score": 90, "delay_factor": 1.05, "desc": "Free flowing traffic"},
        "MODERATE": {"score": 70, "delay_factor": 1.20, "desc": "Typical moving congestion"},
        "HIGH": {"score": 45, "delay_factor": 1.45, "desc": "Slow-and-go bottleneck sections"},
        "HEAVY": {"score": 25, "delay_factor": 1.75, "desc": "Severe congestion / standstill delays"},
    }

    @classmethod
    def evaluate_traffic(
        cls,
        base_duration_minutes: float,
        route_index: int = 0,
        forced_level: Optional[str] = None,
        is_live: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates traffic conditions for a given route.
        Returns level, score (0-100 where higher is smoother), delay minutes, and transparency label.
        """
        if forced_level and forced_level.upper() in cls.SEVERITY_MAPPING:
            level = forced_level.upper()
        else:
            # Deterministic yet distinct distribution across alternative routes
            levels = ["LOW", "MODERATE", "HIGH"]
            level = levels[route_index % len(levels)]

        info = cls.SEVERITY_MAPPING[level]
        actual_delay_factor = info["delay_factor"]
        traffic_delay_minutes = round(base_duration_minutes * (actual_delay_factor - 1.0), 1)
        total_duration_with_traffic = round(base_duration_minutes + traffic_delay_minutes, 1)

        return {
            "level": level,
            "score": info["score"],  # Higher score = smoother traffic
            "delay_factor": actual_delay_factor,
            "delay_minutes": traffic_delay_minutes,
            "duration_with_traffic": total_duration_with_traffic,
            "description": info["desc"],
            "is_live": is_live,
            "data_source": "Live Traffic API" if is_live else "Traffic data simulated / analytical model",
        }


traffic_engine = TrafficEngine()
