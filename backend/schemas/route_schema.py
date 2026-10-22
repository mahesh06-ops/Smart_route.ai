"""
Pydantic Response Schemas for Smart Route AI.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class LocationCoord(BaseModel):
    lat: float
    lon: float
    display_name: str


class ScoreBreakdownItem(BaseModel):
    score: float
    max: float
    normalized_pct: float


class RouteItem(BaseModel):
    route_id: str
    route_name: str
    distance_km: float
    duration_minutes: float
    base_duration_minutes: float
    coordinates: List[List[float]]
    traffic: Dict[str, Any]
    weather: Dict[str, Any]
    safety: Dict[str, Any]
    fuel: Dict[str, Any]
    smart_score: float
    score_breakdown: Dict[str, Any]
    is_recommended: bool
    rank: int
    source_provider: str
    is_live_route: bool


class RouteCalculationResponse(BaseModel):
    success: bool
    source: LocationCoord
    destination: LocationCoord
    routes: List[RouteItem]
    recommended_route: RouteItem
    explanation: Dict[str, Any]
    applied_weights: Dict[str, float]
    history_id: Optional[int] = None
    demo_mode: bool
    emergency_mode: bool
