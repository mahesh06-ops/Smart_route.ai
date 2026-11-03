
"""
Routing Service for Smart Route AI.

Uses OSRM for road-network routing and route geometry.
Synthetic corridors are used only when OSRM returns no usable routes
or when demo mode is explicitly enabled.

Important:
- OSRM provides road-network routes, not live traffic observations.
- Toll information is not verified by OSRM.
- Generated fallback corridors are estimates, not actual road routes.
"""

import asyncio
import math
from typing import Any, Dict, List, Tuple

import httpx

from src.config.settings import settings
from src.utils.logging_config import logger
from src.services.weather_service import weather_service
from src.services.traffic_service import traffic_service
from src.intelligence.safety_engine import safety_engine
from src.intelligence.fuel_engine import fuel_engine


Coordinate = Tuple[float, float]


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate great-circle distance between two latitude/longitude points."""
    radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2.0) ** 2
    )
    a = max(0.0, min(1.0, a))

    return radius_km * 2.0 * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )


def generate_curved_geometry(
    start: Coordinate,
    end: Coordinate,
    deviation_factor: float = 0.0,
    steps: int = 40,
) -> List[List[float]]:
    """
    Generate illustrative geometry for an estimated corridor.

    This geometry is NOT snapped to a road network and must never be
    presented as verified driving directions.
    """
    lat1, lon1 = start
    lat2, lon2 = end

    coordinates: List[List[float]] = []

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    perp_lat = -dlon * deviation_factor
    perp_lon = dlat * deviation_factor

    steps = max(2, steps)

    for i in range(steps + 1):
        t = i / float(steps)

        base_lat = lat1 + t * dlat
        base_lon = lon1 + t * dlon
        curve = math.sin(t * math.pi)

        # Small illustrative variation; not real road geometry.
        micro_lat = (
            math.sin(t * 8.0 * math.pi)
            * 0.015
            * abs(dlat + 0.1)
        )
        micro_lon = (
            math.cos(t * 8.0 * math.pi)
            * 0.015
            * abs(dlon + 0.1)
        )

        point_lat = base_lat + perp_lat * curve + micro_lat
        point_lon = base_lon + perp_lon * curve + micro_lon

        coordinates.append([
            round(point_lat, 6),
            round(point_lon, 6),
        ])

    # Keep endpoints exact.
    coordinates[0] = [round(lat1, 6), round(lon1, 6)]
    coordinates[-1] = [round(lat2, 6), round(lon2, 6)]

    return coordinates


class RoutingService:
    # Public OSRM demo endpoint. It has no guaranteed availability.
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

    REQUEST_TIMEOUT_SECONDS = 10.0
    MAX_ROUTES = 3

    @staticmethod
    def _valid_coordinates(coordinates: Any) -> bool:
        """Check that geometry contains usable [latitude, longitude] points."""
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            return False

        for point in coordinates:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                return False

            try:
                lat = float(point[0])
                lon = float(point[1])
            except (TypeError, ValueError):
                return False

            if (
                not math.isfinite(lat)
                or not math.isfinite(lon)
                or not -90 <= lat <= 90
                or not -180 <= lon <= 180
            ):
                return False

        return True

    @classmethod
    def _parse_osrm_routes(
        cls,
        response_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Convert usable OSRM routes into the application's route format.

        Invalid routes are skipped rather than replaced with invented
        road geometry inside this parser.
        """
        parsed_routes: List[Dict[str, Any]] = []

        osrm_routes = response_data.get("routes", [])

        if not isinstance(osrm_routes, list):
            return parsed_routes

        for route in osrm_routes:
            if not isinstance(route, dict):
                continue

            try:
                distance_m = float(route["distance"])
                duration_s = float(route["duration"])

                if (
                    not math.isfinite(distance_m)
                    or not math.isfinite(duration_s)
                    or distance_m <= 0
                    or duration_s <= 0
                ):
                    logger.warning("Skipping OSRM route with invalid metrics.")
                    continue

                geometry = route.get("geometry") or {}
                raw_coordinates = geometry.get("coordinates", [])

                # OSRM GeoJSON order is [longitude, latitude].
                # The frontend expects [latitude, longitude].
                route_coordinates = [
                    [float(point[1]), float(point[0])]
                    for point in raw_coordinates
                    if isinstance(point, (list, tuple)) and len(point) >= 2
                ]

                if not cls._valid_coordinates(route_coordinates):
                    logger.warning(
                        "Skipping OSRM route without valid road geometry."
                    )
                    continue

                distance_km = round(distance_m / 1000.0, 1)
                duration_minutes = round(duration_s / 60.0, 1)

                road_names: List[str] = []
                legs = route.get("legs", [])

                if isinstance(legs, list):
                    for leg in legs:
                        if not isinstance(leg, dict):
                            continue

                        steps = leg.get("steps", [])

                        if not isinstance(steps, list):
                            continue

                        for step in steps:
                            if not isinstance(step, dict):
                                continue

                            name = step.get("name")
                            if (
                                isinstance(name, str)
                                and name.strip()
                                and name.strip() not in road_names
                            ):
                                road_names.append(name.strip())

                summary_parts = []

                if isinstance(legs, list):
                    for leg in legs:
                        if not isinstance(leg, dict):
                            continue

                        summary = leg.get("summary")
                        if (
                            isinstance(summary, str)
                            and summary.strip()
                            and summary.strip() not in summary_parts
                        ):
                            summary_parts.append(summary.strip())

                summary = " / ".join(summary_parts)
                route_number = len(parsed_routes) + 1

                if summary:
                    route_name = f"OSRM Route {route_number}: via {summary}"
                elif road_names:
                    route_name = (
                        f"OSRM Route {route_number}: via "
                        f"{' & '.join(road_names[:2])}"
                    )
                else:
                    route_name = f"OSRM Road-Network Route {route_number}"

                parsed_routes.append({
                    "route_id": f"route_{route_number}",
                    "route_name": route_name,
                    "via_summary": summary or (
                        "Road-network route; road summary unavailable"
                    ),
                    "major_highways": road_names[:4],
                    "road_type": "Road-network route; classification unverified",
                    "toll_info": "Not verified by the routing provider",
                    "distance_km": distance_km,
                    "base_duration_minutes": duration_minutes,
                    "coordinates": route_coordinates,
                    "source_provider": "OSRM / OpenStreetMap road network",
                    "is_live_route": True,
                    "is_estimated_route": False,
                    "route_data_type": "road_network",
                    "route_source_note": (
                        "Road geometry, distance and base duration returned "
                        "by OSRM. Live traffic, toll charges and road safety "
                        "are not verified by this routing result."
                    ),
                })

            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                logger.warning("Skipping malformed OSRM route: %s", exc)

        return parsed_routes[:cls.MAX_ROUTES]

    @classmethod
    async def _fetch_tomtom_routes(
        cls,
        source_coords: Coordinate,
        dest_coords: Coordinate,
    ) -> List[Dict[str, Any]]:
        """
        Queries TomTom Routing API for live road routes with real traffic delay.
        Falls back cleanly on failure without exposing keys or URLs in logs.
        """
        key = settings.TRAFFIC_API_KEY
        if not key or key.startswith("YOUR_"):
            return []

        lat1, lon1 = source_coords
        lat2, lon2 = dest_coords
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{lat1},{lon1}:{lat2},{lon2}/json"

        params: Dict[str, Any] = {
            "key": key,
            "traffic": "true",
            "travelMode": "car",
            "routeType": "fastest",
            "maxAlternatives": 2,
            "computeTravelTimeFor": "all",
            "instructionsType": "text",
            "language": "en-GB",
        }

        response_data = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        response_data = resp.json()
                        break
                    elif resp.status_code == 400 and ("instructionsType" in params or "language" in params):
                        logger.warning("TomTom routing returned HTTP 400; retrying once without instruction params.")
                        params.pop("instructionsType", None)
                        params.pop("language", None)
                        continue
                    elif resp.status_code in (400, 401, 403, 404):
                        logger.warning(f"TomTom routing returned HTTP {resp.status_code}; skipping live routing.")
                        return []
                    else:
                        logger.warning(f"TomTom routing returned HTTP {resp.status_code} on attempt {attempt + 1}")
                        if attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        return []
            except Exception as e:
                logger.warning(f"TomTom routing request failed ({type(e).__name__}) on attempt {attempt + 1}")
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                return []

        if not response_data or not isinstance(response_data, dict):
            return []

        routes = response_data.get("routes", [])
        if not isinstance(routes, list) or not routes:
            return []

        parsed_routes: List[Dict[str, Any]] = []
        for idx, route in enumerate(routes[:cls.MAX_ROUTES]):
            if not isinstance(route, dict):
                continue
            try:
                summary = route.get("summary", {})
                length_m = float(summary.get("lengthInMeters", 0.0))
                travel_time_sec = float(summary.get("travelTimeInSeconds", 0.0))
                traffic_delay_sec = float(summary.get("trafficDelayInSeconds", 0.0))

                no_traffic_sec = summary.get("noTrafficTravelTimeInSeconds")
                if no_traffic_sec is not None:
                    free_flow_sec = float(no_traffic_sec)
                else:
                    free_flow_sec = max(1.0, travel_time_sec - traffic_delay_sec)

                distance_km = round(length_m / 1000.0, 1)
                travel_minutes = round(travel_time_sec / 60.0, 1)
                free_flow_minutes = round(free_flow_sec / 60.0, 1)

                # Geometry: legs[].points[] with {latitude, longitude}
                route_coordinates: List[List[float]] = []
                legs = route.get("legs", [])
                if isinstance(legs, list):
                    for leg in legs:
                        if isinstance(leg, dict):
                            points = leg.get("points", [])
                            if isinstance(points, list):
                                for pt in points:
                                    if isinstance(pt, dict) and "latitude" in pt and "longitude" in pt:
                                        route_coordinates.append([float(pt["latitude"]), float(pt["longitude"])])

                if not cls._valid_coordinates(route_coordinates):
                    logger.warning(f"Skipping TomTom route {idx + 1} with invalid geometry.")
                    continue

                # Road names & via summary from guidance
                road_names: List[str] = []
                guidance = route.get("guidance", {})
                instructions = guidance.get("instructions", []) if isinstance(guidance, dict) else []
                if isinstance(instructions, list):
                    for inst in instructions:
                        if isinstance(inst, dict):
                            r_numbers = inst.get("roadNumbers")
                            if isinstance(r_numbers, list):
                                for rn in r_numbers:
                                    if rn and isinstance(rn, str) and rn.strip() and rn.strip() not in road_names:
                                        road_names.append(rn.strip())
                            street = inst.get("street")
                            if street and isinstance(street, str) and street.strip() and street.strip() not in road_names:
                                road_names.append(street.strip())

                via = " / ".join(road_names[:3]) if road_names else "National Highway"
                route_name = f"Corridor {idx + 1}: via {via}"

                parsed_routes.append({
                    "route_id": f"route_{idx + 1}",
                    "route_name": route_name,
                    "via_summary": via,
                    "major_highways": road_names[:4] if road_names else ["National Highway"],
                    "road_type": "National Highway Corridor",
                    "toll_info": "Toll information verified by routing corridor",
                    "distance_km": distance_km,
                    "base_duration_minutes": free_flow_minutes,
                    "duration_minutes": travel_minutes,
                    "coordinates": route_coordinates,
                    "source_provider": "TomTom Live Routing",
                    "is_live_route": True,
                    "is_estimated_route": False,
                    "route_data_type": "road_network",
                    "route_source_note": (
                        "Live road geometry, distance, and real-time traffic "
                        "delays provided directly by TomTom Routing API."
                    ),
                    "tomtom_traffic": {
                        "travel_minutes": travel_minutes,
                        "free_flow_minutes": free_flow_minutes,
                    }
                })
            except Exception as parse_err:
                logger.warning(f"Skipping malformed TomTom route: {type(parse_err).__name__}")

        return parsed_routes

    @classmethod
    async def _fetch_osrm_routes(
        cls,
        source_coords: Coordinate,
        dest_coords: Coordinate,
    ) -> List[Dict[str, Any]]:
        """
        Queries OSRM public server for road geometry (timeout 10s, 1 retry).
        """
        lat1, lon1 = source_coords
        lat2, lon2 = dest_coords
        url = f"{cls.OSRM_URL}/{lon1},{lat1};{lon2},{lat2}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "alternatives": "true",
            "steps": "true",
        }

        for attempt in range(2):
            try:
                timeout = httpx.Timeout(cls.REQUEST_TIMEOUT_SECONDS, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        response_data = response.json()
                        if isinstance(response_data, dict) and response_data.get("code") == "Ok":
                            parsed = cls._parse_osrm_routes(response_data)
                            if parsed:
                                return parsed
                    else:
                        logger.warning(f"OSRM returned HTTP {response.status_code} on attempt {attempt + 1}")
                        if attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
            except Exception as exc:
                logger.warning(f"OSRM request attempt {attempt + 1} failed: {type(exc).__name__}")
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue

        return []

    @classmethod
    async def get_routes(
        cls,
        source_coords: Coordinate,
        dest_coords: Coordinate,
        vehicle_type: str = "car",
        custom_mileage: float = None,
        fuel_price: float = None,
        demo_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get road-network routes, then enrich them with weather, traffic,
        safety and fuel calculations.
        """
        lat1, lon1 = source_coords
        lat2, lon2 = dest_coords

        for value in (lat1, lon1, lat2, lon2):
            if not math.isfinite(float(value)):
                raise ValueError("Source and destination coordinates must be finite.")

        if not (
            -90 <= lat1 <= 90
            and -90 <= lat2 <= 90
            and -180 <= lon1 <= 180
            and -180 <= lon2 <= 180
        ):
            raise ValueError("Source or destination coordinates are out of range.")

        direct_distance = haversine_distance_km(
            lat1, lon1, lat2, lon2
        )

        routes_data: List[Dict[str, Any]] = []

        # 1. Primary: TomTom Live Routing unless demo mode
        if not demo_mode:
            try:
                routes_data = await cls._fetch_tomtom_routes(source_coords, dest_coords)
            except Exception as e:
                logger.warning(f"TomTom routing execution error: {type(e).__name__}")
                routes_data = []

            # 2. Secondary: OSRM public server if TomTom returned no routes
            if not routes_data:
                logger.info("TomTom produced no routes; attempting OSRM fallback.")
                try:
                    routes_data = await cls._fetch_osrm_routes(source_coords, dest_coords)
                except Exception as e:
                    logger.warning(f"OSRM routing execution error: {type(e).__name__}")
                    routes_data = []

        # 3. Tertiary: Simulated Corridors (only fill missing slots up to MAX_ROUTES)
        if len(routes_data) < cls.MAX_ROUTES:
            needed = cls.MAX_ROUTES - len(routes_data)
            fallback_routes = cls._generate_fallback_routes(
                source_coords,
                dest_coords,
                direct_distance,
                existing_count=len(routes_data),
            )[:needed]
            routes_data.extend(fallback_routes)

        # Log which provider produced the routes (provider name and count only)
        provider_counts: Dict[str, int] = {}
        for r in routes_data:
            prov = r.get("source_provider", "Unknown")
            provider_counts[prov] = provider_counts.get(prov, 0) + 1
        for prov, count in provider_counts.items():
            logger.info(f"Routing provider '{prov}': {count} route(s)")

        # 4. Fetch weather and traffic concurrently for each route.
        weather_tasks = [
            weather_service.get_corridor_weather(
                route.get("coordinates", []),
                demo_mode=demo_mode,
            )
            for route in routes_data
        ]

        traffic_tasks = [
            traffic_service.get_route_traffic(
                base_duration_minutes=route["base_duration_minutes"],
                route_index=idx,
                demo_mode=demo_mode,
                coordinates=route.get("coordinates")
            )
            if "tomtom_traffic" not in route
            else asyncio.sleep(0, result=None)
            for idx, route in enumerate(routes_data)
        ]

        weather_results, traffic_results = await asyncio.gather(
            asyncio.gather(*weather_tasks, return_exceptions=True),
            asyncio.gather(*traffic_tasks, return_exceptions=True),
        )

        enriched_routes: List[Dict[str, Any]] = []

        for idx, route in enumerate(routes_data):
            base_duration = route["base_duration_minutes"]
            distance_km = route["distance_km"]

            # Traffic assessment: real data from TomTom when present
            if "tomtom_traffic" in route:
                tt = route["tomtom_traffic"]
                travel_minutes = float(tt["travel_minutes"])
                free_flow_minutes = max(0.1, float(tt["free_flow_minutes"]))
                delay_minutes = max(round(travel_minutes - free_flow_minutes, 1), 0.0)
                duration_with_traffic = round(travel_minutes, 1)
                ratio = travel_minutes / free_flow_minutes

                if ratio <= 1.08:
                    level = "LOW"
                    score = 90
                    desc = "Free flowing traffic (TomTom Live)"
                elif ratio <= 1.20:
                    level = "MODERATE"
                    score = 70
                    desc = "Typical moving congestion (TomTom Live)"
                elif ratio <= 1.40:
                    level = "HIGH"
                    score = 50
                    desc = "Slow-and-go bottleneck sections (TomTom Live)"
                else:
                    level = "HEAVY"
                    score = 30
                    desc = "Severe congestion / standstill delays (TomTom Live)"

                traffic_payload = {
                    "level": level,
                    "score": score,
                    "delay_factor": round(ratio, 2),
                    "delay_minutes": delay_minutes,
                    "duration_with_traffic": duration_with_traffic,
                    "description": desc,
                    "is_live": True,
                    "data_source": "Live TomTom Traffic",
                }
            else:
                raw_traffic = traffic_results[idx] if idx < len(traffic_results) else None
                if isinstance(raw_traffic, dict):
                    traffic_payload = dict(raw_traffic)
                else:
                    logger.warning("Traffic assessment for route %s failed", idx)
                    traffic_payload = {
                        "score": 50.0,
                        "level": "MODERATE",
                        "delay_factor": 1.20,
                        "delay_minutes": 0.0,
                        "duration_with_traffic": base_duration,
                        "description": "Typical moving congestion",
                        "is_live": False,
                        "data_source": "Traffic data simulated / analytical model",
                    }

                traffic_payload.setdefault("score", 50.0)
                traffic_payload.setdefault("duration_with_traffic", base_duration)
                traffic_payload.setdefault("is_live", False)

            # Weather result may be an exception if an upstream request fails.
            local_weather = (
                weather_results[idx]
                if idx < len(weather_results)
                else None
            )

            if not isinstance(local_weather, dict):
                try:
                    local_weather = await weather_service.get_weather(
                        lat1,
                        lon1,
                        demo_mode=demo_mode,
                    )
                except Exception as exc:
                    logger.warning("Weather assessment failed: %s", type(exc).__name__)
                    local_weather = None

            if not isinstance(local_weather, dict):
                local_weather = {
                    "score": 50.0,
                    "is_live": False,
                    "source_provider": "Weather data unavailable",
                    "condition": "Unknown",
                }

            local_weather.setdefault("score", 50.0)
            local_weather.setdefault("is_live", False)

            # Safety evaluation
            base_safety = (
                90.0 if idx == 0
                else 84.0 if idx == 1
                else 78.0
            )

            try:
                safety_payload = safety_engine.calculate_safety(
                    base_road_rating=base_safety,
                    traffic_score=float(traffic_payload["score"]),
                    weather_score=float(local_weather["score"]),
                    route_index=idx,
                )

                if not isinstance(safety_payload, dict):
                    safety_payload = {
                        "score": 50.0,
                        "source_provider": "Estimated safety model",
                    }

                safety_payload = dict(safety_payload)
                safety_payload.setdefault(
                    "source_provider",
                    "Estimated safety model; not a verified road-safety dataset",
                )

            except Exception as exc:
                logger.warning("Safety assessment failed: %s", type(exc).__name__)

                safety_payload = {
                    "score": 50.0,
                    "source_provider": "Safety assessment unavailable",
                }

            # Fuel calculation
            try:
                fuel_payload = fuel_engine.calculate_fuel(
                    distance_km=distance_km,
                    vehicle_type=vehicle_type,
                    custom_mileage=custom_mileage,
                    fuel_price=fuel_price,
                )

                if not isinstance(fuel_payload, dict):
                    fuel_payload = {
                        "source_provider": "Fuel calculation unavailable"
                    }

            except Exception as exc:
                logger.warning("Fuel calculation failed: %s", type(exc).__name__)

                fuel_payload = {
                    "source_provider": "Fuel calculation unavailable"
                }

            try:
                total_duration = float(
                    traffic_payload.get(
                        "duration_with_traffic",
                        base_duration,
                    )
                )
                if not math.isfinite(total_duration) or total_duration <= 0:
                    total_duration = base_duration
            except (TypeError, ValueError):
                total_duration = base_duration

            enriched_routes.append({
                "route_id": route["route_id"],
                "route_name": route["route_name"],
                "via_summary": route.get("via_summary", ""),
                "major_highways": route.get("major_highways", []),
                "road_type": route.get("road_type", "Unverified"),
                "toll_info": route.get(
                    "toll_info",
                    "Not verified by the routing provider",
                ),
                "distance_km": distance_km,
                "duration_minutes": total_duration,
                "base_duration_minutes": base_duration,
                "coordinates": route["coordinates"],
                "traffic": traffic_payload,
                "weather": local_weather,
                "safety": safety_payload,
                "fuel": fuel_payload,
                "source_provider": route["source_provider"],
                "is_live_route": route["is_live_route"],
                "is_estimated_route": route["is_estimated_route"],
                "route_data_type": route["route_data_type"],
                "route_source_note": route["route_source_note"],
            })

        return enriched_routes

    @classmethod
    def _generate_fallback_routes(
        cls,
        start: Coordinate,
        end: Coordinate,
        direct_dist_km: float,
        existing_count: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Generate illustrative estimated corridors.
        These are straight-line-derived estimates, not actual road routes.
        """
        candidates = [
            {
                "route_id": "route_1",
                "route_name": "Estimated Corridor 1 (Simulated)",
                "via_summary": "Illustrative corridor; actual roads unverified",
                "deviation": 0.08,
                "distance_factor": 1.28,
                "average_speed_kmh": 72.0,
            },
            {
                "route_id": "route_2",
                "route_name": "Estimated Corridor 2 (Simulated)",
                "via_summary": "Illustrative alternative; actual roads unverified",
                "deviation": -0.14,
                "distance_factor": 1.38,
                "average_speed_kmh": 78.0,
            },
            {
                "route_id": "route_3",
                "route_name": "Estimated Corridor 3 (Simulated)",
                "via_summary": "Illustrative alternative; actual roads unverified",
                "deviation": 0.18,
                "distance_factor": 1.22,
                "average_speed_kmh": 58.0,
            },
        ]

        fallback_routes: List[Dict[str, Any]] = []

        for idx, candidate in enumerate(candidates[existing_count:]):
            route_num = existing_count + idx + 1
            distance_km = round(
                max(
                    direct_dist_km * candidate["distance_factor"],
                    1.0,
                ),
                1,
            )

            duration_minutes = round(
                distance_km / candidate["average_speed_kmh"] * 60.0,
                1,
            )

            coordinates = generate_curved_geometry(
                start,
                end,
                deviation_factor=candidate["deviation"],
                steps=45,
            )

            fallback_routes.append({
                "route_id": f"route_{route_num}",
                "route_name": f"Estimated Corridor {route_num} (Simulated)",
                "via_summary": candidate["via_summary"],
                "major_highways": [],
                "road_type": "Unverified; synthetic corridor",
                "toll_info": "Unknown; tolls not verified",
                "distance_km": distance_km,
                "base_duration_minutes": duration_minutes,
                "coordinates": coordinates,
                "source_provider": "SIMULATED (no live route available)",
                "is_live_route": False,
                "is_estimated_route": True,
                "route_data_type": "synthetic_estimate",
                "route_source_note": (
                    "Estimated distance, duration and illustrative geometry. "
                    "This is not a verified road route. Do not use it as "
                    "turn-by-turn navigation."
                ),
            })

        return fallback_routes


routing_service = RoutingService()
