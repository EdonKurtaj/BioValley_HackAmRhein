"""Turn separate quality and route evidence into explainable actions."""

from __future__ import annotations

from datetime import datetime
from math import isfinite

from .config import ROAD_SPEED_WATCH_SEVERITY
from .interfaces import Assessment, ExposureMetrics, RouteEvidence
from .priority import TRAFFIC_ANOMALY_REFERENCE_Z, PriorityScore

QUALITY_HOLD_REASON = (
    "Package-temperature evidence is missing, uncertain, incomplete, or outside its handling band. "
    "Keep the material in controlled storage and hold for qualified review; "
    "onward delivery and production use remain blocked until authorized release."
)


def decide_action(
    thermal: ExposureMetrics | None, route: RouteEvidence, *, observed_only: bool = False,
) -> Assessment:
    """One policy for scenarios and observed planning; scores never authorize action.

    Observed-only recommendations are logistics advice, not permission to release
    unmonitored material. Normal requires complete package and shipment evidence.
    """
    if not isfinite(route.buffer_hours) or route.buffer_hours < 0:
        raise ValueError("buffer hours must be finite and non-negative")
    for value in (route.traffic_anomaly, route.weather_severity, route.road_traffic_severity):
        if value is not None and not isfinite(value):
            raise ValueError("shipment signals must be finite")
    if route.weather_severity is not None and not 0 <= route.weather_severity <= 100:
        raise ValueError("weather severity must be between 0 and 100")
    if route.road_traffic_severity is not None and not 0 <= route.road_traffic_severity <= 100:
        raise ValueError("road severity must be between 0 and 100")
    for timestamp in (route.estimated_arrival_at, route.material_needed_at, route.alternate_arrival_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("logistics timestamps must include a timezone")
    thermal_status = "unobserved; logistics advice only" if thermal is None else "within configured band"

    def result(action, reason, status):
        return Assessment(action, reason, thermal_status, status, thermal, route.evidence)

    if (thermal is None and not observed_only) or (thermal is not None and thermal.quality_review_required):
        return Assessment("quality_review", QUALITY_HOLD_REASON, "review required",
                          "onward delivery blocked", thermal, route.evidence)

    eta, needed, alternate = route.estimated_arrival_at, route.material_needed_at, route.alternate_arrival_at
    disrupted = route.disruption_observed is True or route.route_restricted
    if disrupted and route.alternate_route_available:
        if (route.alternate_route_suitable is True and eta is not None and needed is not None
                and alternate is not None and alternate < eta and alternate <= needed):
            return result("reroute", "A shipment route disturbance has a verified suitable alternative arriving earlier and before material need-by.",
                          "suitable alternate and acceptable ETA")
    if route.route_restricted:
        return result("monitor", "The route is restricted; verify a suitable alternative and its ETA before dispatch.", "restricted; no verified feasible alternative")
    if eta is None or needed is None:
        return result("monitor", "Shipment ETA and material need-by time are required before selecting a transport action.", "timing unknown")
    traffic = (route.traffic_route_matched and route.traffic_anomaly is not None
               and route.traffic_anomaly >= TRAFFIC_ANOMALY_REFERENCE_Z)
    traffic = traffic or (route.road_traffic_severity is not None
                          and route.road_traffic_severity >= ROAD_SPEED_WATCH_SEVERITY)
    weather = (route.exposed_handling is True and route.weather_severity is not None
               and route.weather_severity > 0)
    if (route.exposed_handling is None
            or (route.exposed_handling is True and route.weather_severity is None)):
        return result("monitor", "Handling conditions are unknown; verify protected or exposed transfer conditions before dispatch.", "handling evidence incomplete")
    if route.disruption_observed is None and not traffic and not weather:
        return result("monitor", "Shipment route status is unknown; verify route evidence before dispatch.", "route evidence incomplete")
    slack = (needed - eta).total_seconds() / 3600
    if slack < route.buffer_hours:
        return result("expedite", f"Estimated receipt leaves {slack:.1f} h of production slack, below the {route.buffer_hours:g} h buffer.", "slack below buffer")
    if disrupted or traffic or weather:
        return result("buffer", "Shipment-related disturbance has sufficient production slack; retain material in controlled storage.", "disturbance with sufficient slack")
    if (thermal is None or route.disruption_observed is None
            or route.exposed_handling is None
            or (route.exposed_handling is True and route.weather_severity is None)):
        return result("monitor", "Package, route or handling evidence is incomplete; do not classify the shipment as normal.", "shipment evidence incomplete")
    return result("normal", "Package evidence, route status, handling context and production slack have no intervention trigger; this is not a quality release.", "no modeled trigger")


def suggestion_from_assessment(assessment: Assessment) -> dict[str, str]:
    """Present the same decision and explanation in the operator suggestion."""
    return {"suggestion": ("Quality review" if assessment.action == "quality_review" else assessment.action.title()), "reason": assessment.reason}


def suggest_system_action(
    thermal: ExposureMetrics | None, route: RouteEvidence, priority: PriorityScore,
) -> dict[str, str]:
    """Compatibility entry point; priority is informational, not an action rule."""
    return suggestion_from_assessment(decide_action(thermal, route))


def parse_time(value: str | None) -> datetime | None:
    """Parse an ISO datetime and reject timezone-naive logistics timestamps."""
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("logistics timestamps must include a timezone")
    return parsed
