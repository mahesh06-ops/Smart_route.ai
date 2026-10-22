"""
GUI Comparison Module for Smart Visa Route.
Generates side-by-side comparison matrices across any arbitrary set of countries.
"""
from typing import List, Dict, Any
from visa.visa_models import UserProfile
from visa.visa_data_service import visa_data_service
from visa.visa_scoring import scoring_engine


class VisaComparisonGUI:
    @staticmethod
    def compare_destinations(country_codes: List[str], purpose: str = "Work Visa") -> Dict[str, Any]:
        dummy_profile = UserProfile(
            current_country="Applicant",
            purpose=purpose,
            monthly_budget_usd=2500.0
        )
        items = []
        for code in country_codes:
            detail = visa_data_service.get_country_detail(code)
            if not detail:
                continue
            breakdown = scoring_engine.calculate_score(dummy_profile, detail)
            items.append({
                "country_code": detail.code,
                "country_name": detail.name,
                "flag_emoji": detail.flag_emoji,
                "region": detail.region,
                "safety_index": detail.safety_index,
                "cost_of_living_index": detail.cost_of_living_index,
                "avg_annual_salary_usd": detail.avg_annual_salary_usd,
                "quality_of_life_index": detail.quality_of_life_index,
                "smart_score": breakdown.total_score,
                "visa_info": detail.visas.get(purpose).model_dump() if detail.visas.get(purpose) else None,
                "official_source": detail.official_source.model_dump()
            })
        return {
            "purpose": purpose,
            "compared_countries": items
        }


visa_comparison_gui = VisaComparisonGUI()
