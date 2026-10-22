"""
GUI Details Module for Smart Visa Route.
Fetches and formats granular visa categories, requirements, processing times,
and official government immigration portal credentials.
"""
from typing import Optional, Dict, Any
from visa.visa_data_service import visa_data_service


class VisaDetailsGUI:
    @staticmethod
    def get_details_view(country_code: str) -> Optional[Dict[str, Any]]:
        country = visa_data_service.get_country_detail(country_code)
        if not country:
            return None
        return country.model_dump()


visa_details_gui = VisaDetailsGUI()
