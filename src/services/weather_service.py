"""
Weather Service for Smart Route AI.
Integrates live weather and multi-point corridor forecasting from Open-Meteo API
with high-fidelity analytical weather simulation fallback when offline.
"""
import asyncio
from typing import Dict, Any, List, Tuple, Optional
import httpx

from src.intelligence.weather_engine import weather_engine
from src.utils.logging_config import logger


class WeatherService:
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    async def get_weather(
        cls,
        lat: float,
        lon: float,
        demo_mode: bool = False,
        include_forecast: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieves live weather and 24-hour / multi-day forecast for given coordinates.
        """
        if not demo_mode:
            try:
                params = {
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "current": (
                        "temperature_2m,relative_humidity_2m,apparent_temperature,"
                        "precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m,"
                        "wind_gusts_10m,visibility"
                    ),
                    "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,visibility",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
                    "forecast_days": 3,
                    "timezone": "auto"
                }

                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(cls.OPEN_METEO_URL, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        current = data.get("current", {})
                        wmo_code = int(current.get("weather_code", 0))
                        condition, cond_desc, rain_est, icon = weather_engine.get_wmo_interpretation(wmo_code)

                        temp = float(current.get("temperature_2m", 28.0))
                        app_temp = float(current.get("apparent_temperature", temp))
                        humidity = float(current.get("relative_humidity_2m", 50.0))
                        precip = float(current.get("precipitation", rain_est))
                        wind = float(current.get("wind_speed_10m", 12.0))
                        gusts = float(current.get("wind_gusts_10m", max(wind * 1.25, wind + 4.0)))
                        wind_dir = int(current.get("wind_direction_10m", 180))
                        # Open-Meteo visibility is in meters; convert to km
                        raw_vis_m = current.get("visibility")
                        vis_km = round(float(raw_vis_m) / 1000.0, 1) if raw_vis_m is not None else (10.0 if condition in ("CLEAR", "PARTLY CLOUDY") else 4.0)

                        # Parse hourly timeline (next 12 hours)
                        hourly_raw = data.get("hourly", {})
                        hourly_list = []
                        times = hourly_raw.get("time", [])[:12]
                        h_temps = hourly_raw.get("temperature_2m", [])
                        h_probs = hourly_raw.get("precipitation_probability", [])
                        h_precips = hourly_raw.get("precipitation", [])
                        h_codes = hourly_raw.get("weather_code", [])
                        h_winds = hourly_raw.get("wind_speed_10m", [])
                        h_vis = hourly_raw.get("visibility", [])

                        for i, t_str in enumerate(times):
                            h_code = h_codes[i] if i < len(h_codes) else 0
                            h_cond, h_desc, _, h_icon = weather_engine.get_wmo_interpretation(h_code)
                            h_vis_km = round(float(h_vis[i]) / 1000.0, 1) if i < len(h_vis) and h_vis[i] is not None else 10.0
                            
                            # Parse short time e.g. "14:00"
                            short_time = t_str.split("T")[-1] if "T" in t_str else t_str
                            hourly_list.append({
                                "time": short_time,
                                "iso_time": t_str,
                                "temp_c": round(float(h_temps[i]), 1) if i < len(h_temps) else temp,
                                "condition": h_cond,
                                "condition_desc": h_desc,
                                "icon": h_icon,
                                "precip_prob_pct": int(h_probs[i]) if i < len(h_probs) else 0,
                                "precip_mm": round(float(h_precips[i]), 1) if i < len(h_precips) else 0.0,
                                "wind_kmh": round(float(h_winds[i]), 1) if i < len(h_winds) else wind,
                                "visibility_km": h_vis_km,
                            })

                        # Parse daily forecast (3 days)
                        daily_raw = data.get("daily", {})
                        daily_list = []
                        d_times = daily_raw.get("time", [])[:3]
                        d_codes = daily_raw.get("weather_code", [])
                        d_maxs = daily_raw.get("temperature_2m_max", [])
                        d_mins = daily_raw.get("temperature_2m_min", [])
                        d_sums = daily_raw.get("precipitation_sum", [])
                        d_probs = daily_raw.get("precipitation_probability_max", [])
                        d_winds = daily_raw.get("wind_speed_10m_max", [])
                        d_uvs = daily_raw.get("uv_index_max", [])

                        for j, d_date in enumerate(d_times):
                            d_code = d_codes[j] if j < len(d_codes) else 0
                            d_cond, d_desc, _, d_icon = weather_engine.get_wmo_interpretation(d_code)
                            daily_list.append({
                                "date": d_date,
                                "condition": d_cond,
                                "condition_desc": d_desc,
                                "icon": d_icon,
                                "temp_max_c": round(float(d_maxs[j]), 1) if j < len(d_maxs) else temp + 2,
                                "temp_min_c": round(float(d_mins[j]), 1) if j < len(d_mins) else temp - 4,
                                "precip_sum_mm": round(float(d_sums[j]), 1) if j < len(d_sums) else 0.0,
                                "precip_prob_pct": int(d_probs[j]) if j < len(d_probs) else 0,
                                "wind_max_kmh": round(float(d_winds[j]), 1) if j < len(d_winds) else wind,
                                "uv_max": round(float(d_uvs[j]), 1) if j < len(d_uvs) else 5.0,
                            })

                        return weather_engine.evaluate_weather(
                            condition=condition,
                            condition_desc=cond_desc,
                            temperature_c=temp,
                            apparent_temperature_c=app_temp,
                            humidity_pct=humidity,
                            rain_mm=precip,
                            precipitation_probability=hourly_list[0]["precip_prob_pct"] if hourly_list else 5,
                            wind_kmh=wind,
                            wind_gusts_kmh=gusts,
                            wind_direction_deg=wind_dir,
                            visibility_km=vis_km,
                            uv_index=daily_list[0]["uv_max"] if daily_list else 5.0,
                            is_live=True,
                            forecast_hourly=hourly_list,
                            forecast_daily=daily_list
                        )
            except Exception as e:
                logger.warning(f"Live Open-Meteo fetch failed for ({lat},{lon}): {e}; switching to analytical model.")

        # High-Fidelity Analytical Simulation
        return cls._generate_fallback_weather(lat, lon)

    @classmethod
    async def get_corridor_weather(
        cls,
        waypoints: List[Tuple[float, float]],
        demo_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Fetches live multi-point weather along a route corridor in parallel.
        Evaluates origin, intermediate corridor waypoints, and destination.
        """
        if not waypoints:
            return cls._generate_fallback_weather(12.97, 77.59)

        # Select up to 4 representative checkpoints along the geometry
        pts_to_query = []
        if len(waypoints) <= 3:
            pts_to_query = waypoints
        else:
            # Origin, 33%, 66%, Destination
            n = len(waypoints)
            indices = [0, n // 3, (2 * n) // 3, n - 1]
            pts_to_query = [waypoints[i] for i in indices]

        # Query all checkpoints concurrently
        tasks = [cls.get_weather(pt[0], pt[1], demo_mode=demo_mode) for pt in pts_to_query]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, dict) and "score" in r:
                valid_results.append(r)
            else:
                valid_results.append(cls._generate_fallback_weather(waypoints[0][0], waypoints[0][1]))

        # The primary corridor weather represents the most representative / impactful section
        # Pick the lowest score (highest risk) checkpoint as driving constraint or average
        worst_weather = min(valid_results, key=lambda x: x.get("score", 100))
        origin_weather = valid_results[0]
        dest_weather = valid_results[-1]

        # Combine hazard alerts across all corridor segments
        combined_hazards = list(dict.fromkeys(
            h for res in valid_results for h in res.get("hazards", [])
        ))

        # Build checkpoint markers for map & UI
        checkpoints = []
        labels = ["Origin", "Corridor Alpha", "Corridor Beta", "Destination"]
        if len(valid_results) == 2:
            labels = ["Origin", "Destination"]
        elif len(valid_results) == 3:
            labels = ["Origin", "Midpoint Corridor", "Destination"]

        for idx, res in enumerate(valid_results):
            checkpoints.append({
                "label": labels[idx] if idx < len(labels) else f"Waypoint {idx+1}",
                "lat": pts_to_query[idx][0],
                "lon": pts_to_query[idx][1],
                "condition": res.get("condition"),
                "icon": res.get("icon"),
                "temperature_c": res.get("temperature_c"),
                "rain_mm": res.get("rain_mm"),
                "wind_kmh": res.get("wind_kmh"),
                "visibility_km": res.get("visibility_km"),
                "hazards": res.get("hazards", []),
                "score": res.get("score", 90),
            })

        # Synthesize aggregate corridor payload
        synthesized = dict(worst_weather)
        synthesized["origin_weather"] = origin_weather
        synthesized["destination_weather"] = dest_weather
        synthesized["corridor_checkpoints"] = checkpoints
        synthesized["hazards"] = combined_hazards
        synthesized["is_corridor_forecast"] = True

        return synthesized

    @classmethod
    def _generate_fallback_weather(cls, lat: float, lon: float) -> Dict[str, Any]:
        """Generates realistic structured meteorological data when offline."""
        # Deterministic variation based on coordinates
        seed_val = abs(int((lat + lon) * 100)) % 10
        cond = "CLEAR" if seed_val < 6 else ("PARTLY CLOUDY" if seed_val < 8 else "RAIN")
        cond_desc, rain_val, icon = ("Clear sunny sky", 0.0, "☀️") if cond == "CLEAR" else (
            ("Scattered clouds with mild sun", 0.0, "⛅") if cond == "PARTLY CLOUDY" else ("Passing rain showers", 3.2, "🌧️")
        )
        base_temp = 28.0 - (seed_val % 4)

        hourly = []
        for h in range(12):
            hour_str = f"{(8 + h) % 24:02d}:00"
            hourly.append({
                "time": hour_str,
                "iso_time": f"2026-09-04T{hour_str}",
                "temp_c": round(base_temp + (2.0 if 11 <= (8+h)%24 <= 16 else -1.5), 1),
                "condition": cond,
                "condition_desc": cond_desc,
                "icon": icon,
                "precip_prob_pct": 10 if cond != "RAIN" else 65,
                "precip_mm": 0.0 if cond != "RAIN" else 1.5,
                "wind_kmh": 12.0 + (h % 3),
                "visibility_km": 10.0 if cond != "RAIN" else 6.0,
            })

        daily = [
            {"date": "Today", "condition": cond, "condition_desc": cond_desc, "icon": icon, "temp_max_c": base_temp + 3, "temp_min_c": base_temp - 4, "precip_sum_mm": rain_val, "precip_prob_pct": 15, "wind_max_kmh": 16.0, "uv_max": 6.5},
            {"date": "Tomorrow", "condition": "PARTLY CLOUDY", "condition_desc": "Partly cloudy", "icon": "⛅", "temp_max_c": base_temp + 2, "temp_min_c": base_temp - 3, "precip_sum_mm": 0.0, "precip_prob_pct": 10, "wind_max_kmh": 14.0, "uv_max": 7.0},
            {"date": "Day 3", "condition": "CLEAR", "condition_desc": "Clear skies", "icon": "☀️", "temp_max_c": base_temp + 4, "temp_min_c": base_temp - 3, "precip_sum_mm": 0.0, "precip_prob_pct": 5, "wind_max_kmh": 12.0, "uv_max": 7.5},
        ]

        return weather_engine.evaluate_weather(
            condition=cond,
            condition_desc=cond_desc,
            temperature_c=base_temp,
            apparent_temperature_c=base_temp + 1.2,
            humidity_pct=52.0,
            rain_mm=rain_val,
            precipitation_probability=15 if cond != "RAIN" else 70,
            wind_kmh=13.5,
            wind_gusts_kmh=18.0,
            wind_direction_deg=220,
            visibility_km=10.0 if cond != "RAIN" else 6.5,
            uv_index=6.0,
            is_live=False,
            forecast_hourly=hourly,
            forecast_daily=daily
        )


weather_service = WeatherService()

