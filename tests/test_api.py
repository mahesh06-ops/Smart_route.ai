"""
API Integration tests using FastAPI TestClient / httpx.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from src.database.database import init_db

# Initialize database before tests
init_db()
client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "services" in data
    assert "weather" in data["services"]
    assert "traffic" in data["services"]


def test_api_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "maptiler_configured" in data
    assert "weather_provider" in data
    assert "traffic_provider" in data
    # Ensure raw secret is not leaked in public settings
    assert "eyJvcmciOi" not in str(data)


def test_api_map_config():
    response = client.get("/api/settings/map-config")
    assert response.status_code == 200
    assert "maptiler_api_key" in response.json()


def test_api_status():
    response = client.get("/api/settings/api-status")
    assert response.status_code == 200
    data = response.json()
    assert "maptiler" in data
    assert "routing" in data
    assert "weather" in data
    assert "traffic" in data


def test_weather_endpoints():
    res_live = client.get("/api/weather/live?location=Bengaluru")
    assert res_live.status_code == 200
    live_data = res_live.json()
    assert "weather" in live_data
    assert "temperature_c" in live_data["weather"]

    res_corridor = client.get("/api/weather/corridor?source=Ballari&destination=Bengaluru")
    assert res_corridor.status_code == 200
    corr_data = res_corridor.json()
    assert "origin_weather" in corr_data["corridor_weather"] or "origin_weather" in corr_data
    assert "destination_weather" in corr_data["corridor_weather"] or "destination_weather" in corr_data


def test_route_calculation_api():
    payload = {
        "source": "Ballari",
        "destination": "Bengaluru",
        "vehicle_type": "car",
        "preference": "balanced",
        "emergency_mode": False,
        "demo_mode": True
    }
    response = client.post("/api/routes/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["routes"]) >= 2
    assert "recommended_route" in data
    assert "explanation" in data
    assert data["recommended_route"]["smart_score"] > 0
    assert "traffic" in data["recommended_route"]
    assert "weather" in data["recommended_route"]


def test_history_lifecycle():
    # 1. Fetch history
    res = client.get("/api/history")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True


def test_visa_endpoints():
    res_status = client.get("/api/visa/status")
    assert res_status.status_code == 200
    res_cat = client.get("/api/visa/categories")
    assert res_cat.status_code == 200
    assert "Work Visa" in res_cat.json()
