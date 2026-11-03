"""
Weather Service for Smart Route AI.
Integrates live weather and multi-point corridor forecasting with provider abstraction:
- Primary Provider: OpenWeatherMap (keyed via WEATHER_API_KEY)
- Resilient Live Fallback: Open-Meteo API (unkeyed)
- High-Fidelity Analytical Fallback: Local simulation when fully offline.
"""
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import httpx

from src.config.settings import settings
from src.intelligence.weather_engine import weather_engine
from src.utils.logging_config import logger


class WeatherService:
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
    OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    @classmethod
    def _map_owm_condition(cls, weather_id: int, main_str: str) -> Tuple[str, str, float, str]:
        """Maps OpenWeatherMap weather IDs to system standard condition, desc, rain est, and icon."""
        if 200 <= weather_id < 300:
            return ("STORM", "Thunderstorm advisory", 15.0, "⚡")
        elif 300 <= weather_id < 400:
            return ("DRIZZLE", "Light drizzle", 1.0, "🌦️")
        elif weather_id in (502, 503, 504, 522):
            return ("HEAVY RAIN", "Heavy downpour", 18.0, "🌧️")
        elif 500 <= weather_id < 600:
            return ("RAIN", "Passing rain showers", 4.0, "🌧️")
        elif 600 <= weather_id < 700:
            return ("SNOW", "Snow precipitation", 2.0, "❄️")
        elif 700 <= weather_id < 800:
            return ("FOG", "Reduced visibility / mist", 0.0, "🌫️")
        elif weather_id == 800:
            return ("CLEAR", "Clear sunny sky", 0.0, "☀️")
        elif weather_id in (801, 802):
            return ("PARTLY CLOUDY", "Scattered clouds with sunshine", 0.0, "⛅")
        elif weather_id in (803, 804):
            return ("OVERCAST", "Overcast cloud cover", 0.0, "☁️")
        return ("CLEAR", "Fair conditions", 0.0, "☀️")

    @classmethod
    async def _fetch_openweathermap(cls, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Queries OpenWeatherMap for current weather and 5-day / 3-hour forecast."""
        key = settings.WEATHER_API_KEY
        if not key or key.startswith("YOUR_"):
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                curr_task = client.get(
                    cls.OWM_CURRENT_URL,
                    params={"lat": round(lat, 4), "lon": round(lon, 4), "appid": key, "units": "metric"}
                )
                fc_task = client.get(
                    cls.OWM_FORECAST_URL,
                    params={"lat": round(lat, 4), "lon": round(lon, 4), "appid": key, "units": "metric"}
                )
                curr_resp, fc_resp = await asyncio.gather(curr_task, fc_task, return_exceptions=True)

                if isinstance(curr_resp, Exception) or curr_resp.status_code != 200:
                    return None

                curr_data = curr_resp.json()
                weather_arr = curr_data.get("weather", [{}])
                w_info = weather_arr[0] if weather_arr else {}
                w_id = int(w_info.get("id", 800))
                cond, cond_desc, rain_est, icon = cls._map_owm_condition(w_id, w_info.get("main", "Clear"))

                main_data = curr_data.get("main", {})
                temp = float(main_data.get("temp", 28.0))
                app_temp = float(main_data.get("feels_like", temp))
                humidity = float(main_data.get("humidity", 50.0))
                
                wind_data = curr_data.get("wind", {})
                wind_speed_ms = float(wind_data.get("speed", 3.5))
                wind_kmh = round(wind_speed_ms * 3.6, 1)
                gusts_ms = float(wind_data.get("gust", wind_speed_ms * 1.3))
                gusts_kmh = round(gusts_ms * 3.6, 1)
                wind_dir = int(wind_data.get("deg", 180))

                raw_vis = curr_data.get("visibility", 10000)
                vis_km = round(float(raw_vis) / 1000.0, 1)

                rain_data = curr_data.get("rain", {})
                rain_mm = float(rain_data.get("1h", rain_data.get("3h", rain_est)))

                # Parse forecast items if available
                hourly_list = []
                daily_list = []
                precip_prob = 10 if rain_mm == 0 else 70

                if not isinstance(fc_resp, Exception) and fc_resp.status_code == 200:
                    fc_data = fc_resp.json()
                    fc_items = fc_data.get("list", [])
                    if fc_items:
                        first_pop = fc_items[0].get("pop", 0.1)
                        precip_prob = int(float(first_pop) * 100)

                    # Build next 12 hours from 3-hour slices (up to 4 items)
                    for item in fc_items[:6]:
                        dt_txt = item.get("dt_txt", "")
                        time_part = dt_txt.split(" ")[-1][:5] if " " in dt_txt else "12:00"
                        item_w = item.get("weather", [{}])[0]
                        item_cond, item_desc, _, item_icon = cls._map_owm_condition(int(item_w.get("id", 800)), item_w.get("main", ""))
                        item_main = item.get("main", {})
                        item_wind = item.get("wind", {})
                        
                        hourly_list.append({
                            "time": time_part,
                            "iso_time": dt_txt,
                            "temp_c": round(float(item_main.get("temp", temp)), 1),
                            "condition": item_cond,
                            "condition_desc": item_desc,
                            "icon": item_icon,
                            "precip_prob_pct": int(float(item.get("pop", 0.0)) * 100),
                            "precip_mm": round(float(item.get("rain", {}).get("3h", 0.0)), 1),
                            "wind_kmh": round(float(item_wind.get("speed", 3.0)) * 3.6, 1),
                            "visibility_km": round(float(item.get("visibility", 10000)) / 1000.0, 1),
                        })

                    # Group daily slices for 3 days
                    daily_groups = {}
                    for item in fc_items:
                        dt_txt = item.get("dt_txt", "")
                        day = dt_txt.split(" ")[0] if " " in dt_txt else "day"
                        if day not in daily_groups:
                            daily_groups[day] = []
                        daily_groups[day].append(item)

                    for day_key, day_items in list(daily_groups.items())[:3]:
                        temps = [float(x.get("main", {}).get("temp", temp)) for x in day_items]
                        max_temp = max(temps) if temps else temp + 2
                        min_temp = min(temps) if temps else temp - 4
                        mid_item = day_items[len(day_items)//2]
                        mid_w = mid_item.get("weather", [{}])[0]
                        d_cond, d_desc, _, d_icon = cls._map_owm_condition(int(mid_w.get("id", 800)), mid_w.get("main", ""))
                        max_pop = max(float(x.get("pop", 0.0)) for x in day_items) if day_items else 0.1
                        
                        daily_list.append({
                            "date": day_key,
                            "condition": d_cond,
                            "condition_desc": d_desc,
                            "icon": d_icon,
                            "temp_max_c": round(max_temp, 1),
                            "temp_min_c": round(min_temp, 1),
                            "precip_sum_mm": round(sum(float(x.get("rain", {}).get("3h", 0.0)) for x in day_items), 1),
                            "precip_prob_pct": int(max_pop * 100),
                            "wind_max_kmh": round(max(float(x.get("wind", {}).get("speed", 3.0)) for x in day_items) * 3.6, 1),
                            "uv_max": 6.0,
                        })

                evaluated = weather_engine.evaluate_weather(
                    condition=cond,
                    condition_desc=cond_desc,
                    temperature_c=temp,
                    apparent_temperature_c=app_temp,
                    humidity_pct=humidity,
                    rain_mm=rain_mm,
                    precipitation_probability=precip_prob,
                    wind_kmh=wind_kmh,
                    wind_gusts_kmh=gusts_kmh,
                    wind_direction_deg=wind_dir,
                    visibility_km=vis_km,
                    uv_index=5.0,
                    is_live=True,
                    forecast_hourly=hourly_list,
                    forecast_daily=daily_list
                )
                evaluated["data_source"] = "Live OpenWeatherMap API"
                return evaluated

        except Exception as e:
            logger.warning(f"OpenWeatherMap call failed for ({lat},{lon}): {e}")
            return None

    @classmethod
    async def _fetch_open_meteo(cls, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Queries Open-Meteo forecast API (public unkeyed fallback)."""
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

            async with httpx.AsyncClient(timeout=5.0) as client:
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
                    raw_vis_m = current.get("visibility")
                    vis_km = round(float(raw_vis_m) / 1000.0, 1) if raw_vis_m is not None else (10.0 if condition in ("CLEAR", "PARTLY CLOUDY") else 4.0)

                    # Hourly
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

                    # Daily
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

                    evaluated = weather_engine.evaluate_weather(
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
                    evaluated["data_source"] = "Live Open-Meteo API"
                    return evaluated
        except Exception as e:
            logger.warning(f"Open-Meteo fallback fetch failed for ({lat},{lon}): {e}")
            return None

    @classmethod
    async def get_weather(
        cls,
        lat: float,
        lon: float,
        demo_mode: bool = False,
        include_forecast: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieves live weather using configured provider (OpenWeatherMap),
        falling back automatically to Open-Meteo, and finally to analytical simulation.
        """
        if not demo_mode:
            # 1. Primary: OpenWeatherMap if key configured
            if settings.WEATHER_PROVIDER == "openweathermap" and settings.WEATHER_API_KEY:
                owm_result = await cls._fetch_openweathermap(lat, lon)
                if owm_result:
                    return owm_result

            # 2. Resilient Live Fallback: Open-Meteo
            open_meteo_result = await cls._fetch_open_meteo(lat, lon)
            if open_meteo_result:
                return open_meteo_result

        # 3. High-Fidelity Analytical Simulation
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

        # Select up to 4 representative checkpoints along the geometry (Origin, 33%, 66%, Destination)
        pts_to_query = []
        if len(waypoints) <= 3:
            pts_to_query = waypoints
        else:
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
                "wind_kmh": res.get("wind_speed_kmh", 12.0),
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
                "iso_time": f"2026-10-25T{hour_str}",
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

        evaluated = weather_engine.evaluate_weather(
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
        evaluated["data_source"] = "Analytical Meteorological Simulation"
        return evaluated


weather_service = WeatherService()
