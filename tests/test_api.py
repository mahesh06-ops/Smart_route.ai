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


def test_api_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "carto_configured" in data
    assert "carto_attribution" in data
    # Ensure raw secret is not leaked in public settings
    assert "eyJvcmciOi" not in str(data)


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


def test_history_lifecycle():
    # 1. Fetch history
    res = client.get("/api/history")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
