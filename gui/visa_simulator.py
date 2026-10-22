"""
GUI What-If Simulator Module for Smart Visa Route.
Executes real-time sensitivity analysis and score adjustments.
"""
from typing import Dict, Any
from visa.visa_models import WhatIfSimulationRequest
from visa.visa_recommendation import recommendation_pipeline


class VisaSimulatorGUI:
    @staticmethod
    def run_simulation(sim_request_dict: Dict[str, Any]) -> Dict[str, Any]:
        req = WhatIfSimulationRequest(**sim_request_dict)
        resp = recommendation_pipeline.simulate_what_if(req)
        return resp.model_dump()


visa_simulator_gui = VisaSimulatorGUI()
