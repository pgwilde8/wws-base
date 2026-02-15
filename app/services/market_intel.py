"""
Market Intel Engine: Lane rates for Origin–Destination pairs.
Uses weighted benchmarks now; can pull from historical won loads as DB grows.
"""
import re
from typing import Tuple, Optional


# Baseline $/mi for common lanes (2026). In production: DAT/Truckstop API or own history.
LANE_BENCHMARKS = {
    ("NJ", "FL"): 2.45,
    ("FL", "NJ"): 1.85,  # Backhaul
    ("NJ", "GA"): 2.60,
    ("GA", "NJ"): 2.20,
    ("NY", "FL"): 2.55,
    ("FL", "NY"): 1.90,
    ("TX", "CA"): 2.40,
    ("CA", "TX"): 2.10,
    ("IL", "FL"): 2.35,
    ("OH", "TX"): 2.25,
}
DEFAULT_RPM = 2.10


def _extract_state(location: str) -> Optional[str]:
    """Extract state from 'City, ST' or 'City, State' format."""
    if not location or not isinstance(location, str):
        return None
    loc = location.strip()
    if "," in loc:
        part = loc.rsplit(",", 1)[-1].strip()
        if len(part) == 2:
            return part.upper()
        # "New Jersey" -> "NJ" (abbrev map would help; for now keep as-is)
        if len(part) > 2:
            return part.upper()
    # Try 2-letter state at end: "Charlotte NC"
    match = re.search(r"\b([A-Z]{2})\s*$", loc, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def get_market_average(
    origin_state: str,
    dest_state: str,
    equipment_type: str = "Van",
) -> dict:
    """
    Returns market rate per mile for a lane.
    In production: hit DAT/Truckstop API or query own won-load history.
    """
    o = (origin_state or "").strip().upper()[:2] if origin_state else ""
    d = (dest_state or "").strip().upper()[:2] if dest_state else ""
    if not o or not d:
        return {"market_rpm": DEFAULT_RPM, "confidence": "Low", "lane_key": None}

    lane_key = (o, d)
    rate_per_mile = LANE_BENCHMARKS.get(lane_key, DEFAULT_RPM)
    confidence = "High" if lane_key in LANE_BENCHMARKS else "Low"

    return {
        "market_rpm": rate_per_mile,
        "confidence": confidence,
        "lane_key": lane_key,
    }


def parse_origin_dest_states(origin: str, destination: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse origin/destination strings to state codes."""
    return _extract_state(origin), _extract_state(destination)
