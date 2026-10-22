"""
Weather API Endpoints for Smart Route AI.
Provides on-demand live weather and corridor forecasting queries.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from src.services.weather_service import weather_service
from src.services.geocoding_service import geocoding_service
from src.utils.logging_config import logger

weather_router = APIRouter(prefix="/weather", tags=["Weather"])


@weather_router.get("/live")
async def get_live_weather(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    location: Optional[str] = Query(None, description="Place or city name"),
    demo_mode: bool = Query(False, description="Whether to simulate offline data")
):
    """
    Returns live meteorological conditions and forecast for coordinates or city name.
    """
    target_lat = lat
    target_lon = lon
    display_name = location

    if location and (target_lat is None or target_lon is None):
        geo = await geocoding_service.geocode(location)
        if not geo.get("success"):
            raise HTTPException(status_code=404, detail=f"Location '{location}' could not be resolved.")
        target_lat = geo["lat"]
        target_lon = geo["lon"]
        display_name = geo.get("display_name", location)

    if target_lat is None or target_lon is None:
        # Default fallback coords e.g. Bengaluru
        target_lat, target_lon = 12.9716, 77.5946
        display_name = "Bengaluru, Karnataka, India"

    try:
        weather_data = await weather_service.get_weather(target_lat, target_lon, demo_mode=demo_mode)
        return {
            "success": True,
            "location": display_name,
            "coordinates": {"lat": target_lat, "lon": target_lon},
            "weather": weather_data
        }
    except Exception as e:
        logger.error(f"Weather query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve live weather data.")


@weather_router.get("/corridor")
async def get_corridor_forecast(
    source: str = Query(..., description="Starting location"),
    destination: str = Query(..., description="Destination location"),
    demo_mode: bool = Query(False, description="Simulate offline data")
):
    """
    Returns multi-point corridor forecast along the direct path between source and destination.
    """
    src_geo = await geocoding_service.geocode(source)
    if not src_geo.get("success"):
        raise HTTPException(status_code=404, detail=f"Source '{source}' could not be located.")

    dest_geo = await geocoding_service.geocode(destination)
    if not dest_geo.get("success"):
        raise HTTPException(status_code=404, detail=f"Destination '{destination}' could not be located.")

    src_pt = (src_geo["lat"], src_geo["lon"])
    dest_pt = (dest_geo["lat"], dest_geo["lon"])

    # Interpolate checkpoints
    pts = [
        src_pt,
        ((2 * src_pt[0] + dest_pt[0]) / 3.0, (2 * src_pt[1] + dest_pt[1]) / 3.0),
        ((src_pt[0] + 2 * dest_pt[0]) / 3.0, (src_pt[1] + 2 * dest_pt[1]) / 3.0),
        dest_pt
    ]

    try:
        corridor_data = await weather_service.get_corridor_weather(pts, demo_mode=demo_mode)
        return {
            "success": True,
            "source": src_geo.get("display_name", source),
            "destination": dest_geo.get("display_name", destination),
            "corridor_weather": corridor_data
        }
    except Exception as e:
        logger.error(f"Corridor weather forecast failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve corridor forecast.")
