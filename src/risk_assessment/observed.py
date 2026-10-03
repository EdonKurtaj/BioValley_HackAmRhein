"""Score current open-data signals without simulating package or route data."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from pathlib import Path

from .config import (
    OPEN_RHINE_WEIGHT,
    OPEN_TRAFFIC_WEIGHT,
    OPEN_URGENCY_WEIGHT,
    OPEN_WEATHER_WEIGHT,
    TRAFFIC_ANOMALY_THRESHOLD,
)
from .disturbance import detect_open_data_disturbances, detect_traffic_disturbance, score_weather_context
from .interfaces import RouteEvidence
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot
from .logistics import RhineStatus, classify_rhine_high_water


def _component(name: str, status: str, severity: float | None, weight: float, evidence: list[str]) -> dict:
    points = round(weight * severity / 100, 1) if severity is not None else None
    return {"name": name, "status": status, "severity_0_to_100": severity,
            "weight_points": weight, "contributed_points": points, "evidence": evidence}


def _rhine_severity(level_cm: float | None, segment: str | None, status: str) -> float | None:
    if status == "unknown":
        return None
    if status == "no_high_water_trigger":
        return 0.0
    if status == "restricted":
        return 100.0
    if level_cm is None or segment is None:
        return None
    restriction = 790.0 if segment == "basel_mittlere_bruecke_birsfelden" else 820.0
    return round(25.0 + 75.0 * (level_cm - 700.0) / (restriction - 700.0), 1)


def assess_observed_data(
    data_dir: Path = DEFAULT_DATA_DIR,
    route: RouteEvidence | None = None,
    route_segment: str | None = None,
) -> dict:
    """Return a current-data score; stale and route-unmatched inputs stay excluded."""
    route = route or RouteEvidence()
    if not isfinite(route.buffer_hours) or route.buffer_hours < 0:
        raise ValueError("buffer hours must be finite and non-negative")
    for timestamp in (route.estimated_arrival_at, route.material_needed_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("logistics timestamps must include a timezone")
    context = collect_local_context(data_dir)
    weather = context.get("weather") or {}
    weather_signal = score_weather_context(weather.get("measurements") or {})
    weather_signal = {
        **weather_signal,
        "source_status": weather.get("source_status", "unknown"),
        "last_observation_severity": weather_signal["score"],
        "current_score_eligible": weather.get("source_status") == "observed",
    }
    if weather.get("source_status") != "observed":
        weather_signal["status"] = weather.get("source_status", "unknown")
        weather_signal["evidence"] = [f"Weather feed is {weather.get('source_status', 'unknown')}; last observation is context only and excluded from the current score."]

    traffic_finding = detect_traffic_disturbance(data_dir)
    traffic_severity = None
    if traffic_finding.robust_z is not None:
        traffic_severity = min(100.0, max(0.0, traffic_finding.robust_z / TRAFFIC_ANOMALY_THRESHOLD * 100.0))

    rhine = context.get("rhine") or {}
    port = rhine.get("port_basel_rheinhalle") or {}
    level = port.get("value")
    if level is not None:
        try:
            level = float(level)
        except (TypeError, ValueError):
            level = None
    port_is_fresh = rhine.get("source_status") == "observed snapshot"
    port_level_for_score = level if port_is_fresh else None
    rhine_status = (classify_rhine_high_water(port_level_for_score, route_segment) if port_is_fresh else
                    RhineStatus("unknown", route_segment, level,
                                f"Port gauge snapshot is {rhine.get('source_status', 'unknown')} and is excluded from the current score."))

    components = [
        _component("weather", weather_signal["status"],
                   weather_signal["score"] if weather_signal["current_score_eligible"] else None,
                   OPEN_WEATHER_WEIGHT,
                   weather_signal["evidence"]),
        _component("traffic", traffic_finding.status, traffic_severity, OPEN_TRAFFIC_WEIGHT,
                   [traffic_finding.summary, *traffic_finding.evidence]),
        _component("rhine", rhine_status.status,
                   _rhine_severity(port_level_for_score, route_segment, rhine_status.status), OPEN_RHINE_WEIGHT,
                   [rhine_status.reason]),
    ]

    urgency_score = None
    urgency_status = "not supplied"
    if route.estimated_arrival_at is not None and route.material_needed_at is not None:
        slack = (route.material_needed_at - route.estimated_arrival_at).total_seconds() / 3600
        if route.buffer_hours == 0:
            urgency_score = 100.0 if slack < 0 else 0.0
        else:
            urgency_score = min(100.0, max(0.0, (route.buffer_hours - slack) / route.buffer_hours * 100))
        urgency_status = "available"
    components.append(_component("production_urgency", urgency_status, urgency_score,
                                 OPEN_URGENCY_WEIGHT,
                                 ["ETA and material need-by inputs are caller-supplied, not in the open-data feeds."]))

    known = [item for item in components if item["contributed_points"] is not None]
    coverage = sum(item["weight_points"] for item in known)
    score = round(sum(item["contributed_points"] for item in known), 1) if known else None
    route_trigger = rhine_status.status in ("pre_alert", "restricted") or traffic_finding.status == "detected"

    if rhine_status.status == "restricted" and route.alternate_route_available:
        suggestion = "Reroute"
        suggestion_reason = "A matching ship-leg restriction is present and a feasible alternate route is available."
    elif (urgency_score is not None and urgency_score >= 70) or (score is not None and score >= 50):
        suggestion = "Expedite"
        suggestion_reason = "Production urgency is high; prioritize delivery/receiving."
    elif (urgency_score is not None and urgency_score >= 50) or route_trigger or (score is not None and score >= 20):
        suggestion = "Buffer"
        suggestion_reason = "Combined evidence indicates elevated risk; protect production slack and monitor the shipment."
    elif coverage < 50:
        suggestion = "Monitor"
        suggestion_reason = (f"Only {coverage:.0f}% of score weight has evidence; collect package-temperature "
                            "and ETA data before calling it normal.")
    else:
        suggestion = "Normal"
        suggestion_reason = "Combined score is below intervention thresholds and evidence coverage is adequate."

    weather_score = weather_signal["score"]
    if rhine_status.status == "restricted" and route.alternate_route_available:
        action = "reroute"
        reason = "The current Port gauge meets a restriction for the supplied ship leg, and an alternate route is available."
    elif route.estimated_arrival_at and route.material_needed_at and urgency_score and urgency_score > 0:
        action = "expedite"
        reason = "Caller-supplied ETA leaves less than the configured production buffer."
    elif route_trigger:
        action = "buffer"
        reason = "Observed route-related evidence indicates a disturbance; retain controlled stock while the route is assessed."
    else:
        action = "normal"
        reason = "No actionable disturbance is present in the scored current observations; unobserved shipment conditions remain unknown."

    current_traffic = traffic_finding.__dict__
    traffic_snapshot = read_snapshot(data_dir, "basel_dataset_100006") or {}
    traffic_rows = ((traffic_snapshot.get("data") or {}).get("results") or [])
    def record_time(record: dict) -> float:
        raw = record.get("datetimeto") or record.get("datetimefrom") or ""
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return float("-inf")
    newest_traffic = max(traffic_rows, key=record_time) if traffic_rows else None
    return {
        "mode": "observed data only; no package-temperature curve, route disruption, or ETA is simulated",
        "pipeline": ["Open data", "Disturbance detection", "Risk assessment", "Manufacturing decision", "Factory dashboard"],
        "action": {"recommendation": action, "reason": reason},
        "system_suggestion": {"suggestion": suggestion, "reason": suggestion_reason},
        "manufacturing_priority_score": {
            "score": score,
            "coverage_percent": round(coverage, 1),
            "components": components,
            "interpretation": "Score points sum only current, applicable evidence. Missing/stale inputs are excluded, not treated as zero; coverage shows how much of the 100-point model is scored.",
        },
        "current_observations": {
            "weather": weather,
            "weather_score_details": weather_signal,
            "traffic": {**context.get("traffic", {}), "latest_observation": newest_traffic,
                        "finding": current_traffic},
            "rhine": {**rhine, "shipment_segment": route_segment,
                      "finding": rhine_status.__dict__},
        },
        "detected_open_data_disturbances": detect_open_data_disturbances(data_dir),
    }


def render_observed_summary(result: dict) -> str:
    """Show current observations and the observed-only score in a short terminal view."""
    observations = result["current_observations"]
    weather = observations["weather"] or {}
    measurements = weather.get("measurements") or {}
    traffic = observations["traffic"]
    rhine = observations["rhine"]
    port = rhine.get("port_basel_rheinhalle") or {}
    basel_gauge = rhine.get("basel_stadt_latest") or {}
    weather_measurements = weather.get("measurements") or {}
    traffic_row = traffic.get("latest_observation") or {}
    score = result["manufacturing_priority_score"]
    current_score = f"{score['score']:.1f}" if score["score"] is not None else "unknown"
    components = {item["name"]: item for item in score["components"]}
    if score["coverage_percent"] == 0:
        refresh_note = "Refresh saved feeds with: python3 pythontest/api_requester.py --once"
    else:
        refresh_note = ""
    lines = [
        "CURRENT OPEN-DATA ASSESSMENT — no simulation",
        f"Weather: {weather.get('source_status', 'unknown')} ({weather.get('observation_age_minutes', 'unknown')} min old); "
        f"{measurements.get('tre200s0', 'unknown')} °C, "
        f"{measurements.get('rre150z0', 'unknown')} mm/10 min rain, gust {measurements.get('fu3010z1', 'unknown')} km/h; "
        f"last-observation context severity {observations['weather_score_details']['last_observation_severity'] if observations['weather_score_details']['last_observation_severity'] is not None else 'unknown'}/100; "
        f"weather contribution {components['weather']['contributed_points'] if components['weather']['contributed_points'] is not None else 'not scored'}/"
        f"{components['weather']['weight_points']:g} points.",
        f"Traffic: {traffic.get('source_status', 'unknown')}; newest count "
        f"{traffic_row.get('total', 'unknown')} at {traffic_row.get('sitename', 'unknown')} "
        f"(pw {traffic_row.get('pw', 'unknown')}, delivery vans {traffic_row.get('lief', 'unknown')}, heavy vehicles {traffic_row.get('lw', 'unknown')}) is "
        f"{traffic.get('latest_record_age_minutes', 'unknown')} minutes old; "
        f"baseline available: {traffic.get('baseline_available', False)}; {'excluded' if components['traffic']['contributed_points'] is None else 'scored'}.",
        f"Weather context-only fields: radiation {weather_measurements.get('gre000z0', 'unknown')} W/m², "
        f"sunshine {weather_measurements.get('sre000z0', 'unknown')} min, humidity {weather_measurements.get('ure200s0', 'unknown')}%, "
        f"dew point {weather_measurements.get('tde200s0', 'unknown')} °C, mean wind {weather_measurements.get('fu3010z0', 'unknown')} km/h, "
        f"pressure {weather_measurements.get('prestas0', 'unknown')} hPa; not scored without a supported relationship/exposed transfer.",
        f"Rhine: Port gauge {port.get('value', 'unknown')} cm ({rhine.get('source_status', 'unknown')}, "
        f"snapshot {rhine.get('port_snapshot_age_minutes', 'unknown')} min old); "
        f"Basel-Stadt gauge {basel_gauge.get('pegelhoehe', 'unknown')} cm ({rhine.get('basel_stadt_observation_age_minutes', 'unknown')} min old) "
        f"and discharge {basel_gauge.get('abfluss', 'unknown')} m³/s; "
        f"ship leg {'supplied' if rhine.get('shipment_segment') else 'not supplied'}, so route effect {'scored' if components['rhine']['contributed_points'] is not None else 'excluded'}.",
        f"Production urgency: {components['production_urgency']['status']}.",
        f"Decision: {result['action']['recommendation'].replace('_', ' ').title()} — {result['action']['reason']}",
        f"Current Risk Score: {current_score}/100 (coverage {score['coverage_percent']:.0f}%)",
        f"System Suggestion: {result['system_suggestion']['suggestion']} — {result['system_suggestion']['reason']}",
        "A score with low coverage is only the risk contribution from known observations, not a complete shipment-risk estimate.",
    ]
    if refresh_note:
        lines.append(refresh_note)
    return "\n".join(lines)
