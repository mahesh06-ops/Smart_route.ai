"""
Unit tests for Machine Learning Preparation & Model Scaffold.
"""
import pytest
import numpy as np
from src.ml.route_features import route_feature_extractor, RouteFeatureExtractor
from src.ml.model_scaffold import ml_ranker, MLRouteRanker


def test_feature_extraction_single_route():
    mock_route = {
        "distance_km": 150.0,
        "duration_minutes": 120.0,
        "traffic": {"level": "MODERATE", "delay_factor": 1.25},
        "weather": {"condition": "CLEAR", "rain_mm": 0.0, "visibility_km": 10.0},
        "safety": {"score": 88.0},
        "fuel": {"fuel_liters": 11.2, "fuel_cost": 1120.0}
    }
    features = route_feature_extractor.extract_features(mock_route, hour=10, is_weekend=False)
    assert isinstance(features, np.ndarray)
    assert features.shape == (len(RouteFeatureExtractor.FEATURE_NAMES),)
    assert features[0] == 150.0  # distance_km
    assert features[1] == 120.0  # duration_minutes


def test_feature_extraction_dataset():
    routes = [
        {"distance_km": 10.0, "duration_minutes": 15.0},
        {"distance_km": 50.0, "duration_minutes": 60.0}
    ]
    matrix = route_feature_extractor.extract_dataset(routes)
    assert matrix.shape == (2, len(RouteFeatureExtractor.FEATURE_NAMES))

    empty_matrix = route_feature_extractor.extract_dataset([])
    assert empty_matrix.shape == (0, len(RouteFeatureExtractor.FEATURE_NAMES))


def test_ml_ranker_predict_and_rank():
    assert ml_ranker.is_trained is True

    routes = [
        {
            "route_id": "fast",
            "distance_km": 80.0,
            "duration_minutes": 70.0,
            "traffic": {"level": "LOW", "delay_factor": 1.0},
            "weather": {"condition": "CLEAR", "rain_mm": 0.0, "visibility_km": 10.0},
            "safety": {"score": 92.0},
            "fuel": {"fuel_liters": 6.0, "fuel_cost": 600.0}
        },
        {
            "route_id": "slow",
            "distance_km": 100.0,
            "duration_minutes": 150.0,
            "traffic": {"level": "HEAVY", "delay_factor": 2.0},
            "weather": {"condition": "STORM", "rain_mm": 18.0, "visibility_km": 3.0},
            "safety": {"score": 45.0},
            "fuel": {"fuel_liters": 15.0, "fuel_cost": 1500.0}
        }
    ]

    ranked = ml_ranker.rank_routes(routes)
    assert len(ranked) == 2
    assert "ml_score" in ranked[0]
    assert "ml_rank" in ranked[0]
    # Faster and cleaner route should have higher ML score
    assert ranked[0]["route_id"] == "fast"
    assert ranked[0]["ml_recommended"] is True

    importances = ml_ranker.get_feature_importances()
    assert isinstance(importances, dict)
    assert len(importances) == len(RouteFeatureExtractor.FEATURE_NAMES)
