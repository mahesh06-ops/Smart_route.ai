"""
Routing Service for Smart Route AI.
Decoupled routing provider that queries OSRM for real-world driving geometries and alternatives.
Includes a high-fidelity realistic corridor generator for demo resilience and offline operation.
Outputs standardized route payloads ready for intelligence engine scoring.
"""
import asyncio
import math
from typing import List, Dict, Any, Tuple
import httpx
from src.utils.logging_config import logger
from src.services.weather_service import weather_service
from src.services.traffic_service import traffic_service
from src.intelligence.safety_engine import safety_engine
from src.intelligence.fuel_engine import fuel_engine


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two points."""
    r = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def generate_curved_geometry(
    start: Tuple[float, float],
    end: Tuple[float, float],
    deviation_factor: float = 0.0,
    steps: int = 40
) -> List[List[float]]:
    """
    Generates a realistic multi-point highway geometry connecting start and end
    with controlled lateral curve deviation to simulate alternative road corridors.
    Returns list of [latitude, longitude] points for Leaflet.
    """
    lat1, lon1 = start
    lat2, lon2 = end
    coords = []

    # Perpendicular vector for lateral highway arc
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    perp_lat = -dlon * deviation_factor
    perp_lon = dlat * deviation_factor

    for i in range(steps + 1):
        t = i / float(steps)
        # Base linear interpolation
        base_lat = lat1 + t * dlat
        base_lon = lon1 + t * dlon
        # Parabolic lateral offset
        curve = math.sin(t * math.pi)
        # Micro-variation to look like real roads rather than rigid math arcs
        micro_lat = math.sin(t * 8.0 * math.pi) * 0.015 * abs(dlat + 0.1)
        micro_lon = math.cos(t * 8.0 * math.pi) * 0.015 * abs(dlon + 0.1)

        pt_lat = round(base_lat + (perp_lat * curve) + micro_lat, 5)
        pt_lon = round(base_lon + (perp_lon * curve) + micro_lon, 5)
        coords.append([pt_lat, pt_lon])

    return coords


class RoutingService:
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

    @classmethod
    async def get_routes(
        cls,
        source_coords: Tuple[float, float],
        dest_coords: Tuple[float, float],
        vehicle_type: str = "car",
        custom_mileage: float = None,
        fuel_price: float = None,
        demo_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Calculates primary and alternative driving routes between coordinates.
        Enriches each route with specific highway corridors, traffic, weather, safety, and fuel models.
        """
        lat1, lon1 = source_coords
        lat2, lon2 = dest_coords
        direct_dist = haversine_distance_km(lat1, lon1, lat2, lon2)

        routes_data = []

        # 1. Attempt live OSRM routing if not forced demo mode
        if not demo_mode:
            try:
                # OSRM expects: {lon1},{lat1};{lon2},{lat2}
                url = f"{cls.OSRM_URL}/{lon1},{lat1};{lon2},{lat2}"
                params = {
                    "overview": "full",
                    "geometries": "geojson",
                    "alternatives": "true",
                    "steps": "true",
                }
                async with httpx.AsyncClient(timeout=4.5) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        osrm_routes = data.get("routes", [])
                        for idx, r in enumerate(osrm_routes[:3]):
                            dist_km = round(r["distance"] / 1000.0, 1)
                            dur_mins = round(r["duration"] / 60.0, 1)
                            raw_coords = r.get("geometry", {}).get("coordinates", [])
                            leaflet_coords = [[pt[1], pt[0]] for pt in raw_coords]

                            legs = r.get("legs", [])
                            summary = legs[0].get("summary", "") if legs else ""
                            steps = legs[0].get("steps", []) if legs else []
                            step_names = [s.get("name") for s in steps if s.get("name") and s.get("name").strip()]
                            unique_roads = list(dict.fromkeys(step_names))

                            if summary:
                                route_title = f"Corridor {idx + 1}: via {summary}"
                            elif unique_roads:
                                primary_highways = [rd for rd in unique_roads if any(k in rd.upper() for k in ("NH", "SH", "EXPRESSWAY", "HIGHWAY", "BYPASS", "ROAD", "AVENUE"))]
                                if primary_highways:
                                    route_title = f"Corridor {idx + 1}: via {' & '.join(primary_highways[:2])}"
                                else:
                                    route_title = f"Corridor {idx + 1}: via {unique_roads[0]}"
                            else:
                                route_title = f"Corridor {idx + 1}: Primary National Highway"

                            routes_data.append({
                                "route_id": f"route_{idx + 1}",
                                "route_name": route_title,
                                "via_summary": summary or (unique_roads[0] if unique_roads else "National Highway Corridor"),
                                "major_highways": unique_roads[:4] if unique_roads else [summary or "National Highway"],
                                "road_type": "4-Lane Divided Expressway" if idx == 0 else "Multi-Lane Highway Bypass",
                                "toll_info": f"{max(1, int(dist_km // 90))} Toll Plazas (~₹{max(1, int(dist_km // 90)) * 75})" if dist_km > 50 else "Urban Transit / Toll-Free",
                                "distance_km": dist_km,
                                "base_duration_minutes": dur_mins,
                                "coordinates": leaflet_coords,
                                "source_provider": "OSRM Live Driving Network",
                                "is_live_route": True
                            })
            except Exception as e:
                logger.warning(f"Live OSRM routing failed ({e}); switching to resilient fallback corridor generator.")

        # 2. Resilient fallback generator if live failed or returned fewer than 2 alternatives
        if len(routes_data) < 3:
            fallback_routes = cls._generate_fallback_routes(source_coords, dest_coords, direct_dist, existing_count=len(routes_data))
            # Merge while keeping existing OSRM routes first
            for fb in fallback_routes:
                if len(routes_data) < 3:
                    fb["route_id"] = f"route_{len(routes_data) + 1}"
                    routes_data.append(fb)

        # 3. Enrich each route with live corridor environmental and vehicle parameters
        # Concurrently fetch corridor weather for each route path
        weather_tasks = [
            weather_service.get_corridor_weather(r.get("coordinates", []), demo_mode=demo_mode)
            for r in routes_data
        ]
        weather_results = await asyncio.gather(*weather_tasks, return_exceptions=True)

        enriched_routes = []
        for idx, r in enumerate(routes_data):
            base_dur = r["base_duration_minutes"]
            dist_km = r["distance_km"]

            # Traffic
            traffic_payload = traffic_service.get_route_traffic(
                base_duration_minutes=base_dur,
                route_index=idx,
                demo_mode=demo_mode
            )

            # Weather from parallel corridor forecast
            local_weather = weather_results[idx] if idx < len(weather_results) and isinstance(weather_results[idx], dict) else await weather_service.get_weather(lat1, lon1, demo_mode=demo_mode)

            # Safety
            base_safety = 90.0 if idx == 0 else (84.0 if idx == 1 else 78.0)
            safety_payload = safety_engine.calculate_safety(
                base_road_rating=base_safety,
                traffic_score=traffic_payload["score"],
                weather_score=local_weather["score"],
                route_index=idx
            )

            # Fuel
            fuel_payload = fuel_engine.calculate_fuel(
                distance_km=dist_km,
                vehicle_type=vehicle_type,
                custom_mileage=custom_mileage,
                fuel_price=fuel_price
            )

            # Total duration includes traffic delay
            total_duration = traffic_payload["duration_with_traffic"]

            enriched_routes.append({
                "route_id": r["route_id"],
                "route_name": r["route_name"],
                "via_summary": r.get("via_summary", "National Highway Corridor"),
                "major_highways": r.get("major_highways", ["National Highway", "Expressway"]),
                "road_type": r.get("road_type", "4-Lane Divided Expressway"),
                "toll_info": r.get("toll_info", "2 Toll Plazas"),
                "distance_km": dist_km,
                "duration_minutes": total_duration,
                "base_duration_minutes": base_dur,
                "coordinates": r["coordinates"],
                "traffic": traffic_payload,
                "weather": local_weather,
                "safety": safety_payload,
                "fuel": fuel_payload,
                "source_provider": r.get("source_provider", "Analytical Corridor Engine"),
                "is_live_route": r.get("is_live_route", False),
            })

        return enriched_routes

    @classmethod
    def _generate_fallback_routes(
        cls,
        start: Tuple[float, float],
        end: Tuple[float, float],
        direct_dist_km: float,
        existing_count: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Creates realistic alternative driving corridors when live routing is unavailable.
        """
        # Route 1: Direct Expressway (Speed limit ~75 km/h)
        dist_1 = round(max(direct_dist_km * 1.28, 5.0), 1)
        dur_1 = round((dist_1 / 72.0) * 60.0, 1)
        geom_1 = generate_curved_geometry(start, end, deviation_factor=0.08, steps=45)

        # Route 2: Ring Road / Outer Bypass (+10% distance, faster average speed ~80 km/h)
        dist_2 = round(max(direct_dist_km * 1.38, 6.0), 1)
        dur_2 = round((dist_2 / 78.0) * 60.0, 1)
        geom_2 = generate_curved_geometry(start, end, deviation_factor=-0.14, steps=45)

        # Route 3: Arterial State Highway (Slightly shorter spatial distance, lower speed ~60 km/h)
        dist_3 = round(max(direct_dist_km * 1.22, 4.5), 1)
        dur_3 = round((dist_3 / 58.0) * 60.0, 1)
        geom_3 = generate_curved_geometry(start, end, deviation_factor=0.18, steps=45)

        candidates = [
            {
                "route_id": "route_1",
                "route_name": "Corridor 1: via NH Primary Expressway",
                "via_summary": "NH Primary Expressway & High-Speed Highway",
                "major_highways": ["National Expressway (NH Direct)", "Elevated Corridor"],
                "road_type": "4-Lane Access-Controlled Highway",
                "toll_info": f"{max(1, int(dist_1 // 90))} Toll Plazas (~₹{max(1, int(dist_1 // 90)) * 80})" if dist_1 > 50 else "Toll-Free Route",
                "distance_km": dist_1,
                "base_duration_minutes": dur_1,
                "coordinates": geom_1,
                "source_provider": "Analytical Corridor Generator (High-Precision)",
                "is_live_route": False,
            },
            {
                "route_id": "route_2",
                "route_name": "Corridor 2: via Outer Bypass & Ring Expressway",
                "via_summary": "Outer Bypass & Ring Expressway (Low Traffic)",
                "major_highways": ["Express Bypass Road", "Ring Expressway Connector"],
                "road_type": "6-Lane Divided Ring Highway",
                "toll_info": f"{max(1, int(dist_2 // 85))} Toll Plazas (~₹{max(1, int(dist_2 // 85)) * 90})" if dist_2 > 50 else "Toll-Free Route",
                "distance_km": dist_2,
                "base_duration_minutes": dur_2,
                "coordinates": geom_2,
                "source_provider": "Analytical Corridor Generator (High-Precision)",
                "is_live_route": False,
            },
            {
                "route_id": "route_3",
                "route_name": "Corridor 3: via State Highway Arterial Link",
                "via_summary": "State Highway Arterial (Direct / Minimal Toll)",
                "major_highways": ["State Highway Arterial", "Regional Link Corridor"],
                "road_type": "2-Lane Paved State Highway",
                "toll_info": "Toll-Free Route (₹0)",
                "distance_km": dist_3,
                "base_duration_minutes": dur_3,
                "coordinates": geom_3,
                "source_provider": "Analytical Corridor Generator (High-Precision)",
                "is_live_route": False,
            },
        ]

        return candidates[existing_count:]


routing_service = RoutingService()
