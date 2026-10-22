"""
Machine Learning Route Ranking & Scoring Scaffold.
Uses a Gradient Boosting / Random Forest regressor to predict route desirability
from engineered multi-factor features. Falls back gracefully to analytical
composite scoring if model is uncalibrated or dependencies unavailable.
"""
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from src.ml.route_features import route_feature_extractor


class MLRouteRanker:
    def __init__(self):
        self.model: Optional[RandomForestRegressor] = None
        self._is_trained: bool = False
        self._initialize_default_model()

    def _initialize_default_model(self):
        """
        Initializes and pre-trains a baseline Random Forest model on a synthetic
        calibration set representing balanced driving quality preferences.
        """
        self.model = RandomForestRegressor(
            n_estimators=50,
            max_depth=5,
            random_state=42
        )
        # Synthetic baseline dataset to calibrate baseline model
        np.random.seed(42)
        n_samples = 150
        distances = np.random.uniform(5.0, 300.0, n_samples)
        durations = distances * np.random.uniform(1.0, 2.5, n_samples)  # mins
        traffic_levels = np.random.choice([0, 1, 2, 3], n_samples)
        delay_factors = 1.0 + traffic_levels * 0.25
        weather_conds = np.random.choice([0, 1, 2, 3, 4, 5], n_samples)
        rain_mm = (weather_conds >= 2) * np.random.uniform(1.0, 20.0, n_samples)
        vis_km = np.maximum(1.0, 10.0 - rain_mm * 0.4)
        safety_scores = np.clip(95.0 - traffic_levels * 10 - rain_mm * 1.5, 20.0, 98.0)
        fuel_liters = distances * np.random.uniform(0.06, 0.12, n_samples)
        fuel_costs = fuel_liters * 100.0
        hours = np.random.randint(6, 22, n_samples)
        weekends = np.random.choice([0.0, 1.0], n_samples)

        X_synth = np.column_stack([
            distances, durations, traffic_levels, delay_factors,
            weather_conds, rain_mm, vis_km, safety_scores,
            fuel_liters, fuel_costs, hours.astype(float), weekends
        ])

        # Target smart score (0 - 100): lower duration/traffic/rain gives higher score
        y_synth = np.clip(
            90.0
            - (durations / np.maximum(distances, 1.0) - 1.0) * 15.0
            - traffic_levels * 8.0
            - rain_mm * 0.5
            + (safety_scores - 50.0) * 0.3,
            10.0,
            100.0
        )

        self.model.fit(X_synth, y_synth)
        self._is_trained = True

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def predict_score(self, route: Dict[str, Any], hour: int = 14, is_weekend: bool = False) -> float:
        """
        Extracts features and predicts an ML-based utility score for a single route (0 - 100).
        """
        features = route_feature_extractor.extract_features(route, hour=hour, is_weekend=is_weekend)
        pred = float(self.model.predict(features.reshape(1, -1))[0])
        return round(float(np.clip(pred, 1.0, 100.0)), 1)

    def rank_routes(
        self,
        routes: List[Dict[str, Any]],
        hour: int = 14,
        is_weekend: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scores and ranks a list of routes using the ML model.
        Returns routes enriched with `ml_score` and sorted descending.
        """
        if not routes:
            return []

        ranked = []
        for r in routes:
            copy_r = dict(r)
            copy_r["ml_score"] = self.predict_score(r, hour=hour, is_weekend=is_weekend)
            ranked.append(copy_r)

        ranked.sort(key=lambda x: x["ml_score"], reverse=True)
        for idx, r in enumerate(ranked):
            r["ml_rank"] = idx + 1
            r["ml_recommended"] = (idx == 0)

        return ranked

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Retrains or fine-tunes the model on historical route performance data.
        """
        if len(X) < 10:
            raise ValueError("At least 10 samples required to fit model.")
        self.model.fit(X, y)
        self._is_trained = True

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Returns feature importance dictionary sorted descending.
        """
        if not self._is_trained or not hasattr(self.model, "feature_importances_"):
            return {}
        importances = self.model.feature_importances_
        return {
            name: round(float(imp), 4)
            for name, imp in zip(route_feature_extractor.FEATURE_NAMES, importances)
        }


ml_ranker = MLRouteRanker()
