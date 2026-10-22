"""
Route Preference Engine.
Configures dynamic weight profiles across multiple factors.
Supports:
- BALANCED
- FASTEST
- SHORTEST
- SAFEST
- FUEL EFFICIENT
- EMERGENCY MODE
"""
from typing import Dict, Any


class PreferenceEngine:
    # Baseline weights for standard profiles
    DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
        "balanced": {
            "time": 0.25,
            "traffic": 0.20,
            "safety": 0.20,
            "weather": 0.15,
            "fuel": 0.10,
            "distance": 0.10,
        },
        "fastest": {
            "time": 0.45,
            "traffic": 0.25,
            "safety": 0.10,
            "weather": 0.05,
            "fuel": 0.05,
            "distance": 0.10,
        },
        "shortest": {
            "distance": 0.45,
            "time": 0.20,
            "traffic": 0.10,
            "safety": 0.10,
            "weather": 0.05,
            "fuel": 0.10,
        },
        "safest": {
            "safety": 0.40,
            "weather": 0.25,
            "traffic": 0.15,
            "time": 0.10,
            "distance": 0.05,
            "fuel": 0.05,
        },
        "fuel_efficient": {
            "fuel": 0.40,
            "distance": 0.25,
            "traffic": 0.10,
            "time": 0.10,
            "safety": 0.10,
            "weather": 0.05,
        },
    }

    # Emergency mode strongly prioritizes travel time, traffic flow, and safety
    EMERGENCY_WEIGHTS: Dict[str, float] = {
        "time": 0.50,
        "traffic": 0.25,
        "safety": 0.20,
        "weather": 0.05,
        "distance": 0.00,
        "fuel": 0.00,
    }

    @classmethod
    def get_weights(cls, preference: str, emergency_mode: bool = False) -> Dict[str, float]:
        """
        Returns normalized weights mapping for the specified preference.
        If emergency_mode is True, returns emergency priority weights.
        """
        if emergency_mode:
            return cls.EMERGENCY_WEIGHTS.copy()

        norm_pref = preference.lower().strip().replace(" ", "_").replace("-", "_")
        weights = cls.DEFAULT_WEIGHTS.get(norm_pref, cls.DEFAULT_WEIGHTS["balanced"]).copy()

        # Guarantee weights sum exactly to 1.0
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return weights


preference_engine = PreferenceEngine()
