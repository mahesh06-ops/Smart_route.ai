"""
GUI Controller for Smart Visa Route.
Acts as the central coordination layer for visa searches, recommendations, comparisons,
details, and what-if simulations.
"""
from typing import Dict, Any, List, Optional
from visa.visa_models import UserProfile, PriorityEnum, WhatIfSimulationRequest
from visa.visa_recommendation import recommendation_pipeline
from visa.visa_data_service import visa_data_service


class VisaRouteGUIController:
    """Provides high-level programmatic interface for GUI applications."""

    @staticmethod
    def get_supported_countries(search: Optional[str] = None, region: Optional[str] = None) -> List[Dict[str, Any]]:
        countries = visa_data_service.get_all_countries(search=search, region=region)
        return [c.model_dump() for c in countries]

    @staticmethod
    def find_best_countries(profile_dict: Dict[str, Any]) -> Dict[str, Any]:
        profile = UserProfile(**profile_dict)
        result = recommendation_pipeline.evaluate_profile(profile)
        return result.model_dump()

    @staticmethod
    def get_country_details(country_code_or_name: str) -> Optional[Dict[str, Any]]:
        detail = visa_data_service.get_country_detail(country_code_or_name)
        return detail.model_dump() if detail else None


visa_route_gui = VisaRouteGUIController()
