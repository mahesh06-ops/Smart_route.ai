"""
Feature Extraction Pipeline for Machine Learning Preparation.
Converts route attributes and environmental conditions into structured numerical
feature vectors for training future regression or ranking models (Random Forest,
Gradient Boosting, Decision Tree).
"""
from typing import Dict, Any, List
import numpy as np


class RouteFeatureExtractor:
    FEATURE_NAMES = [
        "distance_km",
        "duration_minutes",
        "traffic_level_encoded",
        "traffic_delay_factor",
        "weather_condition_encoded",
        "weather_rain_mm",
        "weather_visibility_km",
        "safety_score",
        "fuel_liters",
        "fuel_cost",
        "hour_of_day",
        "is_weekend",
    ]

    TRAFFIC_MAP = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "HEAVY": 3}
    WEATHER_MAP = {"CLEAR": 0, "CLOUDY": 1, "RAIN": 2, "HEAVY RAIN": 3, "FOG": 4, "STORM": 5}

    @classmethod
    def extract_features(cls, route: Dict[str, Any], hour: int = 14, is_weekend: bool = False) -> np.ndarray:
        """
        Extracts a flat NumPy feature vector from a scored route dictionary.
        """
        dist = float(route.get("distance_km", 0.0))
        dur = float(route.get("duration_minutes", 0.0))

        traffic = route.get("traffic", {})
        t_level = cls.TRAFFIC_MAP.get(traffic.get("level", "LOW"), 0)
        t_factor = float(traffic.get("delay_factor", 1.0))

        weather = route.get("weather", {})
        w_cond = cls.WEATHER_MAP.get(weather.get("condition", "CLEAR"), 0)
        w_rain = float(weather.get("rain_mm", 0.0))
        w_vis = float(weather.get("visibility_km", 10.0))

        safety = float(route.get("safety", {}).get("score", 80.0))

        fuel = route.get("fuel", {})
        f_liters = float(fuel.get("fuel_liters", 0.0))
        f_cost = float(fuel.get("fuel_cost", 0.0))

        features = [
            dist,
            dur,
            t_level,
            t_factor,
            w_cond,
            w_rain,
            w_vis,
            safety,
            f_liters,
            f_cost,
            float(hour),
            1.0 if is_weekend else 0.0,
        ]
        return np.array(features, dtype=np.float32)

    @classmethod
    def extract_dataset(cls, routes_list: List[Dict[str, Any]]) -> np.ndarray:
        """Extracts a matrix of feature vectors from multiple routes."""
        if not routes_list:
            return np.empty((0, len(cls.FEATURE_NAMES)))
        return np.vstack([cls.extract_features(r) for r in routes_list])


route_feature_extractor = RouteFeatureExtractor()
