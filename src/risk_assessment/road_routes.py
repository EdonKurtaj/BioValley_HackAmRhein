"""Cached OSRM shortest-path candidates; deterministic demo disruption handling.

OSRM searches the actual driving graph. We rank only its returned candidates,
never inventing connections, reverse edges or claiming a global second-shortest path.
"""

import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parents[2] / "config/demo-road-routes.json"
ROAD_CACHE = json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def route_distance_km(coordinates) -> float:
    """Geodesic length of full road geometry, without off-road endpoint connectors."""
    distance = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coordinates, coordinates[1:]):
        a = sin(radians(lat2 - lat1) / 2) ** 2
        a += cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
        distance += 6371.0 * 2 * asin(min(1.0, sqrt(a)))
    return distance


def edges(coordinates):
    return {(tuple(a), tuple(b)) for a, b in zip(coordinates, coordinates[1:])}


def rank_routes(candidates, *, blocked_edges=(), delay_seconds=None):
    """Reject closed directed segments; minimize base seconds plus segment penalties.

Traffic penalties must be supplied explicitly. The public OSRM driving profile
has no live traffic. The demo uses a synthetic closure on a known candidate edge.
"""
    delays = delay_seconds or {}
    ranked = []
    for candidate in candidates:
        segments = edges(candidate["coordinates"])
        if segments.intersection(blocked_edges):
            continue
        cost = candidate["duration_s"] + sum(delay for edge, delay in delays.items() if edge in segments)
        ranked.append((cost, candidate))
    return [candidate for _, candidate in sorted(ranked, key=lambda item: item[0])]


def road_candidates(shipment_id):
    return rank_routes(ROAD_CACHE["shipments"][shipment_id]["routes"])


def reroute_options(plan):
    """Find a connected alternate from the frozen truck position, before a closure.

Only candidates sharing the entire travelled prefix are eligible. Choosing from
complete provider paths preserves their direction/turn validity and avoids teleporting.
"""
    candidates = road_candidates(plan.id)
    primary = candidates[0]["coordinates"]
    total = route_distance_km(primary)
    if total <= 0 or not 0 <= plan.jam_fraction < 1:
        return None
    travelled = 0.0
    index = 0
    if plan.jam_fraction > 0:
        for index in range(1, len(primary) - 1):
            travelled += route_distance_km(primary[index - 1:index + 1])
            if travelled + total * 1e-12 >= total * plan.jam_fraction:
                break
    prefix = primary[:index + 1]
    compatible = [route for route in candidates[1:] if route["coordinates"][:index + 1] == prefix]
    if not compatible:
        return None
    alternate = compatible[0]["coordinates"]
    divergence = index + 1
    while divergence < min(len(primary), len(alternate)) and primary[divergence] == alternate[divergence]:
        divergence += 1
    if divergence >= len(primary):
        return None
    blocked = (tuple(primary[divergence - 1]), tuple(primary[divergence]))
    available = rank_routes(compatible, blocked_edges={blocked})
    if not available:
        return None
    chosen = available[0]
    # Scale provider costs to the authored replay schedule, then subtract time
    # already spent on the identical prefix. Only the remaining path changes.
    remaining_minutes = plan.travel_minutes * (
        chosen["duration_s"] / candidates[0]["duration_s"] - travelled / total)
    if remaining_minutes <= 0:
        return None
    return {"coordinates": chosen["coordinates"], "progress": travelled / total,
            "remaining_minutes": remaining_minutes, "prefix_km": travelled,
            "blocked_location": primary[divergence], "candidate_count": len(candidates)}
