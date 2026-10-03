"""Transparent demo priority index; this is not a damage probability."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite

from .interfaces import ExposureMetrics, RouteEvidence
from .config import (
    ROUTE_WEIGHT, THERMAL_REFERENCE_DEGREE_HOURS, THERMAL_WEIGHT,
    TRAFFIC_ANOMALY_REFERENCE_Z, URGENCY_WEIGHT,
)


@dataclass(frozen=True)
class PriorityScore:
    """Score interval and weighted component values, all in 0–100 points."""

    minimum: float
    maximum: float
    coverage_percent: float
    evidence_coverage_available: int
    evidence_coverage_total: int
    score_weight_coverage_percent: float
    components: dict[str, float | None]
    weighted_points: dict[str, float | None]
    interpretation: str

    def as_dict(self) -> dict:
        return asdict(self)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))


def calculate_priority_score(
    thermal: ExposureMetrics | None,
    route: RouteEvidence,
) -> PriorityScore:
    """Calculate a weighted manufacturing priority index with missing-data bounds.

    Missing evidence is not treated as zero: the result is an interval whose
    upper bound assigns the unavailable weight its maximum possible value.
    """
    weights = {"thermal": THERMAL_WEIGHT, "route": ROUTE_WEIGHT, "urgency": URGENCY_WEIGHT}

    if thermal is None or thermal.incomplete_history or thermal.sensor_accuracy_unknown:
        thermal_score = None
    else:
        burden = thermal.hot_degree_hours + thermal.cold_degree_hours
        if not isfinite(burden) or burden < 0:
            raise ValueError("thermal degree-hours must be finite and non-negative")
        thermal_score = _clamp(burden / THERMAL_REFERENCE_DEGREE_HOURS * 100)

    route_signals: list[float] = []
    if route.disruption_observed is not None:
        route_signals.append(100.0 if route.disruption_observed else 0.0)
    if route.route_restricted:
        route_signals.append(100.0)
    if route.traffic_route_matched and route.traffic_anomaly is not None:
        if not isfinite(route.traffic_anomaly):
            raise ValueError("traffic anomaly must be finite")
        # Counts indicate unusual volume only; this subscore is not a delay estimate.
        route_signals.append(_clamp(route.traffic_anomaly / TRAFFIC_ANOMALY_REFERENCE_Z * 100))
    route_score = max(route_signals) if route_signals else None

    urgency_score = None
    if not isfinite(route.buffer_hours) or route.buffer_hours < 0:
        raise ValueError("buffer hours must be finite and non-negative")
    for timestamp in (route.estimated_arrival_at, route.material_needed_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("logistics timestamps must include a timezone")
    if route.estimated_arrival_at is not None and route.material_needed_at is not None:
        slack_hours = (route.material_needed_at - route.estimated_arrival_at).total_seconds() / 3600
        if route.buffer_hours == 0:
            urgency_score = 100.0 if slack_hours < 0 else 0.0
        else:
            urgency_score = _clamp((route.buffer_hours - slack_hours) / route.buffer_hours * 100)

    components = {"thermal": thermal_score, "route": route_score, "urgency": urgency_score}
    weighted = {
        name: (value * weights[name] if value is not None else None)
        for name, value in components.items()
    }
    known_points = sum(value for value in weighted.values() if value is not None)
    known_weight = sum(weights[name] for name, value in components.items() if value is not None)
    missing_weight = 1.0 - known_weight
    known_components = sum(value is not None for value in components.values())
    return PriorityScore(
        minimum=round(known_points, 1),
        maximum=round(min(100.0, known_points + missing_weight * 100), 1),
        coverage_percent=round(known_components / len(components) * 100, 1),
        evidence_coverage_available=known_components,
        evidence_coverage_total=len(components),
        score_weight_coverage_percent=round(known_weight * 100, 1),
        components={name: round(value, 1) if value is not None else None
                    for name, value in components.items()},
        weighted_points={name: round(value, 1) if value is not None else None
                         for name, value in weighted.items()},
        interpretation=(
            "Prototype manufacturing-priority index (0–100), not a probability of damage. "
            "Evidence coverage counts available thermal, route, and urgency input groups. "
            "Score-weight coverage is reported separately. Unknown inputs widen the score interval; "
            "traffic volume is not a delay estimate."
        ),
    )
