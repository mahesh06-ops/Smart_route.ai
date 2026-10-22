"""
Unit and integration tests for Smart Visa Route.
Validates all-country dynamic catalog, official source linkage, multi-factor scoring,
recommendation pipeline, what-if sensitivity simulations, and FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from visa.visa_models import UserProfile, PriorityEnum, WhatIfSimulationRequest
from visa.visa_data_service import visa_data_service
from visa.visa_scoring import scoring_engine
from visa.visa_recommendation import recommendation_pipeline
from visa.visa_cache import visa_cache

client = TestClient(app)


def test_visa_data_service_all_countries():
    """Verify that data service loads comprehensive global countries beyond standard 4."""
    countries = visa_data_service.get_all_countries()
    assert len(countries) >= 20, "Must support extensive global country catalog"
    
    # Check diverse representation across continents
    country_codes = {c.code for c in countries}
    expected_sample = {"DEU", "CAN", "AUS", "GBR", "USA", "JPN", "SGP", "ARE", "BRA", "ZAF", "NPL", "MEX", "IND"}
    for code in expected_sample:
        assert code in country_codes, f"Country {code} must be present in dynamic catalog"


def test_visa_data_service_search_and_filters():
    """Test dynamic search query and regional filters."""
    # Search by name
    nepal_results = visa_data_service.get_all_countries(search="Nepal")
    assert len(nepal_results) >= 1
    assert nepal_results[0].name == "Nepal"

    # Search by code
    brazil_results = visa_data_service.get_all_countries(search="BRA")
    assert len(brazil_results) >= 1
    assert brazil_results[0].name == "Brazil"

    # Region filter
    europe_results = visa_data_service.get_all_countries(region="Europe")
    assert len(europe_results) >= 5
    for c in europe_results:
        assert "Europe" in c.region

    # Safety filter
    safe_results = visa_data_service.get_all_countries(safety_min=85.0)
    for c in safe_results:
        assert c.safety_index >= 85.0


def test_visa_country_detail_and_official_source():
    """Verify deep country detail, category completeness, and valid official sources."""
    de_detail = visa_data_service.get_country_detail("DEU")
    assert de_detail is not None
    assert de_detail.name == "Germany"
    assert "https://" in de_detail.official_source.url or "http://" in de_detail.official_source.url
    assert len(de_detail.official_source.name) > 0
    assert "Work Visa" in de_detail.visas
    assert "Student Visa" in de_detail.visas
    assert "Digital Nomad Visa" in de_detail.visas

    # Verify official source for Japan
    jp_detail = visa_data_service.get_country_detail("JPN")
    assert jp_detail is not None
    assert "mofa.go.jp" in jp_detail.official_source.url


def test_visa_scoring_engine_priorities():
    """Test multi-factor scoring calculation with various user priority weights."""
    profile_balanced = UserProfile(
        current_country="India",
        age=28,
        education="master",
        field="tech",
        work_experience_years=5,
        purpose="Work Visa",
        monthly_budget_usd=3000,
        language_skills=["English"],
        priority=PriorityEnum.BALANCED
    )

    de_detail = visa_data_service.get_country_detail("DEU")
    score_balanced = scoring_engine.calculate_score(profile_balanced, de_detail)
    assert 0.0 <= score_balanced.total_score <= 100.0
    assert score_balanced.visa_suitability > 0
    assert score_balanced.safety > 0

    # Test safety priority weight boost
    profile_safety = profile_balanced.model_copy(update={"priority": PriorityEnum.SAFETY})
    score_safety = scoring_engine.calculate_score(profile_safety, de_detail)
    assert 0.0 <= score_safety.total_score <= 100.0


def test_visa_recommendation_pipeline():
    """Test full recommendation pipeline evaluating ALL countries."""
    profile = UserProfile(
        current_country="India",
        age=27,
        education="master",
        field="tech",
        work_experience_years=4,
        purpose="Work Visa",
        monthly_budget_usd=2800,
        language_skills=["English"],
        family_status="single",
        priority=PriorityEnum.JOB
    )

    rec = recommendation_pipeline.evaluate_profile(profile)
    assert rec.total_countries_evaluated >= 20
    assert len(rec.top_3) == 3
    assert len(rec.top_10) == 10
    
    # Top 3 must have badges assigned
    assert rec.top_3[0].badge == "⭐ BEST VISA ROUTE"
    assert rec.top_3[1].badge == "🥈 TOP RUNNER-UP"
    assert rec.top_3[2].badge == "🥉 HIGHLY RECOMMENDED"

    # Smart score must be in descending order
    scores = [item.smart_score for item in rec.top_10]
    assert scores == sorted(scores, reverse=True), "Top 10 must be strictly sorted descending"

    # Official source must be attached
    for item in rec.top_10:
        assert item.official_source.url != ""
        assert len(item.pros) > 0
        assert len(item.trade_offs) > 0


def test_visa_what_if_simulator():
    """Test sensitivity analysis when adjusting experience, budget, and priority."""
    base_profile = UserProfile(
        current_country="India",
        age=24,
        education="bachelor",
        field="tech",
        work_experience_years=1,
        purpose="Work Visa",
        monthly_budget_usd=1200,
        language_skills=["English"],
        priority=PriorityEnum.BALANCED
    )

    req = WhatIfSimulationRequest(
        base_profile=base_profile,
        adjusted_experience=6,
        adjusted_budget=4000,
        adjusted_priority=PriorityEnum.JOB
    )

    sim_res = recommendation_pipeline.simulate_what_if(req)
    assert len(sim_res.simulated_scores) > 0
    assert len(sim_res.score_deltas) > 0


def test_visa_api_endpoints():
    """Test FastAPI API endpoints for Smart Visa Route."""
    # 1. Status
    res_status = client.get("/api/visa/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["success"] is True

    # 2. Categories
    res_cats = client.get("/api/visa/categories")
    assert res_cats.status_code == 200
    cats = res_cats.json()
    assert "Work Visa" in cats
    assert "Student Visa" in cats

    # 3. Countries list
    res_countries = client.get("/api/visa/countries?search=Canada")
    assert res_countries.status_code == 200
    countries = res_countries.json()
    assert len(countries) >= 1
    assert countries[0]["name"] == "Canada"

    # 4. Country detail
    res_detail = client.get("/api/visa/country/SGP")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["name"] == "Singapore"
    assert "Work Visa" in detail["visas"]

    # 5. Recommendation POST
    payload = {
        "current_country": "India",
        "age": 29,
        "education": "master",
        "field": "tech",
        "work_experience_years": 5,
        "purpose": "Work Visa",
        "monthly_budget_usd": 3000,
        "language_skills": ["English"],
        "family_status": "single",
        "priority": "balanced"
    }
    res_rec = client.post("/api/visa/recommend", json=payload)
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert len(rec_data["top_3"]) == 3
    assert len(rec_data["top_10"]) == 10

    # 6. Comparison POST (Any 3 countries: Germany, Japan, UAE)
    comp_payload = {
        "country_codes": ["DEU", "JPN", "ARE"],
        "purpose": "Work Visa",
        "user_budget": 2500
    }
    res_comp = client.post("/api/visa/compare", json=comp_payload)
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert len(comp_data["countries"]) == 3

    # 7. Cache refresh POST
    res_refresh = client.post("/api/visa/cache/refresh")
    assert res_refresh.status_code == 200
    assert res_refresh.json()["status"] == "success"
