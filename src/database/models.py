"""
Data models representing database entities.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HistoryEntry:
    id: Optional[int]
    timestamp: str
    source: str
    destination: str
    source_coords: str
    destination_coords: str
    vehicle_type: str
    preference: str
    emergency_mode: bool
    recommended_route_id: str
    distance_km: float
    duration_minutes: float
    smart_score: float
    fuel_liters: float
    fuel_cost: float
    summary: str
    full_result_json: Optional[str] = None
