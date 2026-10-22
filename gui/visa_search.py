"""
GUI Search Module for Smart Visa Route.
Handles search indexing, fuzzy query matching, and multi-parameter filtering.
"""
from typing import List, Dict, Any, Optional
from visa.visa_data_service import visa_data_service


class VisaSearchGUI:
    @staticmethod
    def search_destinations(
        query: str = "",
        region: str = "All",
        purpose: str = "All",
        safety_min: float = 0.0,
        max_budget: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        countries = visa_data_service.get_all_countries(
            search=query if query else None,
            region=region if region != "All" else None,
            purpose=purpose if purpose != "All" else None,
            safety_min=safety_min if safety_min > 0 else None,
            max_budget=max_budget
        )
        return [c.model_dump() for c in countries]


visa_search_gui = VisaSearchGUI()
