"""
Route Calculation and Recommendation API endpoints.
Main pipeline connecting geocoding, routing, intelligence engines, scoring,
AI explanation, and history logging.
"""
from fastapi import APIRouter, HTTPException
from backend.schemas.request_schema import RouteRequest, GeocodeRequest
from src.services.geocoding_service import geocoding_service
from src.services.routing_service import routing_service
from src.intelligence.route_scoring import route_scoring_engine
from src.intelligence.explanation_engine import explanation_engine
from src.database.history_repository import history_repo
from src.utils.validation import validate_route_request
from src.utils.logging_config import logger

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.post("/geocode")
async def geocode_query(req: GeocodeRequest):
    """Geocodes a place name to coordinates."""
    res = await geocoding_service.geocode(req.query)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Location not found."))
    return res


@router.post("/calculate")
async def calculate_smart_route(req: RouteRequest):
    """
    Main Multi-Factor Route Optimization Pipeline.
    1. Geocodes locations
    2. Retrieves real/simulated routes & alternatives
    3. Evaluates traffic, weather, safety, and fuel
    4. Computes multi-factor Smart Scores
    5. Generates AI explanation
    6. Persists to history
    """
    # 1. Validate inputs
    valid, err_msg = validate_route_request(req.source, req.destination)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg)

    # 2. Geocode Source
    src_res = await geocoding_service.geocode(req.source)
    if not src_res.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Source '{req.source}' could not be located. Please specify a recognized city or region."
        )

    # 3. Geocode Destination
    dest_res = await geocoding_service.geocode(req.destination)
    if not dest_res.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Destination '{req.destination}' could not be located. Please specify a recognized city or region."
        )

    src_coords = (src_res["lat"], src_res["lon"])
    dest_coords = (dest_res["lat"], dest_res["lon"])

    # 4. Routing & Factor Enrichment
    try:
        raw_routes = await routing_service.get_routes(
            source_coords=src_coords,
            dest_coords=dest_coords,
            vehicle_type=req.vehicle_type,
            custom_mileage=req.custom_mileage,
            fuel_price=req.fuel_price,
            demo_mode=req.demo_mode
        )
    except Exception as e:
        logger.error(f"Routing calculation failure: {e}")
        raise HTTPException(status_code=500, detail="Routing service is temporarily unavailable. Please try again.")

    if not raw_routes:
        raise HTTPException(status_code=404, detail="No viable driving routes could be found between these coordinates.")

    # 5. Multi-Factor Intelligent Scoring
    scored_routes = route_scoring_engine.score_routes(
        routes=raw_routes,
        preference=req.preference,
        emergency_mode=req.emergency_mode
    )

    recommended_route = scored_routes[0]

    # 6. Dynamic AI Explanation
    explanation = explanation_engine.generate_explanation(
        recommended_route=recommended_route,
        all_routes=scored_routes,
        preference=req.preference,
        emergency_mode=req.emergency_mode
    )

    # 7. Persist to SQLite History
    history_id = None
    try:
        history_entry = {
            "source": src_res.get("display_name", req.source),
            "destination": dest_res.get("display_name", req.destination),
            "source_coords": f"{src_coords[0]},{src_coords[1]}",
            "destination_coords": f"{dest_coords[0]},{dest_coords[1]}",
            "vehicle_type": req.vehicle_type,
            "preference": req.preference,
            "emergency_mode": req.emergency_mode,
            "recommended_route_id": recommended_route.get("route_id", "route_1"),
            "distance_km": recommended_route.get("distance_km", 0.0),
            "duration_minutes": recommended_route.get("duration_minutes", 0.0),
            "smart_score": recommended_route.get("smart_score", 0.0),
            "fuel_liters": recommended_route.get("fuel", {}).get("fuel_liters", 0.0),
            "fuel_cost": recommended_route.get("fuel", {}).get("fuel_cost", 0.0),
            "summary": explanation.get("summary", ""),
            "full_result": {
                "source": src_res,
                "destination": dest_res,
                "recommended_id": recommended_route.get("route_id"),
                "smart_score": recommended_route.get("smart_score")
            }
        }
        history_id = history_repo.save_history(history_entry)
    except Exception as e:
        logger.error(f"Failed to record search history: {e}")

    return {
        "success": True,
        "source": {
            "lat": src_coords[0],
            "lon": src_coords[1],
            "display_name": src_res.get("display_name", req.source)
        },
        "destination": {
            "lat": dest_coords[0],
            "lon": dest_coords[1],
            "display_name": dest_res.get("display_name", req.destination)
        },
        "routes": scored_routes,
        "recommended_route": recommended_route,
        "explanation": explanation,
        "applied_weights": recommended_route.get("applied_weights", {}),
        "history_id": history_id,
        "demo_mode": req.demo_mode,
        "emergency_mode": req.emergency_mode,
    }
