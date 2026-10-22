"""
Normalization utilities for multi-factor scoring in Smart Route AI.
Normalizes heterogeneous metrics (time, distance, traffic, safety, weather, fuel)
into standard 0 - 100 scales.
"""
from typing import List, Dict, Any


def clamp(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamps value to [min_val, max_val]."""
    return max(min_val, min(max_val, val))


def normalize_metric(
    value: float,
    min_val: float,
    max_val: float,
    higher_is_better: bool = True
) -> float:
    """
    Normalizes a numeric value into a 0.0 to 100.0 scale.
    If higher_is_better is True (e.g., safety, weather quality):
        higher values yield closer to 100.
    If higher_is_better is False (e.g., distance, duration, fuel, traffic penalty):
        lower values yield closer to 100.
    """
    if max_val == min_val:
        return 100.0 if higher_is_better else 100.0

    # Ensure min < max
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    ratio = (value - min_val) / (max_val - min_val)
    ratio = max(0.0, min(1.0, ratio))

    if higher_is_better:
        score = ratio * 100.0
    else:
        # Lower raw value gets higher score
        score = (1.0 - ratio) * 100.0

    return round(clamp(score, 0.0, 100.0), 2)


def normalize_route_group(routes_metrics: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Given a list of metric dicts for comparing alternative routes:
    Calculates relative min/max across the group so that relative advantages
    are properly rewarded (e.g. shortest travel time receives 100 for time).
    """
    if not routes_metrics:
        return []

    # Identify keys
    keys = list(routes_metrics[0].keys())
    mins = {k: min(r[k] for r in routes_metrics) for k in keys}
    maxs = {k: max(r[k] for r in routes_metrics) for k in keys}

    normalized_list = []
    for r in routes_metrics:
        norm_r = {}
        for k in keys:
            # Determine direction: safety and weather_quality are higher_is_better
            higher_is_better = k in ("safety_score", "weather_quality", "road_quality")
            norm_r[k] = normalize_metric(r[k], mins[k], maxs[k], higher_is_better=higher_is_better)
        normalized_list.append(norm_r)

    return normalized_list
