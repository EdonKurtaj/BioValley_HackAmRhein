"""Shared input and output contracts for the local risk engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class TemperatureReading:
    """A package-temperature observation, with its measurement uncertainty."""

    observed_at: datetime
    temperature_c: float
    accuracy_c: float | None = None


@dataclass(frozen=True)
class ExposureMetrics:
    """Thermal exposure; incomplete_history includes missing interval coverage,
    single readings, stale endpoints, unknown monitoring start, and sensor gaps.
    """

    minutes_above_max: float
    minutes_below_min: float
    peak_above_max_c: float
    peak_below_min_c: float
    hot_degree_hours: float
    cold_degree_hours: float
    borderline_readings: int = 0
    incomplete_history: bool = False
    quality_review_required: bool = False
    evidence: tuple[str, ...] = ()
    sensor_accuracy_unknown: bool = False


@dataclass(frozen=True)
class TrafficCounterMatch:
    """A counter, direction and lane explicitly mapped to a shipment route."""

    sitecode: str
    directionname: str
    lanecode: int


@dataclass(frozen=True)
class RoadCounterMatch:
    """Operator-verified detector/direction on the remaining route, with a reference speed.

    Reference speed is a supplied comparable normal speed, not a statutory speed limit.
    Vehicle class is explicit; car speeds must never silently substitute for truck speeds.
    """

    site_id: str
    vehicle_class: Literal["light", "heavy"]
    reference_speed_kmh: float


@dataclass(frozen=True)
class RoadEventMatch:
    """Operator-verified event location, direction and vehicle applicability.

    Verification applies only to the exact source update timestamp; changed messages
    require a new review. Effect is supplied by the operator, never inferred from text.
    """

    situation_id: str
    effect: Literal["disrupted", "restricted"]
    updated_at: str


@dataclass(frozen=True)
class RoadTrafficEvidence:
    """Current matched road signals and auditable exclusions; no inferred ETA."""

    severity: float | None = None
    restricted: bool = False
    disrupted: bool = False
    evidence: tuple[str, ...] = ()
    omitted: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RouteEvidence:
    """Route evidence must be explicit; absent inputs remain unknown."""

    disruption_observed: bool | None = None
    route_restricted: bool = False
    alternate_route_available: bool = False
    traffic_anomaly: float | None = None
    estimated_arrival_at: datetime | None = None
    material_needed_at: datetime | None = None
    buffer_hours: float = 4.0
    evidence: tuple[str, ...] = ()
    traffic_counters: tuple[TrafficCounterMatch, ...] = ()
    traffic_route_matched: bool = False
    exposed_handling: bool | None = None
    weather_severity: float | None = None
    alternate_route_suitable: bool | None = None
    alternate_arrival_at: datetime | None = None
    road_counters: tuple[RoadCounterMatch, ...] = ()
    road_events: tuple[RoadEventMatch, ...] = ()
    road_traffic_severity: float | None = None


@dataclass(frozen=True)
class Assessment:
    """Explainable action and separate thermal/logistics evidence."""

    action: Literal["normal", "buffer", "expedite", "reroute", "quality_review", "monitor"]
    reason: str
    thermal_status: str
    logistics_status: str
    thermal: ExposureMetrics | None = None
    logistics_evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ShipmentPlan:
    """Synthetic replay inputs. Coordinates are illustrative WGS84 lon/lat corridors.

    The replay provides complete simulated package/route/timing evidence; it does
    not replace missing observations in live mode or authorize real dispatch.
    """

    id: str
    name: str
    material: str
    priority: str
    origin: str
    destination: str
    route_name: str
    coordinates: tuple[tuple[float, float], ...]
    travel_minutes: float
    initial_elapsed_minutes: float
    need_after_departure_minutes: float
    delay_minutes: float
    jam_fraction: float
    start_c: float
    ambient_c: float
    tau_minutes: float
    alternate_coordinates: tuple[tuple[float, float], ...] = ()
