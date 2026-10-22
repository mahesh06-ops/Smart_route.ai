"""
Validation utilities for inputs and locations in Smart Route AI.
"""
import re
from typing import Tuple, Optional


def sanitize_string(val: Optional[str]) -> str:
    """Strips and removes dangerous characters."""
    if not val:
        return ""
    # Strip whitespace, control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", val.strip())
    return cleaned[:120]  # Max reasonable location string length


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validates latitude and longitude ranges."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def validate_route_request(source: str, destination: str) -> Tuple[bool, Optional[str]]:
    """Validates source and destination inputs."""
    s = sanitize_string(source)
    d = sanitize_string(destination)

    if not s or not d:
        return False, "Please enter both source and destination locations."

    if len(s) < 2:
        return False, "Source location name is too short. Please be more specific."

    if len(d) < 2:
        return False, "Destination location name is too short. Please be more specific."

    if s.lower() == d.lower():
        return False, "Source and destination cannot be the same location."

    return True, None
