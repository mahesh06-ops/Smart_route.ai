"""
Pydantic Request Schemas for Smart Route AI API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    source: str = Field(..., min_length=2, max_length=120, description="Source location or city name")
    destination: str = Field(..., min_length=2, max_length=120, description="Destination location or city name")
    vehicle_type: str = Field("car", description="Vehicle type: car, bike, suv, custom")
    preference: str = Field("balanced", description="Preference: balanced, fastest, shortest, safest, fuel_efficient")
    emergency_mode: bool = Field(False, description="Emergency prioritization mode")
    custom_mileage: Optional[float] = Field(None, gt=0, description="Custom vehicle mileage in km/L")
    fuel_price: Optional[float] = Field(None, gt=0, description="Fuel price per liter")
    demo_mode: bool = Field(False, description="Run in simulated demo mode")


class GeocodeRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=120, description="Location search query")
