"""
Unit tests for Fuel Consumption & Cost Engine.
"""
import pytest
from src.intelligence.fuel_engine import fuel_engine


def test_car_fuel_calculation():
    # 150 km, car default is 15 km/L -> 10.0 L
    # Price = 100 -> Cost = 1000
    res = fuel_engine.calculate_fuel(distance_km=150.0, vehicle_type="car", fuel_price=100.0)
    assert res["fuel_liters"] == 10.0
    assert res["fuel_cost"] == 1000.0
    assert res["vehicle_type"] == "car"


def test_bike_fuel_calculation():
    # 90 km, bike default is 45 km/L -> 2.0 L
    res = fuel_engine.calculate_fuel(distance_km=90.0, vehicle_type="bike", fuel_price=100.0)
    assert res["fuel_liters"] == 2.0
    assert res["fuel_cost"] == 200.0


def test_custom_mileage():
    # 200 km, custom mileage 20 km/L -> 10.0 L
    res = fuel_engine.calculate_fuel(distance_km=200.0, vehicle_type="custom", custom_mileage=20.0, fuel_price=95.0)
    assert res["fuel_liters"] == 10.0
    assert res["fuel_cost"] == 950.0


def test_zero_or_negative_mileage_defense():
    # Zero or negative mileage should fallback safely without ZeroDivisionError
    res = fuel_engine.calculate_fuel(distance_km=150.0, custom_mileage=0.0)
    assert res["fuel_liters"] > 0
