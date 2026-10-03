"""Deterministic synthetic fleet replay using the existing shipment risk policy."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from math import asin, ceil, cos, exp, isfinite, radians, sin, sqrt
import json
from pathlib import Path

from .decision import decide_action
from .config import DEFAULT_MIN_TEMPERATURE_C, DEFAULT_MAX_TEMPERATURE_C
from .interfaces import RouteEvidence, ShipmentPlan, TemperatureReading
from .priority import calculate_priority_score
from .thermal import analyze_temperature_series, time_to_temperature_limit

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "demo-transports.json"
DEMO_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
SCENARIOS = ("fleet", "normal", "traffic", "urgent", "heat", "reroute")


def route_distance_km(coordinates) -> float:
    """Length of the authored polyline, not a verified navigation distance."""
    distance = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coordinates, coordinates[1:]):
        a = sin(radians(lat2 - lat1) / 2) ** 2
        a += cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
        distance += 6371.0 * 2 * asin(min(1.0, sqrt(a)))
    return distance


def _plans(scenario: str) -> list[ShipmentPlan]:
    plans = []
    for record in DEMO_CONFIG["shipments"]:
        fields = {**record, "coordinates": tuple(tuple(point) for point in record["coordinates"])}
        fields["alternate_coordinates"] = tuple(tuple(point) for point in record.get("alternate_coordinates", []))
        plans.append(ShipmentPlan(**fields))
    if scenario != "fleet":
        plans = [replace(plan, delay_minutes=0, start_c=5, ambient_c=5,
                         need_after_departure_minutes=plan.travel_minutes + 360,
                         alternate_coordinates=()) for plan in plans]
        first = plans[0]
        if scenario in ("traffic", "urgent", "reroute"):
            first = replace(first, delay_minutes=45)
        if scenario == "urgent":
            first = replace(first, priority="critical", need_after_departure_minutes=110)
        if scenario == "heat":
            first = replace(first, start_c=7, ambient_c=40, tau_minutes=90)
        if scenario == "reroute":
            first = replace(first, alternate_coordinates=tuple(
                tuple(point) for point in DEMO_CONFIG["shipments"][0]["alternate_coordinates"]))
        plans[0] = first
    else:
        # An alternate corridor is offered only in the explicit reroute scenario.
        plans = [replace(plan, alternate_coordinates=()) for plan in plans]
    return plans


def _shipment(plan: ShipmentPlan, anchor: datetime, elapsed_minutes: float) -> dict:
    departure = anchor - timedelta(minutes=plan.initial_elapsed_minutes)
    now = anchor + timedelta(minutes=elapsed_minutes)
    journey_minutes = plan.travel_minutes + plan.delay_minutes
    accuracy = DEMO_CONFIG["sensor_accuracy_c"]
    crossings = [time_to_temperature_limit(plan.start_c, plan.ambient_c, limit, timedelta(minutes=plan.tau_minutes))
                 for limit in (DEFAULT_MIN_TEMPERATURE_C + accuracy, DEFAULT_MAX_TEMPERATURE_C - accuracy)]
    hold_times = [ceil(value) for value in crossings if value is not None and value <= journey_minutes]
    hold_at = min(hold_times) if hold_times else None
    raw_elapsed = plan.initial_elapsed_minutes + elapsed_minutes
    elapsed = raw_elapsed if hold_at is not None else min(raw_elapsed, journey_minutes)
    evaluated_at = departure + timedelta(minutes=elapsed)
    jam_start = plan.travel_minutes * plan.jam_fraction
    delay_consumed = min(plan.delay_minutes, max(0.0, elapsed - jam_start))
    progress = min(1.0, (elapsed - delay_consumed) / plan.travel_minutes)
    in_jam = plan.delay_minutes > 0 and jam_start <= elapsed < jam_start + plan.delay_minutes
    delivered = progress >= 1.0
    sample_minutes = list(range(int(elapsed) + 1))
    if sample_minutes[-1] != elapsed:
        sample_minutes.append(elapsed)
    readings = [TemperatureReading(
        departure + timedelta(minutes=minute),
        plan.ambient_c + (plan.start_c - plan.ambient_c) * exp(-minute / plan.tau_minutes),
        DEMO_CONFIG["sensor_accuracy_c"],
    ) for minute in sample_minutes]
    thermal = analyze_temperature_series(readings, monitoring_started_at=departure, evaluated_at=evaluated_at)
    if thermal.quality_review_required:
        # The demo explicitly applies a synthetic hold; no real dispatch is executed.
        movement_elapsed = min(elapsed, hold_at if hold_at is not None else 0)
        movement_delay = min(plan.delay_minutes, max(0.0, movement_elapsed - jam_start))
        progress = min(1.0, (movement_elapsed - movement_delay) / plan.travel_minutes)
        delivered = False
    eta = departure + timedelta(minutes=journey_minutes)
    needed = departure + timedelta(minutes=plan.need_after_departure_minutes)
    alternate_eta = (now + timedelta(minutes=plan.travel_minutes * (1 - progress) + 15)
                     if plan.alternate_coordinates else None)
    disrupted = plan.delay_minutes > 0 and not delivered
    route = RouteEvidence(
        disruption_observed=disrupted, estimated_arrival_at=eta, material_needed_at=needed,
        buffer_hours=DEMO_CONFIG["buffers_hours"][plan.priority], exposed_handling=False,
        alternate_route_available=bool(plan.alternate_coordinates),
        alternate_route_suitable=bool(plan.alternate_coordinates), alternate_arrival_at=alternate_eta,
        evidence=(f"SIMULATED route delay: {plan.delay_minutes:g} minutes.",
                  "SIMULATED protected transfer, ETA, need-by, GPS and package readings."),
    )
    assessment = decide_action(thermal, route)
    score = calculate_priority_score(thermal, route)
    distance = route_distance_km(plan.coordinates)
    return {
        "id": plan.id, "name": plan.name, "material": plan.material, "priority": plan.priority,
        "origin": plan.origin, "destination": plan.destination, "routeName": plan.route_name,
        "route": plan.coordinates, "alternativeRoute": plan.alternate_coordinates,
        "progress": progress, "distanceKm": round(distance, 1),
        "remainingKm": round(distance * (1 - progress), 1),
        "departureAt": departure.isoformat(), "etaAt": eta.isoformat(), "neededAt": needed.isoformat(),
        "alternateEtaAt": alternate_eta.isoformat() if alternate_eta else None,
        "temperatureC": round(readings[-1].temperature_c, 2),
        "temperatureBand": {"minimumC": DEFAULT_MIN_TEMPERATURE_C, "maximumC": DEFAULT_MAX_TEMPERATURE_C},
        "temperatureHistory": [{"at": item.observed_at.isoformat(), "value": round(item.temperature_c, 2)} for item in readings],
        "thermal": asdict(thermal), "score": score.as_dict(),
        "action": assessment.action, "reason": assessment.reason,
        "status": "held" if thermal.quality_review_required else "delivered" if delivered else "delayed" if in_jam else "moving",
        "delayMinutes": plan.delay_minutes,
        "slackMinutes": round((needed - eta).total_seconds() / 60),
        "bufferHours": route.buffer_hours, "observedAt": evaluated_at.isoformat(),
        "provenance": "simulated",
    }


def demo_fleet(anchor: datetime, elapsed_minutes: float = 0, scenario: str = "fleet") -> dict:
    """Replay resets deterministically; no live readings are imported into the demo."""
    if anchor.tzinfo is None or anchor.utcoffset() is None:
        raise ValueError("demo anchor requires a timezone")
    if scenario not in SCENARIOS:
        raise ValueError("unknown demo scenario")
    if not isfinite(elapsed_minutes) or not 0 <= elapsed_minutes <= DEMO_CONFIG["maximum_replay_minutes"]:
        raise ValueError("replay minutes must be between 0 and 180")
    now = anchor.astimezone(timezone.utc) + timedelta(minutes=elapsed_minutes)
    shipments = [_shipment(plan, anchor, elapsed_minutes) for plan in _plans(scenario)]
    return {"updatedAt": now.isoformat(), "shipments": shipments,
            "simulation": {"scenario": scenario, "elapsedMinutes": elapsed_minutes,
                           "minutesPerSecond": DEMO_CONFIG["simulation_minutes_per_second"],
                           "maximumMinutes": DEMO_CONFIG["maximum_replay_minutes"]}}
