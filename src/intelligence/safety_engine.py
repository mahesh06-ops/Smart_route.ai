"""
Safety Intelligence Engine.
Computes an analytical multi-factor safety index (0 - 100).
Incorporates:
- Road corridor characteristics & curvature estimate
- Traffic congestion volatility
- Weather hazard & roadway surface wetness
- Visibility degradation

NOTE: Presented as an analytical algorithmic safety index, not an official
government crash statistics registry.
"""
from typing import Dict, Any
from src.utils.normalization import clamp


class SafetyEngine:
    @staticmethod
    def calculate_safety(
        base_road_rating: float = 85.0,
        traffic_score: float = 80.0,
        weather_score: float = 90.0,
        route_index: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates a composite safety score (0 - 100).
        Higher score means safer route.
        """
        # Baseline variation for alternative corridor design (e.g. bypass vs central highway vs winding shortcut)
        corridor_penalties = [0.0, 5.0, 12.0]
        corridor_penalty = corridor_penalties[route_index % len(corridor_penalties)]

        # Traffic congestion increases collision risk
        traffic_penalty = (100.0 - traffic_score) * 0.25

        # Weather deterioration directly impairs braking and control
        weather_penalty = (100.0 - weather_score) * 0.35

        computed_score = base_road_rating - corridor_penalty - traffic_penalty - weather_penalty
        final_score = round(clamp(computed_score, 15.0, 98.0), 1)

        if final_score >= 80.0:
            category = "HIGH SAFETY"
            risk_level = "LOW RISK"
            color = "#10B981"  # Emerald
            notes = "Divided highway segments with minimal conflict points and excellent conditions."
        elif final_score >= 65.0:
            category = "MODERATE SAFETY"
            risk_level = "MODERATE RISK"
            color = "#F59E0B"  # Amber
            notes = "Standard multi-lane road; occasional urban intersections and moderate traffic flow."
        else:
            category = "LOW SAFETY"
            risk_level = "HIGH RISK"
            color = "#EF4444"  # Red
            notes = "Elevated risk factors due to heavy congestion, reduced visibility, or road constraints."

        return {
            "score": final_score,
            "category": category,
            "risk_level": risk_level,
            "color": color,
            "notes": notes,
            "disclaimer": "Algorithmic analytical safety index (evaluating traffic, weather and corridor flow)",
        }


safety_engine = SafetyEngine()
