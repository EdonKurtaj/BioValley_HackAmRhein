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
    """Measured or simulated thermal exposure over a time series."""

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


@dataclass(frozen=True)
class Assessment:
    """Explainable action and separate thermal/logistics evidence."""

    action: Literal["normal", "buffer", "expedite", "reroute", "quality_review"]
    reason: str
    thermal_status: str
    logistics_status: str
    thermal: ExposureMetrics | None = None
    logistics_evidence: tuple[str, ...] = field(default_factory=tuple)
