"""Evaluate explicitly matched road evidence without inventing travel time or routes."""

from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from .config import ROAD_COUNTER_FRESHNESS_MINUTES, ROAD_EVENT_FRESHNESS_MINUTES
from .interfaces import RoadTrafficEvidence, RouteEvidence
from .local_data import read_snapshot

REVOKED_PREFIXES = ("aufgehoben:", "révoqué:", "revocato:", "revoked:")


def _time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None and result.utcoffset() is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _fresh(value, now, limit):
    observed = _time(value)
    return observed is not None and 0 <= (now - observed).total_seconds() <= limit * 60


def _number(value):
    try:
        number = float(value)
        return number if isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None


def _speed_signal(reading, match, now):
    if match.vehicle_class not in ("light", "heavy"):
        raise ValueError("road vehicle class must be light or heavy")
    if not isfinite(match.reference_speed_kmh) or match.reference_speed_kmh <= 0:
        raise ValueError("road reference speed must be finite and positive")
    if not reading or not _fresh(reading.get("observed_at"), now, ROAD_COUNTER_FRESHNESS_MINUTES):
        return None, "measurement is missing, stale or has an invalid/future timestamp"
    speed_index, flow_index = ("12", "11") if match.vehicle_class == "light" else ("22", "21")
    values = {value.get("index"): value.get("fields", {}) for value in reading.get("values", [])}
    speed = _number(values.get(speed_index, {}).get("speed"))
    flow = _number(values.get(flow_index, {}).get("vehicleFlowRate"))
    if speed is None or flow is None or flow <= 0:
        return None, "class-specific speed or positive flow unavailable; zero flow cannot prove a closure"
    loss = max(0.0, min(100.0, 100 * (1 - speed / match.reference_speed_kmh)))
    return loss, (f"{match.vehicle_class} speed {speed:g} km/h versus supplied normal reference "
                  f"{match.reference_speed_kmh:g} km/h: {loss:.1f}% speed loss; "
                  f"flow {flow:g} vehicles/h, measured {reading['observed_at']}. Point speed is not route travel time.")


def _event_exclusion(event, match, fetched_at, now):
    if match.effect not in ("disrupted", "restricted"):
        raise ValueError("road event effect must be disrupted or restricted")
    if not _fresh(fetched_at, now, ROAD_EVENT_FRESHNESS_MINUTES):
        return "event snapshot is missing, stale or has an invalid/future fetch time"
    if not event:
        return "verified event is absent from the latest snapshot; route clearance is unknown"
    if any(str(text).strip().casefold().startswith(REVOKED_PREFIXES)
           for text in event.get("descriptions", [])):
        return "event was revoked"
    updated = _time(event.get("updated_at"))
    if updated is None or updated > now or updated != _time(match.updated_at):
        return "event update is missing or changed; verify this version's location, direction and effect"
    if event.get("complex_validity"):
        return "recurring or exceptional validity schedule requires separate review"
    start, end = _time(event.get("valid_from")), _time(event.get("valid_until"))
    if event.get("validity_status") not in ("active", "definedByValidityTimeSpec"):
        return "event validity is unknown or inactive"
    if start is None or start > now or (event.get("valid_until") is not None and end is None):
        return "event validity interval is missing, invalid or has not started"
    if end is not None and (end <= now or end <= start):
        return "event has expired or has an invalid interval"
    return None


def assess_road_traffic(data_dir: Path, route: RouteEvidence, *, evaluated_at=None) -> RoadTrafficEvidence:
    """Maximum local signal; incomplete selected evidence leaves the component unknown.

    An independently verified restriction still informs action even if another selected
    counter is unavailable. Missing messages never establish a clear route.
    """
    now = evaluated_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("road evaluation time must include a timezone")
    snapshot = read_snapshot(data_dir, "opentransportdata_basel_region") or {}
    standalone = read_snapshot(data_dir, "opentransportdata") or {}
    combined_time = _time((snapshot.get("data") or {}).get("fetched_at"))
    standalone_time = _time(standalone.get("fetched_at"))
    if standalone_time is not None and (combined_time is None or standalone_time > combined_time):
        snapshot = {"request_ok": not standalone.get("errors"), "data": standalone}
    data = snapshot.get("data") or {}
    counters = data.get("traffic_counters") or {}
    readings = counters.get("current_readings") or []
    events = data.get("traffic_situations") or []
    context = {"fetched_at": data.get("fetched_at"), "filter": data.get("filter"),
               "sites": counters.get("sites", []), "current_readings": readings,
               "traffic_situations": events, "errors": data.get("errors", []),
               "interpretation": "Regional candidates; explicit shipment route matches are required."}
    evidence, omitted, severities = [], [], []
    restricted = disrupted = False
    if not route.road_counters and not route.road_events:
        omitted.append("OpenTransportData is context only: no verified shipment route matches supplied.")
    # Partial fetches can contain useful counters or events; subfeed errors block only that subfeed.
    errors = data.get("errors", [])
    fetched = _time(data.get("fetched_at"))
    failed = (not snapshot.get("request_ok") and not errors) or fetched is None or fetched > now
    reading_by_id = {row.get("site_id"): row for row in readings}
    for match in route.road_counters:
        if failed or any(str(error).startswith("Traffic Counters:") for error in errors):
            severity, reason = None, "counter fetch failed"
        else:
            severity, reason = _speed_signal(reading_by_id.get(match.site_id), match, now)
        note = f"OpenTransportData counter {match.site_id}: {reason}"
        (omitted if severity is None else evidence).append(note)
        if severity is not None:
            severities.append(severity)
    event_by_id = {row.get("id"): row for row in events}
    for match in route.road_events:
        event = event_by_id.get(match.situation_id)
        reason = ("event fetch failed" if failed or any(str(error).startswith("Traffic Situations:") for error in errors)
                  else _event_exclusion(event, match, data.get("fetched_at"), now))
        if reason:
            omitted.append(f"OpenTransportData event {match.situation_id}: {reason}.")
            continue
        restricted |= match.effect == "restricted"
        disrupted = True
        severities.append(100.0)
        evidence.append(f"OpenTransportData event {match.situation_id}: verified {match.effect}, "
                        f"source version {match.updated_at}. Binary disruption severity 100 is a demo policy, not probability.")
    severity = max(severities) if severities and (not omitted or max(severities) == 100) else None
    return RoadTrafficEvidence(severity, restricted, disrupted, tuple(evidence), tuple(omitted), context)
