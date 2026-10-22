"""
Unit tests for Intelligent Route Scoring & Normalization Engine.
"""
import pytest
from src.utils.normalization import normalize_metric, clamp
from src.intelligence.route_scoring import route_scoring_engine


def test_clamp():
    assert clamp(-5, 0, 100) == 0
    assert clamp(150, 0, 100) == 100
    assert clamp(42, 0, 100) == 42


def test_normalize_metric():
    # Lower is better (e.g. duration: 60 mins vs 120 mins)
    # 60 mins should get 100.0, 120 mins should get 0.0
    score_fast = normalize_metric(60, 60, 120, higher_is_better=False)
    score_slow = normalize_metric(120, 60, 120, higher_is_better=False)
    assert score_fast == 100.0
    assert score_slow == 0.0

    # Higher is better (e.g. safety: 90 vs 70)
    score_safe = normalize_metric(90, 70, 90, higher_is_better=True)
    score_risk = normalize_metric(70, 70, 90, higher_is_better=True)
    assert score_safe == 100.0
    assert score_risk == 0.0


def test_route_scoring_engine_ranking():
    mock_routes = [
        {
            "route_id": "r1",
            "route_name": "Route 1",
            "distance_km": 100.0,
            "duration_minutes": 90.0,
            "traffic": {"score": 90, "level": "LOW"},
            "safety": {"score": 90, "category": "HIGH SAFETY"},
            "weather": {"score": 95, "condition": "CLEAR"},
            "fuel": {"fuel_liters": 7.0, "fuel_cost": 700.0},
        },
        {
            "route_id": "r2",
            "route_name": "Route 2",
            "distance_km": 120.0,
            "duration_minutes": 140.0,
            "traffic": {"score": 40, "level": "HIGH"},
            "safety": {"score": 60, "category": "LOW SAFETY"},
            "weather": {"score": 60, "condition": "RAIN"},
            "fuel": {"fuel_liters": 12.0, "fuel_cost": 1200.0},
        }
    ]

    scored = route_scoring_engine.score_routes(mock_routes, preference="balanced")
    assert len(scored) == 2
    # r1 must be ranked first with higher score
    assert scored[0]["route_id"] == "r1"
    assert scored[0]["is_recommended"] is True
    assert scored[0]["smart_score"] > scored[1]["smart_score"]
    assert "score_breakdown" in scored[0]
    assert 0 <= scored[0]["smart_score"] <= 100
