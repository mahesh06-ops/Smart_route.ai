"""
Unit tests for Weather & Safety Intelligence Engines.
"""
import pytest
from src.intelligence.weather_engine import weather_engine
from src.intelligence.safety_engine import safety_engine


def test_weather_eval_clear():
    res = weather_engine.evaluate_weather(condition="CLEAR", temperature_c=30.0)
    assert res["condition"] == "CLEAR"
    assert res["score"] >= 95
    assert res["risk_penalty"] <= 5


def test_weather_eval_rain():
    res = weather_engine.evaluate_weather(condition="RAIN", rain_mm=5.0)
    assert res["condition"] == "RAIN"
    assert res["score"] < 80
    assert res["risk_penalty"] > 0


def test_safety_score_calculation():
    # Ideal conditions
    res_ideal = safety_engine.calculate_safety(base_road_rating=90.0, traffic_score=95.0, weather_score=95.0)
    assert res_ideal["score"] >= 80.0
    assert res_ideal["category"] == "HIGH SAFETY"

    # Degraded conditions (heavy congestion, bad weather)
    res_bad = safety_engine.calculate_safety(base_road_rating=75.0, traffic_score=30.0, weather_score=40.0)
    assert res_bad["score"] < res_ideal["score"]
    assert res_bad["category"] in ("MODERATE SAFETY", "LOW SAFETY")
