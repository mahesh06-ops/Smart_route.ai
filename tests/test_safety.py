"""
Unit tests for Safety Intelligence Engine.
"""
import pytest
from src.intelligence.safety_engine import safety_engine, SafetyEngine


def test_safety_engine_defaults():
    result = safety_engine.calculate_safety()
    assert "score" in result
    assert "category" in result
    assert "risk_level" in result
    assert "color" in result
    assert 15.0 <= result["score"] <= 98.0


def test_safety_engine_corridor_penalty():
    # Route index 0 vs 1 vs 2 should have different corridor penalties
    s0 = safety_engine.calculate_safety(base_road_rating=85.0, traffic_score=80.0, weather_score=90.0, route_index=0)
    s1 = safety_engine.calculate_safety(base_road_rating=85.0, traffic_score=80.0, weather_score=90.0, route_index=1)
    s2 = safety_engine.calculate_safety(base_road_rating=85.0, traffic_score=80.0, weather_score=90.0, route_index=2)

    assert s0["score"] > s1["score"] > s2["score"]


def test_safety_engine_categories():
    # Excellent conditions -> HIGH SAFETY
    high = safety_engine.calculate_safety(base_road_rating=95.0, traffic_score=95.0, weather_score=95.0, route_index=0)
    assert high["category"] == "HIGH SAFETY"
    assert high["risk_level"] == "LOW RISK"

    # Degraded conditions -> LOW SAFETY
    low = safety_engine.calculate_safety(base_road_rating=60.0, traffic_score=20.0, weather_score=20.0, route_index=2)
    assert low["category"] == "LOW SAFETY"
    assert low["risk_level"] == "HIGH RISK"
    assert low["color"] == "#EF4444"
