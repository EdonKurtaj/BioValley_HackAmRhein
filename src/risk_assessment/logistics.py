"""Conservative traffic and Rhine evidence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Literal, Sequence

from .config import MIN_TRAFFIC_BASELINE_SIZE, RHINE_PRE_ALERT_CM, RHINE_RESTRICTION_CM, TRAFFIC_MINIMUM_SCALE

@dataclass(frozen=True)
class TrafficAnomaly:
    status: Literal["available", "unknown"]
    robust_z: float | None
    baseline_median: float | None
    reason: str


def traffic_volume_anomaly(
    observed_count: float,
    comparable_counts: Sequence[float],
    minimum_scale: float = TRAFFIC_MINIMUM_SCALE,
    minimum_baseline_size: int = MIN_TRAFFIC_BASELINE_SIZE,
) -> TrafficAnomaly:
    """Robust anomaly by median/MAD; caller must supply like-for-like counter bins."""
    if not isfinite(observed_count) or observed_count < 0:
        raise ValueError("traffic count must be finite and non-negative")
    if not isfinite(minimum_scale) or minimum_scale <= 0:
        raise ValueError("minimum scale must be finite and positive")
    if minimum_baseline_size < 3:
        raise ValueError("minimum baseline size must be at least three")
    if any(not isfinite(value) or value < 0 for value in comparable_counts):
        raise ValueError("baseline counts must be finite and non-negative")
    if len(comparable_counts) < minimum_baseline_size:
        return TrafficAnomaly("unknown", None, None,
                              f"Need at least {minimum_baseline_size} comparable observations; received {len(comparable_counts)}.")
    center = median(comparable_counts)
    mad = median([abs(value - center) for value in comparable_counts])
    scale = max(1.4826 * mad, minimum_scale)
    return TrafficAnomaly("available", (observed_count - center) / scale, center,
                          "Unusual volume is not proof of congestion or travel delay.")


@dataclass(frozen=True)
class RhineStatus:
    status: Literal["unknown", "no_high_water_trigger", "pre_alert", "restricted"]
    route_segment: str | None
    water_level_cm: float | None
    reason: str


def classify_rhine_high_water(
    water_level_cm: float | None,
    route_segment: str | None,
) -> RhineStatus:
    """Apply Port of Switzerland marks only to an explicitly matching ship leg."""
    if water_level_cm is None or not isfinite(water_level_cm):
        return RhineStatus("unknown", route_segment, water_level_cm, "Port gauge reading is missing or invalid.")
    if route_segment not in RHINE_RESTRICTION_CM:
        return RhineStatus("unknown", route_segment, water_level_cm,
                           "No matching ship-leg segment was supplied; the gauge cannot trigger this shipment.")
    restriction_level = RHINE_RESTRICTION_CM[route_segment]
    if water_level_cm >= restriction_level:
        return RhineStatus("restricted", route_segment, water_level_cm,
                           f"Port high-water mark {restriction_level:g} cm reached for this segment.")
    if water_level_cm >= RHINE_PRE_ALERT_CM:
        return RhineStatus("pre_alert", route_segment, water_level_cm,
                           f"Port high-water pre-alert mark {RHINE_PRE_ALERT_CM:g} cm reached; this is not by itself a closure.")
    return RhineStatus("no_high_water_trigger", route_segment, water_level_cm,
                       "Below the Port high-water pre-alert; no low-water capacity rule is inferred.")
