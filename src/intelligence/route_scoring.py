"""
Intelligent Route Scoring Engine.
Central decision engine that normalizes multi-factor metrics and combines them
according to user preference weights to calculate the Smart Route Score (0 - 100).
"""
from typing import List, Dict, Any
from src.utils.normalization import normalize_metric, clamp
from src.intelligence.preference_engine import preference_engine


class RouteScoringEngine:
    @classmethod
    def score_routes(
        cls,
        routes: List[Dict[str, Any]],
        preference: str = "balanced",
        emergency_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scores and ranks a set of alternative routes.
        Calculates normalized scores across all factors, applies dynamic weights,
        and determines the recommended route.
        """
        if not routes:
            return []

        weights = preference_engine.get_weights(preference, emergency_mode=emergency_mode)

        # Find min/max ranges across available routes to normalize competitively
        durations = [r["duration_minutes"] for r in routes]
        distances = [r["distance_km"] for r in routes]
        traffic_scores = [r["traffic"]["score"] for r in routes]
        safety_scores = [r["safety"]["score"] for r in routes]
        weather_scores = [r["weather"]["score"] for r in routes]
        fuel_liters = [r["fuel"]["fuel_liters"] for r in routes]

        min_dur, max_dur = min(durations), max(durations)
        min_dist, max_dist = min(distances), max(distances)
        min_traf, max_traf = min(traffic_scores), max(traffic_scores)
        min_safe, max_safe = min(safety_scores), max(safety_scores)
        min_weath, max_weath = min(weather_scores), max(weather_scores)
        min_fuel, max_fuel = min(fuel_liters), max(fuel_liters)

        scored_routes = []
        for r in routes:
            # 1. Travel Time score (lower duration is better)
            # If all routes have same duration, score is 90
            norm_time = normalize_metric(r["duration_minutes"], min_dur, max_dur, higher_is_better=False) if min_dur != max_dur else 90.0

            # 2. Distance score (lower distance is better)
            norm_distance = normalize_metric(r["distance_km"], min_dist, max_dist, higher_is_better=False) if min_dist != max_dist else 90.0

            # 3. Traffic score (higher traffic smoothness score is better)
            # Use the traffic engine's absolute score (0-100) directly or relative
            raw_traffic = float(r["traffic"]["score"])
            norm_traffic = clamp(raw_traffic, 10.0, 100.0)

            # 4. Safety score (higher safety score is better)
            raw_safety = float(r["safety"]["score"])
            norm_safety = clamp(raw_safety, 10.0, 100.0)

            # 5. Weather score (higher weather quality score is better)
            raw_weather = float(r["weather"]["score"])
            norm_weather = clamp(raw_weather, 10.0, 100.0)

            # 6. Fuel efficiency score (lower fuel liters is better)
            norm_fuel = normalize_metric(r["fuel"]["fuel_liters"], min_fuel, max_fuel, higher_is_better=False) if min_fuel != max_fuel else 90.0

            # Compute weighted components
            w_time = weights.get("time", 0.25)
            w_traffic = weights.get("traffic", 0.20)
            w_safety = weights.get("safety", 0.20)
            w_weather = weights.get("weather", 0.15)
            w_fuel = weights.get("fuel", 0.10)
            w_distance = weights.get("distance", 0.10)

            comp_time = round(norm_time * w_time, 1)
            comp_traffic = round(norm_traffic * w_traffic, 1)
            comp_safety = round(norm_safety * w_safety, 1)
            comp_weather = round(norm_weather * w_weather, 1)
            comp_fuel = round(norm_fuel * w_fuel, 1)
            comp_distance = round(norm_distance * w_distance, 1)

            total_score = round(comp_time + comp_traffic + comp_safety + comp_weather + comp_fuel + comp_distance, 1)
            total_score = clamp(total_score, 1.0, 100.0)

            breakdown = {
                "travel_time": {
                    "score": comp_time,
                    "max": round(w_time * 100, 1),
                    "normalized_pct": round(norm_time, 1)
                },
                "traffic": {
                    "score": comp_traffic,
                    "max": round(w_traffic * 100, 1),
                    "normalized_pct": round(norm_traffic, 1)
                },
                "safety": {
                    "score": comp_safety,
                    "max": round(w_safety * 100, 1),
                    "normalized_pct": round(norm_safety, 1)
                },
                "weather": {
                    "score": comp_weather,
                    "max": round(w_weather * 100, 1),
                    "normalized_pct": round(norm_weather, 1)
                },
                "fuel": {
                    "score": comp_fuel,
                    "max": round(w_fuel * 100, 1),
                    "normalized_pct": round(norm_fuel, 1)
                },
                "distance": {
                    "score": comp_distance,
                    "max": round(w_distance * 100, 1),
                    "normalized_pct": round(norm_distance, 1)
                },
                "total": total_score,
            }

            # Tag characteristics
            is_fast = (r["duration_minutes"] == min_dur)
            is_short = (r["distance_km"] == min_dist)
            is_safe = (r["safety"]["score"] == max_safe)
            is_econ = (r["fuel"]["fuel_liters"] == min_fuel)
            is_low_traf = (r["traffic"]["score"] == max_traf)

            tags = []
            if is_fast:
                tags.append({"label": "⚡ Fastest Transit", "type": "fast"})
            if is_safe:
                tags.append({"label": "🛡️ Safest Corridor", "type": "safe"})
            if is_econ:
                tags.append({"label": "⛽ Most Economical", "type": "fuel"})
            if is_short and not is_fast:
                tags.append({"label": "📍 Shortest Distance", "type": "distance"})
            if is_low_traf and not is_fast:
                tags.append({"label": "🟢 Lowest Congestion", "type": "traffic"})

            route_copy = dict(r)
            route_copy["smart_score"] = total_score
            route_copy["score_breakdown"] = breakdown
            route_copy["applied_weights"] = weights
            route_copy["is_fastest"] = is_fast
            route_copy["is_shortest"] = is_short
            route_copy["is_safest"] = is_safe
            route_copy["is_most_fuel_efficient"] = is_econ
            route_copy["is_lowest_traffic"] = is_low_traf
            route_copy["tags"] = tags
            scored_routes.append(route_copy)

        # Rank by smart_score descending
        scored_routes.sort(key=lambda x: x["smart_score"], reverse=True)

        # Mark recommendation flag
        for idx, sr in enumerate(scored_routes):
            sr["is_recommended"] = (idx == 0)
            sr["rank"] = idx + 1
            if idx == 0:
                sr["tags"].insert(0, {"label": "🏆 AI Recommended", "type": "recommended"})

        return scored_routes


route_scoring_engine = RouteScoringEngine()
