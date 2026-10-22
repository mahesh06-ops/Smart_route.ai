"""
FastAPI Router for Smart Visa Route.
Exposes endpoints for all-country search, live visa categories, profile matching,
dynamic comparison of any countries, what-if simulations, and live cache management.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from visa.visa_models import (
    CountrySummary,
    CountryDetail,
    UserProfile,
    RecommendationResponse,
    ComparisonResponse,
    ComparisonItem,
    WhatIfSimulationRequest,
    WhatIfSimulationResponse,
    VisaCategoryEnum
)
from visa.visa_data_service import visa_data_service
from visa.visa_scoring import scoring_engine
from visa.visa_recommendation import recommendation_pipeline
from visa.visa_cache import visa_cache
from config.api_config import api_config
from src.utils.logging_config import logger

visa_router = APIRouter(prefix="/visa", tags=["Smart Visa Route"])


class ComparisonRequest(BaseModel):
    country_codes: List[str] = Field(..., min_length=2, max_length=5, description="List of 2 to 5 ISO country codes")
    purpose: str = Field(default="Work Visa", description="Visa category for comparison")
    user_budget: float = Field(default=2500.0)


@visa_router.get("/status")
async def get_visa_status():
    """Returns connectivity and cache status for Smart Visa Route."""
    return {
        "success": True,
        "config": api_config.get_public_config(),
        "cache": visa_cache.get_status(),
        "timestamp": datetime.now().strftime("%d %B %Y, %H:%M"),
        "disclaimer": (
            "Visa and immigration information can change. This application provides decision-support information "
            "only and does not guarantee visa approval. Always verify current requirements with the relevant "
            "official government/immigration authority."
        )
    }


@visa_router.get("/categories", response_model=List[str])
async def get_supported_categories():
    """Returns all supported visa categories."""
    return [c.value for c in VisaCategoryEnum]


@visa_router.get("/countries", response_model=List[CountrySummary])
async def get_all_countries(
    search: Optional[str] = Query(None, description="Dynamic country name, code, or capital search"),
    region: Optional[str] = Query(None, description="Region filter: Europe, Americas, Asia-Pacific, Middle East, Africa"),
    purpose: Optional[str] = Query(None, description="Visa purpose filter"),
    safety_min: Optional[float] = Query(None, description="Minimum safety index (0-100)"),
    max_budget: Optional[float] = Query(None, description="Maximum monthly living budget (USD)"),
    language: Optional[str] = Query(None, description="Language spoken"),
    min_score: Optional[float] = Query(None, description="Minimum overall score")
):
    """
    Search and retrieve all supported countries dynamically from the live database.
    """
    try:
        countries = visa_data_service.get_all_countries(
            search=search,
            region=region,
            purpose=purpose,
            safety_min=safety_min,
            max_budget=max_budget,
            language=language,
            min_score=min_score
        )
        return countries
    except Exception as e:
        logger.error(f"Error fetching countries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to retrieve country dataset. Please try again.")


@visa_router.get("/country/{country_code}", response_model=CountryDetail)
async def get_country_detail(country_code: str):
    """
    Retrieves deep visa information across all categories for any country.
    """
    detail = visa_data_service.get_country_detail(country_code)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"Country '{country_code}' not found in live database. Please verify name or code."
        )
    return detail


@visa_router.post("/recommend", response_model=RecommendationResponse)
async def recommend_best_countries(profile: UserProfile):
    """
    Smart Visa Route matching pipeline:
    Evaluates applicant profile against ALL supported countries, calculates Smart Scores,
    and returns ranked Top 10 destinations with Top 3 gold/silver/bronze spotlight recommendations.
    """
    try:
        response = recommendation_pipeline.evaluate_profile(profile)
        return response
    except Exception as e:
        logger.error(f"Error evaluating visa profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate visa recommendations: {str(e)}")


@visa_router.post("/compare", response_model=ComparisonResponse)
async def compare_countries(request: ComparisonRequest):
    """
    Side-by-side comparison of ANY 2 to 5 countries selected by the user.
    """
    comparison_items: List[ComparisonItem] = []

    # Mock baseline profile for comparative score
    dummy_profile = UserProfile(
        current_country="Applicant",
        purpose=request.purpose,
        monthly_budget_usd=request.user_budget
    )

    for code in request.country_codes:
        detail = visa_data_service.get_country_detail(code)
        if not detail:
            continue

        breakdown = scoring_engine.calculate_score(dummy_profile, detail)
        visa_for_purpose = detail.visas.get(request.purpose)

        item = ComparisonItem(
            country_code=detail.code,
            country_name=detail.name,
            flag_emoji=detail.flag_emoji,
            region=detail.region,
            safety_index=detail.safety_index,
            cost_of_living_index=detail.cost_of_living_index,
            avg_annual_salary_usd=detail.avg_annual_salary_usd,
            quality_of_life_index=detail.quality_of_life_index,
            visa_details_for_purpose=visa_for_purpose,
            smart_score=breakdown.total_score,
            official_source=detail.official_source
        )
        comparison_items.append(item)

    if not comparison_items:
        raise HTTPException(status_code=400, detail="No valid country codes supplied for comparison.")

    return ComparisonResponse(
        purpose=request.purpose,
        countries=comparison_items,
        timestamp=datetime.now().strftime("%d %B %Y, %H:%M"),
        disclaimer=(
            "Visa and immigration information can change. This application provides decision-support information "
            "only and does not guarantee visa approval. Always verify current requirements with the relevant "
            "official government/immigration authority."
        )
    )


@visa_router.post("/simulate", response_model=WhatIfSimulationResponse)
async def simulate_what_if(request: WhatIfSimulationRequest):
    """
    What-If Simulator: dynamic recalculation of scores based on simulated parameter shifts.
    """
    try:
        return recommendation_pipeline.simulate_what_if(request)
    except Exception as e:
        logger.error(f"Error during what-if simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


@visa_router.post("/cache/refresh")
async def refresh_visa_cache():
    """
    Forces a cache invalidation and updates live timestamps from official sources.
    """
    try:
        result = visa_data_service.refresh_live_catalog()
        return result
    except Exception as e:
        logger.error(f"Error refreshing visa cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh live cache.")
