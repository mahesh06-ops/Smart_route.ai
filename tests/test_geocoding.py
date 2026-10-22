"""
Unit tests for Geocoding and Location Validation.
"""
import pytest
from src.services.geocoding_service import geocoding_service, CITY_CACHE
from src.utils.validation import validate_route_request, validate_coordinates


def test_coordinate_validation():
    assert validate_coordinates(15.1394, 76.9214) is True
    assert validate_coordinates(95.0, 76.0) is False  # Lat > 90
    assert validate_coordinates(15.0, 190.0) is False # Lon > 180


def test_input_request_validation():
    # Empty inputs
    valid, msg = validate_route_request("", "Bengaluru")
    assert valid is False
    assert "both" in msg.lower()

    # Same source and destination
    valid, msg = validate_route_request("Bengaluru", "Bengaluru")
    assert valid is False
    assert "same" in msg.lower()

    # Valid inputs
    valid, msg = validate_route_request("Ballari", "Bengaluru")
    assert valid is True
    assert msg is None


@pytest.mark.anyio
async def test_geocoding_cache_lookup():
    res = await geocoding_service.geocode("Ballari")
    assert res["success"] is True
    assert round(res["lat"], 2) == 15.14
    assert round(res["lon"], 2) == 76.92
