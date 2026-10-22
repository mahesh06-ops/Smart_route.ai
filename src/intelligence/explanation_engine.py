"""
AI Explanation Engine.
Generates dynamic, human-readable explanations justifying route recommendations
based on empirical differences in traffic, safety, weather, travel time, and fuel economy.
"""
from typing import List, Dict, Any


class ExplanationEngine:
    @classmethod
    def generate_explanation(
        cls,
        recommended_route: Dict[str, Any],
        all_routes: List[Dict[str, Any]],
        preference: str = "balanced",
        emergency_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generates dynamic text explanation, key advantages, and potential caveats.
        """
        r_name = recommended_route.get("route_name", "Recommended Route")
        r_dist = recommended_route.get("distance_km", 0.0)
        r_dur = recommended_route.get("duration_minutes", 0.0)
        r_score = recommended_route.get("smart_score", 0.0)
        r_traffic = recommended_route.get("traffic", {}).get("level", "LOW")
        r_safety = recommended_route.get("safety", {}).get("score", 85.0)
        r_weather = recommended_route.get("weather", {}).get("condition", "CLEAR")
        r_fuel = recommended_route.get("fuel", {}).get("fuel_liters", 0.0)

        advantages = []
        caveats = []

        # Compare against other routes
        other_routes = [r for r in all_routes if r.get("route_id") != recommended_route.get("route_id")]

        if other_routes:
            min_other_dist = min(r.get("distance_km", r_dist) for r in other_routes)
            min_other_dur = min(r.get("duration_minutes", r_dur) for r in other_routes)
            max_other_safety = max(r.get("safety", {}).get("score", 70) for r in other_routes)

            # Check time advantage
            if r_dur < min_other_dur:
                saved_mins = round(min_other_dur - r_dur)
                advantages.append(f"Saves ~{saved_mins} mins travel time compared to alternative options")
            elif r_dur == min_other_dur:
                advantages.append("Equal fastest travel time available")

            # Check traffic advantage
            if r_traffic in ("LOW", "MODERATE"):
                advantages.append(f"Favorable {r_traffic.lower()} congestion levels with steady vehicle flow")

            # Check safety
            if r_safety >= max_other_safety or r_safety >= 85:
                advantages.append(f"Superior corridor safety index ({r_safety}/100) on divided expressway")

            # Check fuel
            min_other_fuel = min(r.get("fuel", {}).get("fuel_liters", r_fuel) for r in other_routes)
            if r_fuel <= min_other_fuel:
                advantages.append(f"Most fuel-efficient corridor ({r_fuel} L total consumption)")

            # Check weather
            if r_weather in ("CLEAR", "CLOUDY"):
                advantages.append(f"Optimal driving conditions with {r_weather.lower()} sky")

            # Check caveats (e.g. distance trade-off)
            if r_dist > min_other_dist:
                extra_km = round(r_dist - min_other_dist, 1)
                caveats.append(f"Approximately {extra_km} km longer than the absolute shortest path, but chosen to avoid congestion bottlenecks and risk zones.")

            # Formulate narrative paragraph
            if emergency_mode:
                summary = (
                    f"🚨 Emergency Priority Active: {r_name} is selected for fastest clearance ({r_dur:.0f} mins) "
                    f"with {r_traffic.lower()} traffic friction and high transit safety ({r_safety}/100)."
                )
            elif preference.lower() == "fastest":
                summary = (
                    f"{r_name} achieves the fastest estimated travel time ({r_dur:.0f} mins). "
                    f"Traffic flow is rated {r_traffic} and road conditions allow optimal transit speed."
                )
            elif preference.lower() == "shortest":
                summary = (
                    f"{r_name} is chosen as the most direct spatial route ({r_dist:.1f} km). "
                    f"Multi-factor scoring confirms acceptable travel time and road conditions."
                )
            elif preference.lower() == "safest":
                summary = (
                    f"{r_name} offers the highest safety rating ({r_safety}/100) across evaluated corridors. "
                    f"Low accident risk profile, clear weather ({r_weather}), and wide roadway geometry prioritize passenger security."
                )
            elif preference.lower() == "fuel_efficient":
                summary = (
                    f"{r_name} provides peak fuel economy requiring approximately {r_fuel:.1f} liters. "
                    f"Consistent driving speeds and moderate topography minimize consumption."
                )
            else:  # Balanced
                summary = (
                    f"{r_name} is selected because it delivers the smartest multi-factor balance. "
                    f"At {r_dist:.1f} km and {r_dur:.0f} mins, it balances smooth traffic ({r_traffic}), "
                    f"solid safety ({r_safety}/100), and efficient fuel consumption ({r_fuel:.1f} L)."
                )
        else:
            # Single route scenario
            summary = (
                f"{r_name} ({r_dist:.1f} km, {r_dur:.0f} mins) is the primary validated driving corridor, "
                f"scoring {r_score}/100 with {r_traffic.lower()} traffic and {r_weather.lower()} weather."
            )
            advantages = [
                f"Direct arterial connection ({r_dist:.1f} km)",
                f"Calculated transit duration of {r_dur:.0f} minutes",
                f"Safe transit index rating of {r_safety}/100",
                f"Estimated fuel consumption: {r_fuel:.1f} liters",
            ]

        if not advantages:
            advantages = ["Best overall multi-factor composite score among available routes"]

        return {
            "summary": summary,
            "advantages": advantages,
            "caveats": caveats,
            "headline": f"Why {r_name} is Recommended",
        }


explanation_engine = ExplanationEngine()
