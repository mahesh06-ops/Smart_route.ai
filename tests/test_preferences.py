"""
Unit tests for Preference Engine & Weighting Profiles.
"""
import pytest
from src.intelligence.preference_engine import preference_engine


def test_balanced_weights_sum():
    w = preference_engine.get_weights("balanced")
    assert round(sum(w.values()), 4) == 1.0
    assert w["time"] == 0.25
    assert w["traffic"] == 0.20


def test_fastest_weights_priority():
    w = preference_engine.get_weights("fastest")
    assert round(sum(w.values()), 4) == 1.0
    # Fastest must assign highest weight to time
    assert w["time"] > w["safety"]
    assert w["time"] > w["fuel"]


def test_safest_weights_priority():
    w = preference_engine.get_weights("safest")
    assert round(sum(w.values()), 4) == 1.0
    assert w["safety"] > w["time"]
    assert w["safety"] > w["fuel"]


def test_fuel_efficient_weights_priority():
    w = preference_engine.get_weights("fuel_efficient")
    assert round(sum(w.values()), 4) == 1.0
    assert w["fuel"] > w["time"]


def test_emergency_mode_override():
    w = preference_engine.get_weights("balanced", emergency_mode=True)
    assert round(sum(w.values()), 4) == 1.0
    # Emergency mode zeroes out fuel and distance
    assert w["fuel"] == 0.0
    assert w["distance"] == 0.0
    assert w["time"] >= 0.50
