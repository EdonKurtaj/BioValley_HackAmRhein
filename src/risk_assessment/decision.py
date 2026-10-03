"""Turn separate quality and route evidence into explainable actions."""

from __future__ import annotations

from datetime import datetime
from math import isfinite

from .interfaces import Assessment, ExposureMetrics, RouteEvidence
from .priority import TRAFFIC_ANOMALY_REFERENCE_Z, PriorityScore

SYSTEM_BUFFER_THRESHOLD = 20.0
SYSTEM_EXPEDITE_THRESHOLD = 50.0
SYSTEM_URGENCY_EXPEDITE_THRESHOLD = 70.0
SYSTEM_NORMAL_MIN_COVERAGE = 50.0


def decide_action(thermal: ExposureMetrics | None, route: RouteEvidence) -> Assessment:
    """Apply deterministic decision rules; quality review takes precedence."""
    if not isfinite(route.buffer_hours) or route.buffer_hours < 0:
        raise ValueError("buffer hours must be finite and non-negative")
    if route.traffic_anomaly is not None and not isfinite(route.traffic_anomaly):
        raise ValueError("traffic anomaly must be finite")
    for timestamp in (route.estimated_arrival_at, route.material_needed_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("logistics timestamps must include a timezone")
    if thermal is None or thermal.quality_review_required:
        reason = "Package-temperature evidence is out of range, uncertain, incomplete, or missing; hold for qualified review."
        return Assessment("quality_review", reason, "review required", "separate route assessment", thermal, route.evidence)

    if route.route_restricted and route.alternate_route_available:
        return Assessment("reroute", "A route restriction is reported and a feasible alternate route is available.",
                          "within configured band", "restricted; alternate available", thermal, route.evidence)

    slack_hours = None
    if route.estimated_arrival_at and route.material_needed_at:
        slack_hours = (route.material_needed_at - route.estimated_arrival_at).total_seconds() / 3600
    if slack_hours is not None and slack_hours < route.buffer_hours:
        return Assessment("expedite", f"Estimated receipt leaves {slack_hours:.1f} h of production slack, below the {route.buffer_hours:g} h scenario buffer.",
                          "within configured band", "slack below buffer", thermal, route.evidence)

    if route.disruption_observed is True or route.route_restricted:
        return Assessment("buffer", "A route disruption is indicated, while available evidence does not justify a feasible reroute or expedite.",
                          "within configured band", "disruption indicated", thermal, route.evidence)

    if (route.disruption_observed is None and route.traffic_anomaly is None
            and route.estimated_arrival_at is None and route.material_needed_at is None):
        logistics_status = "unknown"
    else:
        logistics_status = "no actionable disruption evidence"
    return Assessment("normal", "No modeled trigger requires intervention; this is not a product-quality release decision.",
                      "within configured band", logistics_status, thermal, route.evidence)


def suggest_system_action(
    thermal: ExposureMetrics | None,
    route: RouteEvidence,
    priority: PriorityScore,
) -> dict[str, str]:
    """Map the weighted score and hard safety/logistics triggers to one suggestion."""
    quality_review = thermal is None or thermal.quality_review_required
    quality_reason = "Package-temperature evidence is missing, uncertain, incomplete, or outside its handling band."
    if route.route_restricted and route.alternate_route_available:
        logistics_suggestion = "Reroute"
        logistics_reason = "A matching route restriction is present and a feasible alternate route is available."
    else:
        urgency = priority.components.get("urgency")
        if (priority.minimum >= SYSTEM_EXPEDITE_THRESHOLD
                or (urgency is not None and urgency >= SYSTEM_URGENCY_EXPEDITE_THRESHOLD)):
            logistics_suggestion = "Expedite"
            logistics_reason = (f"Combined weighted risk is {priority.minimum:.1f}/100, or production urgency is high; "
                                "prioritize delivery/receiving.")
        else:
            traffic_trigger = (route.traffic_anomaly is not None
                               and route.traffic_anomaly >= TRAFFIC_ANOMALY_REFERENCE_Z)
            if (priority.minimum >= SYSTEM_BUFFER_THRESHOLD or route.disruption_observed is True
                    or route.route_restricted or traffic_trigger):
                logistics_suggestion = "Buffer"
                logistics_reason = (f"Combined weighted risk is {priority.minimum:.1f}/100 or a route disturbance is present; "
                                    "protect production slack and monitor the shipment.")
            elif priority.coverage_percent < SYSTEM_NORMAL_MIN_COVERAGE:
                logistics_suggestion = "Monitor"
                logistics_reason = (f"Only {priority.coverage_percent:.0f}% of score weight has evidence; "
                                    "collect shipment temperature and ETA data before calling it normal.")
            else:
                logistics_suggestion = "Normal"
                logistics_reason = "Combined score is below the intervention thresholds and evidence coverage is adequate."

    if quality_review:
        if logistics_suggestion in ("Reroute", "Expedite", "Buffer"):
            return {"suggestion": f"Quality review + {logistics_suggestion}",
                    "reason": f"{quality_reason} {logistics_reason}"}
        return {"suggestion": "Quality review",
                "reason": f"{quality_reason} {logistics_reason}"}
    return {"suggestion": logistics_suggestion, "reason": logistics_reason}


def parse_time(value: str | None) -> datetime | None:
    """Parse an ISO datetime and reject timezone-naive logistics timestamps."""
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("logistics timestamps must include a timezone")
    return parsed
