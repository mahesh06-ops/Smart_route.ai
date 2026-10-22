"""Visa package initialization."""
from visa.visa_models import (
    CountrySummary,
    CountryDetail,
    VisaDetail,
    UserProfile,
    SmartScoreBreakdown,
    RecommendationItem,
    RecommendationResponse,
    ComparisonResponse,
    WhatIfSimulationRequest,
    WhatIfSimulationResponse,
    VisaCategoryEnum,
    PriorityEnum
)
from visa.visa_data_service import visa_data_service, VisaDataService
from visa.visa_scoring import scoring_engine, VisaScoringEngine
from visa.visa_recommendation import recommendation_pipeline, VisaRecommendationPipeline
from visa.visa_cache import visa_cache, VisaCacheManager
from visa.visa_api import visa_router

__all__ = [
    "CountrySummary",
    "CountryDetail",
    "VisaDetail",
    "UserProfile",
    "SmartScoreBreakdown",
    "RecommendationItem",
    "RecommendationResponse",
    "ComparisonResponse",
    "WhatIfSimulationRequest",
    "WhatIfSimulationResponse",
    "VisaCategoryEnum",
    "PriorityEnum",
    "visa_data_service",
    "VisaDataService",
    "scoring_engine",
    "VisaScoringEngine",
    "recommendation_pipeline",
    "VisaRecommendationPipeline",
    "visa_cache",
    "VisaCacheManager",
    "visa_router"
]
