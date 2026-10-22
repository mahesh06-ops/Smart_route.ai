"""
Weather Intelligence Engine.
Analyzes weather conditions along trip endpoints and computes driving impact score.
Supported conditions: CLEAR, PARTLY CLOUDY, OVERCAST, FOG, DRIZZLE, RAIN, HEAVY RAIN, SNOW, STORM, FREEZING RAIN.
Clearly flags data source (Live Open-Meteo vs Fallback/Simulated).
"""
from typing import Dict, Any, Optional, List


class WeatherEngine:
    # Granular weather driving profiles and risk coefficients
    WEATHER_PROFILES = {
        "CLEAR": {
            "quality_score": 98,
            "risk_penalty": 0,
            "desc": "Optimal visibility, dry pavement, and ideal driving traction.",
            "icon": "☀️",
            "hazards": []
        },
        "PARTLY CLOUDY": {
            "quality_score": 94,
            "risk_penalty": 2,
            "desc": "Mild cloud cover with excellent road visibility.",
            "icon": "⛅",
            "hazards": []
        },
        "OVERCAST": {
            "quality_score": 88,
            "risk_penalty": 5,
            "desc": "Overcast skies; normal road grip and standard visual range.",
            "icon": "☁️",
            "hazards": []
        },
        "FOG": {
            "quality_score": 48,
            "risk_penalty": 38,
            "desc": "Dense fog / mist causing critically reduced sightlines. Maintain low speeds and use fog lamps.",
            "icon": "🌫️",
            "hazards": ["Critically Reduced Sight Distance", "Low Visibility Warning"]
        },
        "DRIZZLE": {
            "quality_score": 80,
            "risk_penalty": 10,
            "desc": "Light drizzle; initial slickness on asphalt. Moderate wiper usage required.",
            "icon": "🌦️",
            "hazards": ["Slick Road Surface"]
        },
        "RAIN": {
            "quality_score": 65,
            "risk_penalty": 22,
            "desc": "Wet surface, increased braking distance (~25%), moderate water spray from heavy vehicles.",
            "icon": "🌧️",
            "hazards": ["Wet Road Surface", "Increased Braking Distance"]
        },
        "HEAVY RAIN": {
            "quality_score": 38,
            "risk_penalty": 45,
            "desc": "Severe downpour; heightened aquaplaning risk, localized waterlogging and low contrast.",
            "icon": "⛈️",
            "hazards": ["Aquaplaning Risk", "Severe Waterlogging Hazard", "Low Visual Contrast"]
        },
        "SNOW": {
            "quality_score": 32,
            "risk_penalty": 55,
            "desc": "Snowfall / freezing slush on carriageway. Severe loss of tire adhesion; anti-skid precautions essential.",
            "icon": "❄️",
            "hazards": ["Icy Roadways", "Severe Traction Loss", "Freezing Surface"]
        },
        "FREEZING RAIN": {
            "quality_score": 20,
            "risk_penalty": 70,
            "desc": "Black ice hazard! Freezing precipitation forms invisible ice sheets across asphalt.",
            "icon": "🧊",
            "hazards": ["Black Ice Emergency", "Extreme Loss of Control Hazard"]
        },
        "STORM": {
            "quality_score": 22,
            "risk_penalty": 65,
            "desc": "Thunderstorms with lightning strikes, severe gale gusts (>50 km/h) and flying debris risks.",
            "icon": "⚡",
            "hazards": ["Severe Crosswind Warning", "Lightning Hazard", "Debris / Falling Branch Risk"]
        },
    }

    # Complete WMO Code to Category & Description Mapping
    WMO_MAP = {
        0: ("CLEAR", "Clear sky", 0.0, "☀️"),
        1: ("CLEAR", "Mainly clear", 0.0, "🌤️"),
        2: ("PARTLY CLOUDY", "Partly cloudy", 0.0, "⛅"),
        3: ("OVERCAST", "Overcast", 0.0, "☁️"),
        45: ("FOG", "Foggy conditions", 0.0, "🌫️"),
        48: ("FOG", "Depositing rime fog", 0.0, "🌫️"),
        51: ("DRIZZLE", "Light drizzle", 0.5, "🌦️"),
        53: ("DRIZZLE", "Moderate drizzle", 1.2, "🌦️"),
        55: ("DRIZZLE", "Dense drizzle", 2.5, "🌦️"),
        56: ("FREEZING RAIN", "Light freezing drizzle", 0.8, "🧊"),
        57: ("FREEZING RAIN", "Dense freezing drizzle", 2.0, "🧊"),
        61: ("RAIN", "Slight rain", 2.0, "🌧️"),
        63: ("RAIN", "Moderate rain", 6.0, "🌧️"),
        65: ("HEAVY RAIN", "Heavy rain downpour", 16.0, "🌧️"),
        66: ("FREEZING RAIN", "Light freezing rain", 3.0, "🧊"),
        67: ("FREEZING RAIN", "Heavy freezing rain", 10.0, "🧊"),
        71: ("SNOW", "Slight snow fall", 1.5, "🌨️"),
        73: ("SNOW", "Moderate snow fall", 4.5, "🌨️"),
        75: ("SNOW", "Heavy snow fall", 12.0, "❄️"),
        77: ("SNOW", "Snow grains", 1.0, "❄️"),
        80: ("RAIN", "Slight rain showers", 3.0, "🌦️"),
        81: ("RAIN", "Moderate rain showers", 7.5, "🌧️"),
        82: ("HEAVY RAIN", "Violent rain showers", 22.0, "⛈️"),
        85: ("SNOW", "Slight snow showers", 2.0, "🌨️"),
        86: ("SNOW", "Heavy snow showers", 8.0, "❄️"),
        95: ("STORM", "Thunderstorm", 18.0, "⚡"),
        96: ("STORM", "Thunderstorm with slight hail", 24.0, "⛈️"),
        99: ("STORM", "Thunderstorm with heavy hail", 35.0, "⛈️"),
    }

    @classmethod
    def get_wmo_interpretation(cls, wmo_code: int) -> tuple:
        """Returns (condition_key, description, estimated_rain_mm, icon)"""
        return cls.WMO_MAP.get(wmo_code, ("CLEAR", "Clear conditions", 0.0, "☀️"))

    @classmethod
    def evaluate_weather(
        cls,
        condition: Optional[str] = None,
        condition_desc: Optional[str] = None,
        temperature_c: Optional[float] = None,
        apparent_temperature_c: Optional[float] = None,
        humidity_pct: Optional[float] = None,
        rain_mm: Optional[float] = None,
        precipitation_probability: Optional[int] = None,
        wind_kmh: Optional[float] = None,
        wind_gusts_kmh: Optional[float] = None,
        wind_direction_deg: Optional[int] = None,
        visibility_km: Optional[float] = None,
        uv_index: Optional[float] = None,
        is_live: bool = False,
        forecast_hourly: Optional[List[Dict[str, Any]]] = None,
        forecast_daily: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates weather impact on route safety and travel comfort with rich meteorology.
        """
        raw_cond = (condition or "CLEAR").upper().strip()
        if raw_cond == "CLOUDY":
            raw_cond = "PARTLY CLOUDY"

        if raw_cond not in cls.WEATHER_PROFILES:
            raw_cond = "CLEAR"

        profile = cls.WEATHER_PROFILES[raw_cond]
        temp = float(temperature_c if temperature_c is not None else 28.0)
        app_temp = float(apparent_temperature_c if apparent_temperature_c is not None else temp)
        humidity = float(humidity_pct if humidity_pct is not None else 55.0)
        rain = float(rain_mm if rain_mm is not None else (0.0 if raw_cond in ("CLEAR", "PARTLY CLOUDY", "OVERCAST") else 4.5))
        precip_prob = int(precipitation_probability if precipitation_probability is not None else (min(100, int(rain * 15)) if rain > 0 else 5))
        wind = float(wind_kmh if wind_kmh is not None else 14.0)
        gusts = float(wind_gusts_kmh if wind_gusts_kmh is not None else max(wind * 1.3, wind + 5))
        vis = float(visibility_km if visibility_km is not None else (10.0 if raw_cond in ("CLEAR", "PARTLY CLOUDY", "OVERCAST") else 3.5))
        uv = float(uv_index if uv_index is not None else 5.0)

        # Build dynamic hazard warnings
        hazards = list(profile["hazards"])
        if vis < 2.0 and "Critically Reduced Sight Distance" not in hazards:
            hazards.append("Extreme Low Visibility (< 2 km)")
        elif vis < 5.0 and "Low Visibility Warning" not in hazards:
            hazards.append("Reduced Visibility (2-5 km)")

        if gusts >= 45.0 and "Severe Crosswind Warning" not in hazards:
            hazards.append(f"High Gusting Crosswinds ({round(gusts)} km/h)")

        if rain >= 12.0 and "Aquaplaning Risk" not in hazards:
            hazards.append("High Aquaplaning Risk")

        if temp >= 42.0:
            hazards.append("Extreme Heat Advisory (Engine & Tire Stress)")
        elif temp <= 0.0 and "Icy Roadways" not in hazards:
            hazards.append("Sub-Zero Surface Freezing Advisory")

        # Compute dynamic driving quality score (0 - 100)
        base_score = profile["quality_score"]
        if rain > 5.0:
            base_score = max(20, base_score - int(rain * 1.5))
        if vis < 4.0:
            base_score = max(20, base_score - int((4.0 - vis) * 8))
        if wind > 35.0:
            base_score = max(20, base_score - int((wind - 35) * 0.8))

        risk_pen = max(0, 100 - base_score)

        return {
            "condition": raw_cond,
            "condition_desc": condition_desc or profile["desc"],
            "icon": profile["icon"],
            "temperature_c": round(temp, 1),
            "apparent_temperature_c": round(app_temp, 1),
            "humidity_pct": round(humidity, 0),
            "rain_mm": round(rain, 1),
            "precipitation_probability": precip_prob,
            "wind_speed_kmh": round(wind, 1),
            "wind_gusts_kmh": round(gusts, 1),
            "wind_direction_deg": wind_direction_deg or 180,
            "visibility_km": round(vis, 1),
            "uv_index": round(uv, 1),
            "score": base_score,  # 0 - 100, higher = better driving conditions
            "risk_penalty": risk_pen,
            "impact_summary": profile["desc"],
            "hazards": hazards,
            "is_live": is_live,
            "data_source": "Live Open-Meteo Meteorological API (High-Precision)" if is_live else "Analytical Meteorological Simulation",
            "forecast_hourly": forecast_hourly or [],
            "forecast_daily": forecast_daily or [],
        }


weather_engine = WeatherEngine()

